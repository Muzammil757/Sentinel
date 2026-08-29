"""
Mapping logic against REAL pipeline output -- no live database involved.
Every fixture here runs the actual conflict_matrix/resolve/weigh/govern/
executor code, so a mapper drifting from what those layers actually emit
fails a test rather than silently persisting the wrong shape.
"""

import pytest

from persistence import mappers
from persistence.conftest import (
    full_run_ambiguous,
    full_run_escalated_release,
    full_run_payout_vs_dispute,
)
from persistence.errors import PersistenceError


# --- agent_outputs -----------------------------------------------------------


def test_map_agent_outputs_assigns_roles_and_preserves_payload():
    run = full_run_payout_vs_dispute()
    rows = mappers.map_agent_outputs(run["agent_actions"], "payouts", "dispute")

    by_name = {row["agent_name"]: row for row in rows}
    assert by_name["payouts"]["role"] == "agent_a"
    assert by_name["dispute"]["role"] == "agent_b"
    assert by_name["payouts"]["proposed_action"] == "RELEASE_PAYMENT"
    assert by_name["payouts"]["confidence"] == 0.95
    # The full agent payload, verbatim -- not reconstructed from the three
    # promoted columns.
    assert by_name["payouts"]["payload"] == run["agent_actions"]["payouts"]
    assert by_name["dispute"]["payload"] == run["agent_actions"]["dispute"]


def test_map_agent_outputs_tags_extra_agents():
    agent_actions = {
        "rto": {"agent": "rto", "proposed_action": "HOLD_ORDER", "confidence": 0.9},
        "retention": {"agent": "retention", "proposed_action": "WIN_BACK_OFFER", "confidence": 0.9},
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.9},
    }
    rows = mappers.map_agent_outputs(agent_actions, "rto", "retention")
    roles = {row["agent_name"]: row["role"] for row in rows}
    assert roles == {"rto": "agent_a", "retention": "agent_b", "payouts": "extra"}


# --- conflicts ---------------------------------------------------------------


def test_map_conflict_fields():
    run = full_run_payout_vs_dispute()
    row = mappers.map_conflict(run["conflict_result"])
    assert row["action_a"] == "RELEASE_PAYMENT"
    assert row["action_b"] == "HOLD_RELATED_ACTIONS"
    assert row["conflict"] is True
    assert row["reason"] == run["conflict_result"]["reason"]


# --- candidates ----------------------------------------------------------


def test_map_candidates_preserves_resolve_substance_and_order():
    run = full_run_payout_vs_dispute()
    resolve_candidates = run["resolve_output"]["candidates"]
    rows = mappers.map_candidates(resolve_candidates)

    assert [row["candidate_id"] for row in rows] == [c["candidate_id"] for c in resolve_candidates]
    for row, candidate in zip(rows, resolve_candidates):
        assert row["strategy"] == candidate["strategy"]
        assert row["preferred_agent"] == candidate["preferred_agent"]
        assert row["resulting_actions"] == candidate["resulting_actions"]
        assert row["rationale"] == candidate["rationale"]
        assert row["source_rule"] == candidate["source_rule"]


def test_map_candidates_empty_resulting_actions_for_hold_both():
    run = full_run_payout_vs_dispute()
    rows = mappers.map_candidates(run["resolve_output"]["candidates"])
    hold_both = next(r for r in rows if r["strategy"] == "HOLD_BOTH_PENDING_REVIEW")
    assert hold_both["resulting_actions"] == []


# --- candidate_scores ------------------------------------------------------


def test_map_candidate_scores_joins_rank_from_ranking():
    run = full_run_payout_vs_dispute()
    weigh_output = run["weigh_output"]
    candidate_row_ids = {c["candidate_id"]: f"row-{i}" for i, c in enumerate(weigh_output["candidates"])}

    rows = mappers.map_candidate_scores(weigh_output, candidate_row_ids)

    ranking_by_id = {entry["candidate_id"]: entry for entry in weigh_output["ranking"]}
    for candidate, row in zip(weigh_output["candidates"], rows):
        ranking = ranking_by_id[candidate["candidate_id"]]
        assert row["candidate_row_id"] == candidate_row_ids[candidate["candidate_id"]]
        assert row["total_score"] == candidate["total_score"] == ranking["total_score"]
        assert row["rank"] == ranking["rank"]
        assert row["score_rank"] == ranking["score_rank"]
        assert row["tie_group"] == ranking["tie_group"]
        assert row["eligible"] == candidate["eligible"]
        assert row["objective_impacts"] == candidate["objective_impacts"]
        assert row["constraint_findings"] == candidate["constraint_findings"]


def test_map_candidate_scores_raises_on_missing_row_id():
    run = full_run_payout_vs_dispute()
    with pytest.raises(PersistenceError, match="candidate row id"):
        mappers.map_candidate_scores(run["weigh_output"], candidate_row_ids={})


# --- weigh_results ----------------------------------------------------------


def test_map_weigh_result_uses_profile_name_not_selected():
    run = full_run_payout_vs_dispute()
    weigh_output = run["weigh_output"]
    row = mappers.map_weigh_result(weigh_output)

    assert row["profile_name"] == weigh_output["profile"]["profile_name"] == "standard"
    assert "profile_selected" not in row
    assert row["profile_reason"] == weigh_output["profile"]["reason"]
    assert row["case_confidence"] == weigh_output["evidence"]["case_confidence"]
    assert row["ambiguity_detected"] == weigh_output["ambiguity"]["detected"]


