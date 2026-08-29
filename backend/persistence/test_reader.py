"""
CaseReader against the in-memory FakeSupabaseClient -- mirrors test_store.py's
stance: no live database, real pipeline output via persistence.conftest.
"""

from persistence.conftest import FakeSupabaseClient, full_run_ambiguous, full_run_payout_vs_dispute
from persistence.reader import CaseReader
from persistence.store import PersistenceStore, candidate_row_id_map


def _persist_full_run(store, run, external_case_id):
    case = store.get_or_create_case(external_case_id)
    case_run = store.create_case_run(
        case["id"],
        run["resolve_output"],
        run["case_context"],
        run["weigh_output"]["policy_id"],
        run["weigh_output"]["policy_version"],
        run["weigh_output"]["policy_hash"],
    )
    store.record_audit_event(case_run["id"], "RUN_STARTED", "SUCCEEDED", "run started")
    store.record_agent_outputs(
        case_run["id"], run["agent_actions"], run["resolve_output"]["agent_a"], run["resolve_output"]["agent_b"]
    )
    store.record_audit_event(case_run["id"], "AGENTS_RECORDED", "SUCCEEDED", "agents recorded")
    store.record_conflict(case_run["id"], run["conflict_result"])
    store.record_audit_event(case_run["id"], "CONFLICT_EVALUATED", "SUCCEEDED", "conflict evaluated")
    candidate_rows = store.record_candidates(case_run["id"], run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    store.record_audit_event(case_run["id"], "RESOLVE_COMPLETED", "SUCCEEDED", "candidates generated")
    store.record_candidate_scores(run["weigh_output"], row_ids)
    store.record_weigh_result(case_run["id"], run["weigh_output"])
    store.record_audit_event(case_run["id"], "WEIGH_COMPLETED", "SUCCEEDED", "weighed")
    govern_row = store.record_govern_result(case_run["id"], run["govern_output"], row_ids)
    store.update_case_run_status(case_run["id"], run["govern_output"]["outcome"])
    store.record_audit_event(case_run["id"], "GOVERN_DECIDED", "SUCCEEDED", "governed")
    receipt_row = store.record_execution_receipt(case_run["id"], govern_row["id"], run["receipt"])
    store.record_audit_event(case_run["id"], "EXECUTOR_COMPLETED", "SUCCEEDED", "executed")
    return case, case_run, candidate_rows, row_ids, govern_row, receipt_row


def test_list_cases_and_get_case():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    reader = CaseReader(client)
    run = full_run_payout_vs_dispute()

    case, case_run, *_ = _persist_full_run(store, run, "case-Q")

    cases = reader.list_cases()
    assert len(cases) == 1
    assert reader.get_case(case["id"])["id"] == case["id"]
    assert reader.get_case("nonexistent") is None


class _RaisesOnQueryClient:
    """
    Stands in for a real Postgres/PostgREST client's actual behavior: querying
    a `uuid` column with `.eq("id", <non-uuid text>)` raises (invalid input
    syntax for type uuid) rather than returning zero rows -- unlike
    FakeSupabaseClient, which never type-checks and would silently return no
    rows either way. Used to prove CaseReader.get_case's UUID guard rejects a
    malformed id before ever reaching the client, not merely by coincidence
    of the fake's leniency.
    """

    def table(self, name):
        raise AssertionError(f"table({name!r}) should never be called for a non-UUID id")


def test_get_case_with_syntactically_invalid_id_never_queries_the_client():
    reader = CaseReader(_RaisesOnQueryClient())
    assert reader.get_case("does-not-exist") is None


def test_get_case_with_well_formed_but_unknown_uuid_queries_and_returns_none():
    client = FakeSupabaseClient()
    reader = CaseReader(client)
    assert reader.get_case("00000000-0000-0000-0000-000000000000") is None


def test_list_case_runs_for_case_sorted_newest_first():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    reader = CaseReader(client)
    run = full_run_payout_vs_dispute()

    case, first_run, *_ = _persist_full_run(store, run, "case-Q")
    _, second_run, *_ = _persist_full_run(store, run, "case-Q")

    runs = reader.list_case_runs_for_case(case["id"])
    assert [r["id"] for r in runs] == [second_run["id"], first_run["id"]]
    assert reader.get_latest_case_run(case["id"])["id"] == second_run["id"]


def test_stage_reads_round_trip_a_full_run():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    reader = CaseReader(client)
    run = full_run_payout_vs_dispute()

    case, case_run, candidate_rows, row_ids, govern_row, receipt_row = _persist_full_run(
        store, run, "case-Q"
    )

    assert len(reader.list_agent_outputs(case_run["id"])) == 2
    assert reader.get_conflict(case_run["id"])["conflict"] is True
    assert len(reader.list_candidates(case_run["id"])) == len(run["resolve_output"]["candidates"])
    assert len(reader.list_candidate_scores(list(row_ids.values()))) == len(run["weigh_output"]["candidates"])
    assert reader.get_weigh_result(case_run["id"])["profile_name"] == "standard"
    assert reader.get_govern_result(case_run["id"])["outcome"] == "PROCEED"
    assert reader.get_execution_receipt(case_run["id"])["status"] == "EXECUTED"

    events = reader.list_audit_events(case_run["id"])
    assert [e["stage"] for e in events] == [
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "WEIGH_COMPLETED",
        "GOVERN_DECIDED",
        "EXECUTOR_COMPLETED",
    ]


def test_missing_stage_rows_read_as_none():
    client = FakeSupabaseClient()
    reader = CaseReader(client)
    assert reader.get_conflict("no-such-run") is None
    assert reader.get_weigh_result("no-such-run") is None
    assert reader.get_govern_result("no-such-run") is None
    assert reader.get_execution_receipt("no-such-run") is None
    assert reader.list_agent_outputs("no-such-run") == []
    assert reader.list_audit_events("no-such-run") == []


def test_ambiguous_run_has_null_selected_candidate_on_read_back():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    reader = CaseReader(client)
    run = full_run_ambiguous()

    _, case_run, *_ = _persist_full_run(store, run, "case-R")

    govern_row = reader.get_govern_result(case_run["id"])
    assert govern_row["outcome"] == "AMBIGUOUS"
    assert govern_row["selected_candidate_row_id"] is None
    receipt = reader.get_execution_receipt(case_run["id"])
    assert receipt["status"] == "REJECTED"


def test_human_reviews_round_trip():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    reader = CaseReader(client)
    run = full_run_payout_vs_dispute()
    _, case_run, *_ = _persist_full_run(store, run, "case-Q")

    assert reader.list_human_reviews(case_run["id"]) == []

    store.record_human_review(case_run["id"], "approve", "reviewer-1", "looks right", "PROCEED")
    store.record_human_review(case_run["id"], "reject", None, None, "PROCEED")

    reviews = reader.list_human_reviews(case_run["id"])
    assert [r["action"] for r in reviews] == ["approve", "reject"]
    assert reviews[0]["reviewer"] == "reviewer-1"
    assert reviews[0]["case_run_status_at_review"] == "PROCEED"
