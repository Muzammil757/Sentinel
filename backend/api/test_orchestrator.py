"""
Direct tests of backend.api.orchestrator.run_pipeline against
persistence.conftest.FakeSupabaseClient -- the real pipeline, a fake
database, no HTTP layer involved. Covers the success path and every
stage's non-silent failure path (a stage that raises is recorded as
RUN_FAILED, never reported as a success).
"""

from persistence.conftest import FakeSupabaseClient
from persistence.reader import CaseReader
from persistence.store import PersistenceStore

from .orchestrator import run_pipeline

PAYOUTS = {
    "agent": "payouts",
    "proposed_action": "RELEASE_PAYMENT",
    "confidence": 0.95,
    "amount": 42000,
    "days_overdue": 9,
}
DISPUTE = {
    "agent": "dispute",
    "proposed_action": "HOLD_RELATED_ACTIONS",
    "confidence": 0.95,
    "dispute_status": "OPEN",
    "disputed_amount": 42000,
}


def _store_and_reader():
    client = FakeSupabaseClient()
    return PersistenceStore(client), CaseReader(client), client


def test_successful_run_persists_every_stage():
    store, reader, client = _store_and_reader()

    outcome = run_pipeline(
        store,
        external_case_id="case-Q",
        entity_type="order_vendor",
        agent_a=PAYOUTS,
        agent_b=DISPUTE,
        case_context={"case_id": "case-Q", "merchant_id": "mrch_001"},
    )

    assert outcome.failed is False
    assert outcome.govern_output["outcome"] == "PROCEED"
    assert outcome.receipt["status"] == "EXECUTED"
    assert outcome.case_run["status"] == "PROCEED"

    assert len(client.rows("agent_outputs")) == 2
    assert len(client.rows("conflicts")) == 1
    assert len(client.rows("weigh_results")) == 1
    assert len(client.rows("govern_results")) == 1
    assert len(client.rows("execution_receipts")) == 1
    events = reader.list_audit_events(outcome.case_run["id"])
    assert [e["stage"] for e in events] == [
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "WEIGH_COMPLETED",
        "GOVERN_DECIDED",
        "EXECUTOR_COMPLETED",
    ]


def test_conflict_or_resolve_failure_is_recorded_as_run_failed_not_success():
    store, reader, client = _store_and_reader()
    malformed_agent = {"agent": "payouts", "confidence": 0.95}  # no proposed_action

    outcome = run_pipeline(
        store,
        external_case_id="case-fail",
        entity_type="order_vendor",
        agent_a=malformed_agent,
        agent_b=DISPUTE,
    )

    assert outcome.failed is True
    assert outcome.failed_stage == "CONFLICT_OR_RESOLVE"
    assert outcome.case_run["status"] == "FAILED"
    assert client.rows("govern_results") == []
    assert client.rows("execution_receipts") == []

    events = reader.list_audit_events(outcome.case_run["id"])
    assert [e["stage"] for e in events] == ["RUN_STARTED", "RUN_FAILED"]
    assert events[-1]["outcome"] == "FAILED"
    assert events[-1]["detail"]["failed_stage"] == "CONFLICT_OR_RESOLVE"


def test_weigh_failure_is_recorded_as_run_failed():
    import copy

    from policy.loader import load_policy

    store, reader, client = _store_and_reader()
    broken_policy = copy.deepcopy(load_policy())
    del broken_policy["scoring"]["action_effects"]["RELEASE_PAYMENT"]
    del broken_policy["scoring"]["action_effects"]["HOLD_RELATED_ACTIONS"]

    outcome = run_pipeline(
        store,
        external_case_id="case-weigh-fail",
        entity_type="order_vendor",
        agent_a=PAYOUTS,
        agent_b=DISPUTE,
        case_context={"case_id": "case-weigh-fail"},
        policy=broken_policy,
    )

    assert outcome.failed is True
    assert outcome.failed_stage == "WEIGH"
    assert outcome.case_run["status"] == "FAILED"
    assert client.rows("weigh_results") == []
    assert client.rows("govern_results") == []

    events = reader.list_audit_events(outcome.case_run["id"])
    assert events[-1]["stage"] == "RUN_FAILED"
    assert events[-1]["detail"]["failed_stage"] == "WEIGH"


def test_rerun_of_the_same_case_creates_a_second_run():
    store, reader, client = _store_and_reader()
    kwargs = dict(
        external_case_id="case-Q",
        entity_type="order_vendor",
        agent_a=PAYOUTS,
        agent_b=DISPUTE,
        case_context={"case_id": "case-Q"},
    )
    first = run_pipeline(store, **kwargs)
    second = run_pipeline(store, **kwargs)

    assert first.case["id"] == second.case["id"]
    assert first.case_run["id"] != second.case_run["id"]
    assert len(client.rows("cases")) == 1
    assert len(client.rows("case_runs")) == 2
