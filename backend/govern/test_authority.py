"""
Phase 2: authority enforcement (design §H).

This is the half of governance WEIGH deliberately never touched -- per-agent
caps, the `actions_requiring_escalation` flag (which currently holds a
strategy, not an action), and the `actions_requiring_governance` gate.
"""

import copy

from govern import decide
from govern.authority import authority_exceeded_codes, evaluate_authority
from govern.conftest import (
    no_conflict_release_case,
    payout_vs_dispute_case,
    real_policy,
    unresolved_case,
)


def _record(output, candidate_id):
    return next(
        record
        for record in output["permission_evaluation"]["candidates"]
        if record["candidate_id"] == candidate_id
    )


# --- per-agent limits ------------------------------------------------------


def test_amount_cap_is_inclusive():
    # amount > max_autonomous_amount is the violation test, so payouts'
    # 50 000 cap authorizes 50 000 and refuses 50 001.
    authorized = decide(*no_conflict_release_case(50000))
    refused = decide(*no_conflict_release_case(50001))

    assert authorized["execution_authorized"] is True
    assert (
        _record(authorized, "no_conflict_proceed-1")["authority"]["per_action"][
            "RELEASE_PAYMENT"
        ]
        == {"agent": "payouts", "result": "AUTHORIZED", "reason": "within_amount_limit"}
    )

    assert refused["execution_authorized"] is False
    assert (
        _record(refused, "no_conflict_proceed-1")["authority"]["per_action"]["RELEASE_PAYMENT"]
        == {
            "agent": "payouts",
            "result": "NOT_AUTHORIZED",
            "reason": "amount_exceeds_max_autonomous_amount",
        }
    )


def test_no_conflict_release_over_cap_escalates_with_a_named_reason():
    output = decide(*no_conflict_release_case(50001))

    assert output["outcome"] == "ESCALATE"
    assert output["execution_authorized"] is False
    assert "AUTHORITY_EXCEEDED:payouts:RELEASE_PAYMENT" in output["escalation"]["reasons"]
    assert "HC_UNAUTHORIZED_ACTION:VIOLATED" in output["escalation"]["reasons"]


def test_raising_the_cap_in_policy_authorizes_the_same_release():
    # The boundary is policy data, not application code.
    relaxed = copy.deepcopy(real_policy())
    relaxed["authority"]["agents"]["payouts"]["max_autonomous_amount"] = 100000

    output = decide(*no_conflict_release_case(50001, policy=relaxed))

    assert output["outcome"] == "PROCEED"
    assert output["execution_authorized"] is True
    assert output["authorized_actions"] == ["RELEASE_PAYMENT", "CLOSE_CASE"]


def test_agent_with_no_authority_entry_is_a_determinate_refusal():
    stripped = copy.deepcopy(real_policy())
    del stripped["authority"]["agents"]["dispute"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=stripped)
    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "defer_to_agent-1")

    entry = record["authority"]["per_action"]["HOLD_RELATED_ACTIONS"]
    assert entry["result"] == "NOT_AUTHORIZED"
    assert entry["reason"] == "agent_has_no_authority_entry"
    assert record["permitted"] is False


def test_authority_exceeded_codes_ignores_unattributable_actions():
    # An action GOVERN cannot attribute to exactly one agent is reported
    # through the constraint's INDETERMINATE code, not as "agent X exceeded".
    block = {
        "per_action": {
            "A": {"agent": None, "result": "INDETERMINATE", "reason": "ambiguous"},
            "B": {"agent": "payouts", "result": "NOT_AUTHORIZED", "reason": "capped"},
        }
    }
    assert authority_exceeded_codes(block) == ["AUTHORITY_EXCEEDED:payouts:B"]


# --- actions_requiring_escalation: strategy AND actions --------------------


def test_escalation_matches_strategy_not_just_action():
    # HOLD_BOTH_PENDING_REVIEW is a RESOLVE strategy sitting in a field named
    # for actions. Matching it against resulting_actions alone would match
    # nothing, ever.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    assert policy["authority"]["actions_requiring_escalation"] == ["HOLD_BOTH_PENDING_REVIEW"]

    output = decide(weigh_output, agent_actions, case_context, policy)
    flagged = _record(output, "hold_both_pending_review-2")

    assert flagged["authority"]["requires_escalation"] is True
    assert flagged["authority"]["escalation_matches"] == ["strategy:HOLD_BOTH_PENDING_REVIEW"]
    assert flagged["authority"]["escalation_match"] == "strategy:HOLD_BOTH_PENDING_REVIEW"


def test_flagged_candidate_stays_permitted_but_is_never_selected():
    # Evaluated at selection, not at set membership: excluding the flagged
    # candidate would delete the conservative fallback from the comparison,
    # which is exactly backwards.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert "hold_both_pending_review-2" in output["permission_evaluation"][
        "permitted_candidate_ids"
    ]
    assert output["selected_candidate"]["candidate_id"] == "defer_to_agent-1"
    assert output["outcome"] == "PROCEED"
    # The case-level escalation did NOT fire, because the flagged candidate
    # is not permitted[0].
    assert output["escalation"]["required"] is False