def test_map_weigh_result_raw_output_is_the_verbatim_document():
    run = full_run_payout_vs_dispute()
    weigh_output = run["weigh_output"]
    row = mappers.map_weigh_result(weigh_output)
    assert row["raw_output"] == weigh_output
    assert row["raw_output"] is weigh_output


# --- govern_results ----------------------------------------------------------


def test_map_govern_result_resolves_selected_candidate_link():
    run = full_run_payout_vs_dispute()
    govern_output = run["govern_output"]
    assert govern_output["outcome"] == "PROCEED"

    candidate_row_ids = {"defer_to_agent-1": "row-a", "hold_both_pending_review-2": "row-b"}
    row = mappers.map_govern_result(govern_output, candidate_row_ids)

    assert row["decision_id"] == govern_output["decision_id"]
    assert row["outcome"] == "PROCEED"
    assert row["execution_authorized"] is True
    assert row["selected_candidate_row_id"] == "row-a"
    assert row["authorized_actions"] == ["HOLD_RELATED_ACTIONS"]
    assert row["raw_output"] == govern_output


def test_map_govern_result_null_selected_candidate_on_non_proceed():
    run = full_run_escalated_release()
    govern_output = run["govern_output"]
    assert govern_output["outcome"] != "PROCEED"
    assert govern_output["selected_candidate"] is None

    candidate_row_ids = {
        c["candidate_id"]: f"row-{i}" for i, c in enumerate(govern_output["permission_evaluation"]["candidates"])
    }
    row = mappers.map_govern_result(govern_output, candidate_row_ids)

    assert row["selected_candidate_row_id"] is None
    assert row["execution_authorized"] is False
    assert row["authorized_actions"] == []


def test_map_govern_result_raises_on_missing_selected_candidate_link():
    run = full_run_payout_vs_dispute()
    with pytest.raises(PersistenceError, match="selected_candidate"):
        mappers.map_govern_result(run["govern_output"], candidate_row_ids={})


def test_map_govern_result_raises_on_missing_candidate_under_review_link():
    run = full_run_ambiguous()
    govern_output = run["govern_output"]
    assert govern_output["outcome"] == "AMBIGUOUS"
    assert govern_output["selected_candidate"] is None
    assert govern_output["candidate_under_review"] is not None
    with pytest.raises(PersistenceError, match="candidate_under_review"):
        mappers.map_govern_result(govern_output, candidate_row_ids={})


# --- execution_receipts -----------------------------------------------------


def test_map_execution_receipt_executed():
    run = full_run_payout_vs_dispute()
    receipt = run["receipt"]
    assert receipt["status"] == "EXECUTED"

    row = mappers.map_execution_receipt(receipt, govern_result_id="gov-row-1")
    assert row["govern_result_id"] == "gov-row-1"
    assert row["receipt_id"] == receipt["receipt_id"]
    assert row["status"] == "EXECUTED"
    assert row["rejection"] is None
    assert row["executed_actions"] == receipt["executed_actions"]
    assert row["raw_output"] == receipt


def test_map_execution_receipt_rejected_never_becomes_executed():
    run = full_run_escalated_release()
    receipt = run["receipt"]
    assert receipt["status"] == "REJECTED"

    row = mappers.map_execution_receipt(receipt, govern_result_id="gov-row-2")
    assert row["status"] == "REJECTED"
    assert row["rejection"] is not None
    assert row["executed_actions"] == []
    assert row["raw_output"]["status"] == "REJECTED"


# --- case_runs ---------------------------------------------------------------


def test_map_case_run_fields():
    run = full_run_payout_vs_dispute()
    row = mappers.map_case_run(
        case_id="case-row-id",
        resolve_output=run["resolve_output"],
        case_context=run["case_context"],
        policy_id=run["weigh_output"]["policy_id"],
        policy_version=run["weigh_output"]["policy_version"],
        policy_hash=run["weigh_output"]["policy_hash"],
    )
    assert row["case_id"] == "case-row-id"
    assert row["entity_type"] == "order_vendor"
    assert row["agent_a"] == "payouts"
    assert row["agent_b"] == "dispute"
    assert row["conflict"] is True
    assert row["unresolved"] is False
    assert row["case_context"] == run["case_context"]
    assert row["status"] == "IN_PROGRESS"


def test_map_case_run_status_is_overridable():
    run = full_run_payout_vs_dispute()
    row = mappers.map_case_run(
        "case-row-id",
        run["resolve_output"],
        run["case_context"],
        "p",
        "v",
        "h",
        status="PROCEED",
    )
    assert row["status"] == "PROCEED"


# --- candidate_row_id_map -----------------------------------------------------


def test_candidate_row_id_map_builds_from_inserted_rows():
    rows = [{"id": "uuid-1", "candidate_id": "defer_to_agent-1"}, {"id": "uuid-2", "candidate_id": "hold_both_pending_review-2"}]
    assert mappers.candidate_row_id_map(rows) == {
        "defer_to_agent-1": "uuid-1",
        "hold_both_pending_review-2": "uuid-2",
    }


# --- human_reviews ------------------------------------------------------------


def test_map_human_review_is_pure_annotation():
    row = mappers.map_human_review("approve", "reviewer-1", "looks right", "PROCEED")
    assert row == {
        "action": "approve",
        "reviewer": "reviewer-1",
        "reason": "looks right",
        "case_run_status_at_review": "PROCEED",
    }
    # No key here can feed back into execution_authorized or an outcome.
    assert "execution_authorized" not in row
    assert "outcome" not in row


def test_map_human_review_allows_null_reviewer_and_reason():
    row = mappers.map_human_review("request_more_evidence", None, None, "AMBIGUOUS")
    assert row["reviewer"] is None
    assert row["reason"] is None
