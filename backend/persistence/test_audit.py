"""
audit_events: the closed stage/outcome vocabulary, and the observability
guarantee for a stage that raises before producing a result (design section
I.1, brief section 11): "WEIGH was reached and failed" must be answerable
from audit_events alone, with no fabricated weigh_results row.
"""

import pytest

from persistence.audit import (
    OUTCOME_FAILED,
    OUTCOME_SUCCEEDED,
    STAGE_RUN_FAILED,
    STAGES,
    map_audit_event,
    map_run_failed_event,
)
from persistence.conftest import FakeSupabaseClient, full_run_payout_vs_dispute
from persistence.store import PersistenceStore, candidate_row_id_map


def test_stage_vocabulary_matches_the_schema_check_constraint():
    # supabase/migrations/20260825000000_initial_schema.sql's audit_events
    # CHECK constraint, restated here so a drift between the two is a test
    # failure rather than a silent insert-time rejection.
    assert STAGES == {
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "WEIGH_COMPLETED",
        "GOVERN_DECIDED",
        "EXECUTOR_COMPLETED",
        "RUN_FAILED",
    }


def test_map_audit_event_rejects_unknown_stage():
    with pytest.raises(ValueError, match="unknown audit stage"):
        map_audit_event("NOT_A_REAL_STAGE", OUTCOME_SUCCEEDED, "x")


def test_map_audit_event_rejects_unknown_outcome():
    with pytest.raises(ValueError, match="unknown audit outcome"):
        map_audit_event("RUN_STARTED", "MAYBE", "x")


def test_map_run_failed_event_shape():
    row = map_run_failed_event("WEIGH", ValueError("policy is missing section 'scoring'"))
    assert row["stage"] == STAGE_RUN_FAILED
    assert row["outcome"] == OUTCOME_FAILED
    assert row["detail"]["failed_stage"] == "WEIGH"
    assert row["detail"]["error_type"] == "ValueError"
    assert "scoring" in row["detail"]["error_message"]


def test_map_run_failed_event_detail_is_small_not_a_reconstructed_document():
    # design section F.10: detail is an error message and type, never the
    # full payload a successful stage would have produced.
    row = map_run_failed_event("GOVERN", RuntimeError("boom"))
    assert set(row["detail"]) == {"failed_stage", "error_type", "error_message"}


# --- the observability guarantee, exercised against the store --------------


def _simulate_pipeline_with_failing_weigh(store, case_run_id, run):
    """
    Mirrors the shape a future orchestrator would use: persist what happened
    up to the failing stage, catch the stage's exception, and record it --
    never fabricate a result row for the stage that failed.
    """

    store.record_audit_event(case_run_id, "RUN_STARTED", "SUCCEEDED", "run started")
    store.record_agent_outputs(case_run_id, run["agent_actions"], "payouts", "dispute")
    store.record_audit_event(case_run_id, "AGENTS_RECORDED", "SUCCEEDED", "agents recorded")
    store.record_conflict(case_run_id, run["conflict_result"])
    store.record_audit_event(case_run_id, "CONFLICT_EVALUATED", "SUCCEEDED", "conflict evaluated")
    store.record_candidates(case_run_id, run["resolve_output"]["candidates"])
    store.record_audit_event(case_run_id, "RESOLVE_COMPLETED", "SUCCEEDED", "resolve completed")

    try:
        raise ValueError("policy is missing required section 'scoring'")
    except ValueError as exc:
        store.record_run_failed(case_run_id, "WEIGH", exc)
        raise


def test_failed_stage_leaves_no_result_row_but_is_observable_in_audit_events():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()
    case_run_id = "case-run-failed"

    with pytest.raises(ValueError):
        _simulate_pipeline_with_failing_weigh(store, case_run_id, run)

    # No weigh_results row exists for this run -- WEIGH never produced one.
    assert client.rows("weigh_results") == []
    assert client.rows("govern_results") == []
    assert client.rows("execution_receipts") == []

    # But the audit trail proves WEIGH was reached and failed.
    events = [e for e in client.rows("audit_events") if e["case_run_id"] == case_run_id]
    stages = [e["stage"] for e in events]
    assert stages == [
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "RUN_FAILED",
    ]
    failure = events[-1]
    assert failure["outcome"] == "FAILED"
    assert failure["detail"]["failed_stage"] == "WEIGH"
    assert failure["detail"]["error_type"] == "ValueError"


def test_audit_events_stay_associated_with_the_correct_case_run():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)

    store.record_audit_event("run-A", "RUN_STARTED", "SUCCEEDED", "a")
    store.record_audit_event("run-B", "RUN_STARTED", "SUCCEEDED", "b")
    store.record_run_failed("run-B", "GOVERN", RuntimeError("boom"))

    run_a_events = [e for e in client.rows("audit_events") if e["case_run_id"] == "run-A"]
    run_b_events = [e for e in client.rows("audit_events") if e["case_run_id"] == "run-B"]

    assert len(run_a_events) == 1
    assert len(run_b_events) == 2
    assert run_a_events[0]["stage"] == "RUN_STARTED"
    assert {e["stage"] for e in run_b_events} == {"RUN_STARTED", "RUN_FAILED"}


def test_successful_run_records_a_success_event_per_stage_reached():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()
    case_run_id = "case-run-ok"

    store.record_audit_event(case_run_id, "RUN_STARTED", "SUCCEEDED", "run started")
    store.record_agent_outputs(case_run_id, run["agent_actions"], "payouts", "dispute")
    store.record_audit_event(case_run_id, "AGENTS_RECORDED", "SUCCEEDED", "agents recorded")
    store.record_conflict(case_run_id, run["conflict_result"])
    store.record_audit_event(case_run_id, "CONFLICT_EVALUATED", "SUCCEEDED", "conflict evaluated")
    candidate_rows = store.record_candidates(case_run_id, run["resolve_output"]["candidates"])
    store.record_audit_event(case_run_id, "RESOLVE_COMPLETED", "SUCCEEDED", "resolve completed")
    row_ids = candidate_row_id_map(candidate_rows)
    store.record_candidate_scores(run["weigh_output"], row_ids)
    store.record_weigh_result(case_run_id, run["weigh_output"])
    store.record_audit_event(case_run_id, "WEIGH_COMPLETED", "SUCCEEDED", "weigh completed")
    govern_row = store.record_govern_result(case_run_id, run["govern_output"], row_ids)
    store.record_audit_event(case_run_id, "GOVERN_DECIDED", "SUCCEEDED", "govern decided")
    store.record_execution_receipt(case_run_id, govern_row["id"], run["receipt"])
    store.record_audit_event(case_run_id, "EXECUTOR_COMPLETED", "SUCCEEDED", "executor completed")

    events = [e for e in client.rows("audit_events") if e["case_run_id"] == case_run_id]
    assert [e["stage"] for e in events] == [
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "WEIGH_COMPLETED",
        "GOVERN_DECIDED",
        "EXECUTOR_COMPLETED",
    ]
    assert all(e["outcome"] == "SUCCEEDED" for e in events)
