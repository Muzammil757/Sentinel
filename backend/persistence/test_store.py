"""
PersistenceStore against the in-memory FakeSupabaseClient. No live database
is used (see the final report's local-testing-strategy section) -- these
tests exercise insert/select/update call shape, FK linkage, and the
case/case_run/rerun semantics design section D and section J require.
"""

from persistence.conftest import (
    FakeSupabaseClient,
    full_run_ambiguous,
    full_run_escalated_release,
    full_run_payout_vs_dispute,
)
from persistence.store import PersistenceStore, candidate_row_id_map


def _persist_full_run(store, run, external_case_id):
    """
    Walk one full pipeline run through every store method, exactly the
    sequence docs/data_layer_design.md's Supabase implementation plan
    describes. Shared by several tests below.
    """

    case = store.get_or_create_case(external_case_id)
    case_run = store.create_case_run(
        case["id"],
        run["resolve_output"],
        run["case_context"],
        run["weigh_output"]["policy_id"],
        run["weigh_output"]["policy_version"],
        run["weigh_output"]["policy_hash"],
    )
    store.record_agent_outputs(case_run["id"], run["agent_actions"], run["resolve_output"]["agent_a"], run["resolve_output"]["agent_b"])
    store.record_conflict(case_run["id"], run["conflict_result"])
    candidate_rows = store.record_candidates(case_run["id"], run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    store.record_candidate_scores(run["weigh_output"], row_ids)
    store.record_weigh_result(case_run["id"], run["weigh_output"])
    govern_row = store.record_govern_result(case_run["id"], run["govern_output"], row_ids)
    store.update_case_run_status(case_run["id"], run["govern_output"]["outcome"])
    receipt_row = store.record_execution_receipt(case_run["id"], govern_row["id"], run["receipt"])
    return case, case_run, candidate_rows, govern_row, receipt_row


# --- case / case_run ----------------------------------------------------


def test_get_or_create_case_creates_new_case_without_external_id():
    store = PersistenceStore(FakeSupabaseClient())
    first = store.get_or_create_case(None)
    second = store.get_or_create_case(None)
    # Multiple cases with no external id coexist (design F.1); nothing forces
    # them to collapse into one row.
    assert first["id"] != second["id"]


def test_get_or_create_case_reuses_existing_external_id():
    store = PersistenceStore(FakeSupabaseClient())
    first = store.get_or_create_case("case-Q")
    second = store.get_or_create_case("case-Q")
    assert first["id"] == second["id"]


def test_get_or_create_case_distinguishes_different_external_ids():
    store = PersistenceStore(FakeSupabaseClient())
    a = store.get_or_create_case("case-A")
    b = store.get_or_create_case("case-B")
    assert a["id"] != b["id"]


def test_create_case_run_always_inserts_a_new_row():
    store = PersistenceStore(FakeSupabaseClient())
    run = full_run_payout_vs_dispute()
    case = store.get_or_create_case("case-Q")

    first_run = store.create_case_run(
        case["id"], run["resolve_output"], run["case_context"],
        run["weigh_output"]["policy_id"], run["weigh_output"]["policy_version"], run["weigh_output"]["policy_hash"],
    )
    second_run = store.create_case_run(
        case["id"], run["resolve_output"], run["case_context"],
        run["weigh_output"]["policy_id"], run["weigh_output"]["policy_version"], run["weigh_output"]["policy_hash"],
    )

    assert first_run["id"] != second_run["id"]
    assert first_run["case_id"] == second_run["case_id"] == case["id"]


def test_rerun_creates_a_second_case_run_never_overwrites_the_first():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    _persist_full_run(store, run, "case-Q")
    _persist_full_run(store, run, "case-Q")

    cases = client.rows("cases")
    case_runs = client.rows("case_runs")
    assert len(cases) == 1
    assert len(case_runs) == 2
    assert {r["case_id"] for r in case_runs} == {cases[0]["id"]}
    # The first run's govern_results/execution_receipts rows are untouched --
    # exactly one of each per case_run, not overwritten by the second run.
    assert len(client.rows("govern_results")) == 2
    assert len(client.rows("execution_receipts")) == 2


def test_update_case_run_status_is_the_only_mutation():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()
    case = store.get_or_create_case("case-Q")
    case_run = store.create_case_run(
        case["id"], run["resolve_output"], run["case_context"],
        run["weigh_output"]["policy_id"], run["weigh_output"]["policy_version"], run["weigh_output"]["policy_hash"],
    )
    assert case_run["status"] == "IN_PROGRESS"

    store.update_case_run_status(case_run["id"], "PROCEED")

    (updated,) = [r for r in client.rows("case_runs") if r["id"] == case_run["id"]]
    assert updated["status"] == "PROCEED"
    # Every other column is untouched.
    for key in case_run:
        if key != "status":
            assert updated[key] == case_run[key]


# --- agent_outputs / conflicts / candidates -------------------------------


def test_record_agent_outputs_are_linked_to_the_case_run():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()
    case_run_id = "case-run-1"

    rows = store.record_agent_outputs(case_run_id, run["agent_actions"], "payouts", "dispute")

    assert len(rows) == 2
    assert all(row["case_run_id"] == case_run_id for row in rows)
    assert {row["agent_name"] for row in rows} == {"payouts", "dispute"}


def test_record_candidates_returns_rows_with_ids_in_resolve_order():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    rows = store.record_candidates("case-run-1", run["resolve_output"]["candidates"])

    assert [row["candidate_id"] for row in rows] == [
        c["candidate_id"] for c in run["resolve_output"]["candidates"]
    ]
    assert all("id" in row and row["case_run_id"] == "case-run-1" for row in rows)


def test_record_candidate_scores_links_to_candidate_row_id():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    candidate_rows = store.record_candidates("case-run-1", run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    score_rows = store.record_candidate_scores(run["weigh_output"], row_ids)

    assert {row["candidate_row_id"] for row in score_rows} == set(row_ids.values())
    assert len(score_rows) == len(run["weigh_output"]["candidates"])


# --- weigh_results / govern_results / execution_receipts -------------------


def test_record_weigh_result_preserves_raw_output():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    row = store.record_weigh_result("case-run-1", run["weigh_output"])

    assert row["case_run_id"] == "case-run-1"
    assert row["raw_output"] == run["weigh_output"]
    assert row["profile_name"] == "standard"


def test_record_govern_result_proceed_links_selected_candidate():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    candidate_rows = store.record_candidates("case-run-1", run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    row = store.record_govern_result("case-run-1", run["govern_output"], row_ids)

    assert row["outcome"] == "PROCEED"
    assert row["execution_authorized"] is True
    selected_id = run["govern_output"]["selected_candidate"]["candidate_id"]
    assert row["selected_candidate_row_id"] == row_ids[selected_id]
    assert row["decision_id"] == run["govern_output"]["decision_id"]
    assert row["raw_output"] == run["govern_output"]


def test_record_govern_result_ambiguous_has_null_selected_candidate():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_ambiguous()

    candidate_rows = store.record_candidates("case-run-1", run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    row = store.record_govern_result("case-run-1", run["govern_output"], row_ids)

    assert row["outcome"] == "AMBIGUOUS"
    assert row["execution_authorized"] is False
    assert row["selected_candidate_row_id"] is None
    assert row["candidate_under_review_row_id"] is not None


def test_record_execution_receipt_executed():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    row = store.record_execution_receipt("case-run-1", "govern-row-1", run["receipt"])

    assert row["status"] == "EXECUTED"
    assert row["rejection"] is None
    assert row["govern_result_id"] == "govern-row-1"
    assert row["receipt_id"] == run["receipt"]["receipt_id"]


def test_record_execution_receipt_rejected_stays_rejected():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_escalated_release()
    assert run["receipt"]["status"] == "REJECTED"

    row = store.record_execution_receipt("case-run-1", "govern-row-1", run["receipt"])

    assert row["status"] == "REJECTED"
    assert row["rejection"] is not None
    assert row["executed_actions"] == []


# --- audit events ------------------------------------------------------------


def test_record_audit_event_is_linked_to_case_run():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    row = store.record_audit_event("case-run-1", "RUN_STARTED", "SUCCEEDED", "run started")
    assert row["case_run_id"] == "case-run-1"
    assert row["stage"] == "RUN_STARTED"
    assert row["outcome"] == "SUCCEEDED"


def test_record_run_failed_carries_error_detail():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    row = store.record_run_failed("case-run-1", "WEIGH", ValueError("bad policy"))

    assert row["stage"] == "RUN_FAILED"
    assert row["outcome"] == "FAILED"
    assert row["detail"]["failed_stage"] == "WEIGH"
    assert row["detail"]["error_type"] == "ValueError"
    assert row["detail"]["error_message"] == "bad policy"


# --- human review -------------------------------------------------------------


def test_record_human_review_is_linked_to_case_run():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    row = store.record_human_review("case-run-1", "approve", "reviewer-1", "looks right", "PROCEED")
    assert row["case_run_id"] == "case-run-1"
    assert row["action"] == "approve"
    assert row["reviewer"] == "reviewer-1"
    assert row["case_run_status_at_review"] == "PROCEED"


def test_record_human_review_never_touches_govern_or_execution_receipt_tables():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    store.record_human_review("case-run-1", "reject", None, "insufficient evidence", "HOLD")
    assert client.rows("govern_results") == []
    assert client.rows("execution_receipts") == []
    assert client.rows("case_runs") == []


# --- end-to-end reconstruction ------------------------------------------------


def test_full_run_reconstructs_via_the_faked_tables():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()

    case, case_run, candidate_rows, govern_row, receipt_row = _persist_full_run(store, run, "case-Q")

    assert len(client.rows("agent_outputs")) == 2
    assert len(client.rows("conflicts")) == 1
    assert len(candidate_rows) == len(run["resolve_output"]["candidates"])
    assert len(client.rows("candidate_scores")) == len(run["weigh_output"]["candidates"])
    assert len(client.rows("weigh_results")) == 1
    assert len(client.rows("govern_results")) == 1
    assert govern_row["outcome"] == "PROCEED"
    assert receipt_row["status"] == "EXECUTED"

    (stored_case_run,) = [r for r in client.rows("case_runs") if r["id"] == case_run["id"]]
    assert stored_case_run["case_id"] == case["id"]