def test_flagged_candidate_at_the_top_escalates_the_case():
    # Block the DEFER_TO_AGENT candidate so the flagged fallback rises to the
    # top of the permitted order; D3 then fires.
    stripped = copy.deepcopy(real_policy())
    stripped["authority"]["agents"]["dispute"]["autonomous_actions"] = ["CLOSE_CASE"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=stripped)
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["permission_evaluation"]["permitted_candidate_ids"] == [
        "hold_both_pending_review-2"
    ]
    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "ACTION_REQUIRES_ESCALATION"
    assert output["execution_authorized"] is False
    assert output["candidate_under_review"] == "hold_both_pending_review-2"
    assert output["escalation"]["escalation_matches"] == ["strategy:HOLD_BOTH_PENDING_REVIEW"]
    assert (
        "ACTION_REQUIRES_ESCALATION:strategy:HOLD_BOTH_PENDING_REVIEW"
        in output["escalation"]["reasons"]
    )


def test_unresolved_case_escalates():
    # RESOLVE's unresolved path: hold_both_pending_review-1 is the sole
    # candidate, it is permitted, it carries the flag, so D3 fires.
    weigh_output, agent_actions, case_context, policy = unresolved_case()
    assert weigh_output["case"]["unresolved"] is True
    assert [c["candidate_id"] for c in weigh_output["candidates"]] == [
        "hold_both_pending_review-1"
    ]

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "ACTION_REQUIRES_ESCALATION"
    assert output["execution_authorized"] is False
    assert output["candidate_under_review"] == "hold_both_pending_review-1"


def test_action_token_in_the_escalation_list_also_matches():
    flagged = copy.deepcopy(real_policy())
    flagged["authority"]["actions_requiring_escalation"] = ["HOLD_RELATED_ACTIONS"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=flagged)
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "ESCALATE"
    assert output["escalation"]["escalation_matches"] == ["action:HOLD_RELATED_ACTIONS"]


def test_proposed_strategies_requiring_escalation_field_is_honoured():
    # Design §R.3 proposes moving the strategy token to its own field. GOVERN
    # reads both, so behaviour is identical before and after that correction.
    corrected = copy.deepcopy(real_policy())
    corrected["authority"]["actions_requiring_escalation"] = []
    corrected["authority"]["strategies_requiring_escalation"] = ["HOLD_BOTH_PENDING_REVIEW"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=corrected)
    output = decide(weigh_output, agent_actions, case_context, policy)
    flagged = _record(output, "hold_both_pending_review-2")

    assert flagged["authority"]["escalation_matches"] == ["strategy:HOLD_BOTH_PENDING_REVIEW"]


# --- actions_requiring_governance: the gate with teeth --------------------


def test_governance_gate_is_absent_for_ungated_candidates():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    for record in output["permission_evaluation"]["candidates"]:
        assert record["authority"]["requires_governance_actions"] == []
        assert record["governance_gate"] is None


def test_governance_gate_blocks_an_indeterminate_gated_action():
    # retention's 5 000 cap applies but the mock retention agent publishes no
    # amount, so WIN_BACK_OFFER is permanently indeterminate and therefore
    # never autonomously authorizable.
    policy = real_policy()
    weigh_candidate = {
        "candidate_id": "synthetic-win-back",
        "strategy": "DEFER_TO_AGENT",
        "resulting_actions": ["WIN_BACK_OFFER"],
    }
    unauthorized_observed = {
        "WIN_BACK_OFFER": {
            "agent": "retention",
            "result": "INDETERMINATE",
            "reason": "amount_required_but_missing",
        }
    }
    block, gate, blocking = evaluate_authority(weigh_candidate, unauthorized_observed, policy)

    assert block["requires_governance_actions"] == ["WIN_BACK_OFFER"]
    assert gate["all_determinate"] is False
    assert gate["checks_run"]["amount_limit_evaluated"] is False
    assert blocking == ["GOVERNANCE_GATE_INDETERMINATE:WIN_BACK_OFFER"]


def test_governance_gate_calls_a_determinate_refusal_determinate():
    # An over-cap release is a governed "no", not an unanswered question: the
    # gate stays determinate and the candidate is blocked by the constraint.
    output = decide(*no_conflict_release_case(50001))
    record = _record(output, "no_conflict_proceed-1")

    assert record["governance_gate"]["all_determinate"] is True
    assert record["blocking_reasons"] == ["HC_UNAUTHORIZED_ACTION:VIOLATED"]


def test_gated_action_can_never_be_authorized_without_a_determinate_gate():
    # The receipt line a judge is shown: this release was governed, not
    # waved through.
    for amount in (10000, 50000):
        output = decide(*no_conflict_release_case(amount))
        assert output["execution_authorized"] is True
        assert "RELEASE_PAYMENT" in output["authorized_actions"]
        gate = _record(output, "no_conflict_proceed-1")["governance_gate"]
        assert gate is not None
        assert gate["all_determinate"] is True
        assert all(gate["checks_run"].values())


def test_adding_an_action_to_the_governance_list_adds_a_gate_record():
    extended = copy.deepcopy(real_policy())
    extended["authority"]["actions_requiring_governance"].append("HOLD_RELATED_ACTIONS")

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=extended)
    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "defer_to_agent-1")

    assert record["governance_gate"]["gated_actions"] == ["HOLD_RELATED_ACTIONS"]
    assert record["governance_gate"]["all_determinate"] is True
    assert output["escalation"]["actions_requiring_governance_matched"] == [
        "HOLD_RELATED_ACTIONS"
    ]
    assert output["outcome"] == "PROCEED"
