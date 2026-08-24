"""
Design §R: the same evidence, evaluated under two different policy files,
must produce a different WEIGH result with zero application-code changes.
This is the buildathon demo's central claim -- Sentinel is policy-driven,
not a collection of hard-coded if/else rules -- so it gets its own file.
"""

import copy

from policy.loader import compute_policy_hash, load_policy
from weigh import evaluate_candidates


def _policy():
    return load_policy()


def _payout_vs_dispute_case():
    resolve_output = {
        "entity_type": "order_vendor",
        "agent_a": "payouts",
        "agent_b": "dispute",
        "conflict": True,
        "unresolved": False,
        "candidates": [
            {
                "candidate_id": "defer_to_agent-1",
                "strategy": "DEFER_TO_AGENT",
                "preferred_agent": "dispute",
                "resulting_actions": ["HOLD_RELATED_ACTIONS"],
                "rationale": "r1",
                "source_rule": "release_payment_vs_hold_related_actions",
            },
            {
                "candidate_id": "hold_both_pending_review-2",
                "strategy": "HOLD_BOTH_PENDING_REVIEW",
                "preferred_agent": None,
                "resulting_actions": [],
                "rationale": "r2",
                "source_rule": "release_payment_vs_hold_related_actions",
            },
        ],
    }
    agent_actions = {
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.95},
        "dispute": {
            "agent": "dispute",
            "proposed_action": "HOLD_RELATED_ACTIONS",
            "confidence": 0.95,
            "dispute_status": "OPEN",
        },
    }
    return resolve_output, agent_actions


def _hold_order_vs_win_back_case_with_counterfactual():
    """
    A three-candidate fixture standing in for RESOLVE's optional
    `defer_to_agent-2` addendum (design §C.4): the counterfactual
    DEFER_TO_AGENT candidate that favors retention instead of rto. RESOLVE
    itself was not modified for this task -- WEIGH only consumes whatever
    shape of resolve_output it is given, so this proves WEIGH's own
    behavior (§R.2/§R.3 full ranking reversal) without touching RESOLVE.
    """
    resolve_output = {
        "entity_type": "customer",
        "agent_a": "rto",
        "agent_b": "retention",
        "conflict": True,
        "unresolved": False,
        "candidates": [
            {
                "candidate_id": "defer_to_agent-1",
                "strategy": "DEFER_TO_AGENT",
                "preferred_agent": "rto",
                "resulting_actions": ["HOLD_ORDER"],
                "rationale": "r1",
                "source_rule": "hold_order_vs_win_back_offer",
            },
            {
                "candidate_id": "defer_to_agent-2",
                "strategy": "DEFER_TO_AGENT",
                "preferred_agent": "retention",
                "resulting_actions": ["WIN_BACK_OFFER"],
                "rationale": "r2",
                "source_rule": "hold_order_vs_win_back_offer",
            },
            {
                "candidate_id": "hold_both_pending_review-2",
                "strategy": "HOLD_BOTH_PENDING_REVIEW",
                "preferred_agent": None,
                "resulting_actions": [],
                "rationale": "r3",
                "source_rule": "hold_order_vs_win_back_offer",
            },
        ],
    }
    agent_actions = {
        "rto": {"agent": "rto", "proposed_action": "HOLD_ORDER", "confidence": 0.95},
        # amount supplied (within retention's 5000 cap) so HC_UNAUTHORIZED_ACTION
        # resolves to SATISFIED rather than INDETERMINATE -- this fixture is
        # about the ranking reversal from re-weighting, not constraint findings.
        "retention": {"agent": "retention", "proposed_action": "WIN_BACK_OFFER", "confidence": 0.95, "amount": 3000},
    }
    return resolve_output, agent_actions


def test_ambiguity_threshold_change_flips_detection_with_identical_scores():
    # Design §R.1: change one number in policy (near_tie_threshold), same
    # evidence, same code -- only the ambiguity signal changes.
    resolve_output, agent_actions = _payout_vs_dispute_case()

    policy_before = _policy()
    before = evaluate_candidates(resolve_output, agent_actions, {}, policy_before)

    policy_after = copy.deepcopy(policy_before)
    policy_after["ambiguity"]["near_tie_threshold"] = 0.15
    after = evaluate_candidates(resolve_output, agent_actions, {}, policy_after)

    before_scores = {c["candidate_id"]: c["total_score"] for c in before["candidates"]}
    after_scores = {c["candidate_id"]: c["total_score"] for c in after["candidates"]}
    assert before_scores == after_scores

    assert before["ambiguity"]["detected"] is False
    assert after["ambiguity"]["detected"] is True
    assert before["policy_hash"] != after["policy_hash"]
    assert before["policy_hash"] == compute_policy_hash(policy_before)
    assert after["policy_hash"] == compute_policy_hash(policy_after)


def test_reweighting_standard_profile_reverses_the_ranking():
    # Design §R.2/§R.3: re-weighting "standard" toward merchant_trust
    # flips the winner from HOLD_ORDER to WIN_BACK_OFFER -- a full ranking
    # reversal from one policy edit, zero application-code changes.
    resolve_output, agent_actions = _hold_order_vs_win_back_case_with_counterfactual()
    # merchant_flags known and empty, so HC_RETENTION_TO_FLAGGED_MERCHANT
    # resolves to SATISFIED rather than INDETERMINATE -- this test is about
    # the ranking reversal from re-weighting, not constraint findings.
    case_context = {"merchant_flags": []}

    policy_before = _policy()
    before = evaluate_candidates(resolve_output, agent_actions, case_context, policy_before)
    before_ranking = [r["candidate_id"] for r in before["ranking"]]
    assert before_ranking[0] == "defer_to_agent-1"  # HOLD_ORDER wins under standard weights

    policy_after = copy.deepcopy(policy_before)
    policy_after["weights"]["profiles"]["standard"] = {
        "financial_exposure_prevention": 0.25,
        "fraud_risk_reduction": 0.15,
        "compliance_risk_reduction": 0.15,
        "merchant_trust": 0.35,
        "operational_cost": 0.10,
    }
    after = evaluate_candidates(resolve_output, agent_actions, case_context, policy_after)
    after_ranking = [r["candidate_id"] for r in after["ranking"]]
    assert after_ranking[0] == "defer_to_agent-2"  # WIN_BACK_OFFER now wins

    assert before_ranking != after_ranking
    assert before["policy_hash"] != after["policy_hash"]


def test_policy_hash_is_stable_when_policy_is_unchanged():
    resolve_output, agent_actions = _payout_vs_dispute_case()
    policy = _policy()

    result_1 = evaluate_candidates(resolve_output, agent_actions, {}, policy)
    result_2 = evaluate_candidates(resolve_output, agent_actions, {}, _policy())

    assert result_1["policy_hash"] == result_2["policy_hash"]
