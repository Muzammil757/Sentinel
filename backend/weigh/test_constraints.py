import pytest

from mock_agents.rto import generate_rto_action
from policy.loader import load_policy
from weigh.constraints import CONSTRAINT_EVALUATORS, evaluate_constraints_for_candidate
from weigh.errors import WeighPolicyError

POLICY = load_policy()
HARD_CONSTRAINTS = POLICY["hard_constraints"]


def _run(candidate, agent_actions, case_context=None, originating_confidence=0.90):
    return evaluate_constraints_for_candidate(
        candidate, agent_actions, case_context or {}, HARD_CONSTRAINTS, POLICY, originating_confidence
    )


def _finding_for(findings, constraint_id):
    return next(f for f in findings if f["constraint_id"] == constraint_id)


# ---------------------------------------------------------------------------
# HC_PAYOUT_DURING_CHARGEBACK
# ---------------------------------------------------------------------------


def test_payout_during_open_chargeback_is_violated():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"dispute": {"dispute_status": "OPEN"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_PAYOUT_DURING_CHARGEBACK")["status"] == "VIOLATED"
    assert eligible is False


def test_payout_after_closed_dispute_is_satisfied():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"dispute": {"dispute_status": "CLOSED"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_PAYOUT_DURING_CHARGEBACK")["status"] == "SATISFIED"


def test_payout_constraint_not_applicable_without_release_payment():
    candidate = {"resulting_actions": ["HOLD_RELATED_ACTIONS"]}
    agent_actions = {"dispute": {"dispute_status": "OPEN"}}
    findings, _eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_PAYOUT_DURING_CHARGEBACK")["status"] == "NOT_APPLICABLE"


def test_payout_constraint_indeterminate_without_dispute_evidence():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_PAYOUT_DURING_CHARGEBACK")["status"] == "INDETERMINATE"
    assert eligible is False


# ---------------------------------------------------------------------------
# HC_THIRDWATCH_HIGH_RISK_PAYOUT -- must defer to the RTO agent's own
# published verdict, never re-derive a band from rto_score itself.
# ---------------------------------------------------------------------------


def test_thirdwatch_blocks_payout_when_rto_agent_holds_order():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"rto": {"proposed_action": "HOLD_ORDER"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "VIOLATED"
    assert eligible is False


def test_thirdwatch_allows_payout_when_rto_agent_allows_order():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"rto": {"proposed_action": "ALLOW_ORDER"}}
    findings, _eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "SATISFIED"


def test_thirdwatch_defers_to_agent_verdict_not_raw_rto_score():
    # rto_score=0.95 would normally yield HOLD_ORDER, but the evaluator must
    # read proposed_action, not re-threshold rto_score itself. Forcing a
    # mismatched proposed_action proves WEIGH has no second risk classifier.
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"rto": {"proposed_action": "ALLOW_ORDER", "rto_score": 0.95}}
    findings, _eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "SATISFIED"


def test_thirdwatch_mirrors_rto_agents_own_published_band():
    # Behavioral mirror-consistency check (design §I.8 / §P test 35): drive
    # the *real* mock RTO agent across its band boundary and confirm the
    # constraint's verdict tracks the agent's own proposed_action, so the
    # two cannot silently drift apart.
    below = generate_rto_action(order_id="o1", customer_id="c1", rto_score=0.74, shipment_status="in_transit")
    at_or_above = generate_rto_action(order_id="o1", customer_id="c1", rto_score=0.75, shipment_status="in_transit")

    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}

    findings_below, _e = _run(candidate, {"rto": below})
    findings_at, _e2 = _run(candidate, {"rto": at_or_above})

    assert _finding_for(findings_below, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "SATISFIED"
    assert _finding_for(findings_at, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "VIOLATED"


def test_thirdwatch_not_applicable_without_release_payment():
    candidate = {"resulting_actions": ["HOLD_ORDER"]}
    agent_actions = {"rto": {"proposed_action": "HOLD_ORDER"}}
    findings, _eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_THIRDWATCH_HIGH_RISK_PAYOUT")["status"] == "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# HC_RETENTION_TO_FLAGGED_MERCHANT
# ---------------------------------------------------------------------------


def test_retention_to_flagged_merchant_is_violated():
    candidate = {"resulting_actions": ["WIN_BACK_OFFER"]}
    findings, eligible = _run(candidate, {}, case_context={"merchant_flags": ["FRAUD_REVIEW"]})
    assert _finding_for(findings, "HC_RETENTION_TO_FLAGGED_MERCHANT")["status"] == "VIOLATED"
    assert eligible is False


def test_retention_to_unflagged_merchant_is_satisfied():
    candidate = {"resulting_actions": ["WIN_BACK_OFFER"]}
    findings, _eligible = _run(candidate, {}, case_context={"merchant_flags": []})
    assert _finding_for(findings, "HC_RETENTION_TO_FLAGGED_MERCHANT")["status"] == "SATISFIED"


def test_retention_constraint_indeterminate_without_merchant_flags_evidence():
    candidate = {"resulting_actions": ["WIN_BACK_OFFER"]}
    findings, eligible = _run(candidate, {}, case_context={})
    assert _finding_for(findings, "HC_RETENTION_TO_FLAGGED_MERCHANT")["status"] == "INDETERMINATE"
    assert eligible is False


def test_retention_constraint_not_applicable_without_win_back_offer():
    candidate = {"resulting_actions": ["RETENTION_MESSAGE"]}
    findings, _eligible = _run(candidate, {}, case_context={"merchant_flags": ["FRAUD_REVIEW"]})
    assert _finding_for(findings, "HC_RETENTION_TO_FLAGGED_MERCHANT")["status"] == "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# HC_CONFIDENCE_FLOOR -- and the "no action, no violation" invariant
# ---------------------------------------------------------------------------


def test_confidence_below_floor_is_violated():
    candidate = {"resulting_actions": ["HOLD_RELATED_ACTIONS"]}
    findings, eligible = _run(candidate, {}, originating_confidence=0.10)
    assert _finding_for(findings, "HC_CONFIDENCE_FLOOR")["status"] == "VIOLATED"
    assert eligible is False


def test_confidence_at_or_above_floor_is_satisfied():
    candidate = {"resulting_actions": ["HOLD_RELATED_ACTIONS"]}
    findings, _eligible = _run(candidate, {}, originating_confidence=0.60)
    assert _finding_for(findings, "HC_CONFIDENCE_FLOOR")["status"] == "SATISFIED"


def test_confidence_floor_not_applicable_when_no_resulting_actions():
    # design §I.5: the conservative fallback must never be blocked by weak
    # evidence, or uncertainty would make holding unavailable.
    candidate = {"resulting_actions": []}
    findings, eligible = _run(candidate, {}, originating_confidence=0.0)
    assert _finding_for(findings, "HC_CONFIDENCE_FLOOR")["status"] == "NOT_APPLICABLE"
    assert eligible is True


def test_no_action_candidate_is_not_applicable_for_every_constraint():
    candidate = {"resulting_actions": []}
    agent_actions = {"dispute": {"dispute_status": "OPEN"}, "rto": {"proposed_action": "HOLD_ORDER"}}
    findings, eligible = _run(
        candidate, agent_actions, case_context={"merchant_flags": ["FRAUD_REVIEW"]}, originating_confidence=0.0
    )
    assert all(f["status"] == "NOT_APPLICABLE" for f in findings)
    assert eligible is True


# ---------------------------------------------------------------------------
# HC_UNAUTHORIZED_ACTION
# ---------------------------------------------------------------------------


def test_authorized_action_within_amount_limit_is_satisfied():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    # dispute/rto evidence supplied so the *other* RELEASE_PAYMENT-gated
    # constraints resolve to SATISFIED rather than INDETERMINATE, isolating
    # this assertion to HC_UNAUTHORIZED_ACTION's own behavior.
    agent_actions = {
        "payouts": {"proposed_action": "RELEASE_PAYMENT", "amount": 1000},
        "dispute": {"dispute_status": "CLOSED"},
        "rto": {"proposed_action": "ALLOW_ORDER"},
    }
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "SATISFIED"
    assert eligible is True


def test_action_exceeding_max_autonomous_amount_is_violated():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"payouts": {"proposed_action": "RELEASE_PAYMENT", "amount": 999999}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "VIOLATED"
    assert eligible is False


def test_action_outside_autonomous_actions_is_violated():
    candidate = {"resulting_actions": ["WIN_BACK_OFFER"]}
    agent_actions = {"payouts": {"proposed_action": "WIN_BACK_OFFER"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "VIOLATED"
    assert eligible is False


def test_amount_required_but_missing_is_indeterminate():
    # retention's WIN_BACK_OFFER has a max_autonomous_amount of 5000, but
    # the mock retention agent publishes no "amount" field -- design §I.7.
    candidate = {"resulting_actions": ["WIN_BACK_OFFER"]}
    agent_actions = {"retention": {"proposed_action": "WIN_BACK_OFFER"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "INDETERMINATE"
    assert eligible is False


def test_action_with_no_authority_entry_is_violated():
    candidate = {"resulting_actions": ["SOME_ACTION"]}
    agent_actions = {"unknown_agent": {"proposed_action": "SOME_ACTION"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "VIOLATED"
    assert eligible is False


def test_ambiguous_action_attribution_is_indeterminate():
    candidate = {"resulting_actions": ["SAME_ACTION"]}
    agent_actions = {
        "payouts": {"proposed_action": "SAME_ACTION"},
        "dispute": {"proposed_action": "SAME_ACTION"},
    }
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "INDETERMINATE"
    assert eligible is False


def test_no_amount_limit_agent_is_satisfied_without_amount_field():
    candidate = {"resulting_actions": ["HOLD_RELATED_ACTIONS"]}
    agent_actions = {"dispute": {"proposed_action": "HOLD_RELATED_ACTIONS"}}
    findings, eligible = _run(candidate, agent_actions)
    assert _finding_for(findings, "HC_UNAUTHORIZED_ACTION")["status"] == "SATISFIED"
    assert eligible is True


# ---------------------------------------------------------------------------
# Registry / fail-closed behavior
# ---------------------------------------------------------------------------


def test_every_required_hard_constraint_has_a_registered_evaluator():
    for constraint in HARD_CONSTRAINTS:
        assert constraint["id"] in CONSTRAINT_EVALUATORS


def test_missing_min_confidence_parameter_raises_policy_error():
    broken_constraint = dict(HARD_CONSTRAINTS[3])
    assert broken_constraint["id"] == "HC_CONFIDENCE_FLOOR"
    broken_constraint["parameters"] = {}
    broken_constraints = list(HARD_CONSTRAINTS)
    broken_constraints[3] = broken_constraint

    candidate = {"resulting_actions": ["HOLD_RELATED_ACTIONS"]}
    with pytest.raises(WeighPolicyError):
        evaluate_constraints_for_candidate(candidate, {}, {}, broken_constraints, POLICY, 0.90)


def test_advisory_flag_is_always_true():
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}
    agent_actions = {"dispute": {"dispute_status": "OPEN"}, "payouts": {"proposed_action": "RELEASE_PAYMENT"}}
    findings, _eligible = _run(candidate, agent_actions)
    assert all(f["advisory"] is True for f in findings)


def test_source_field_is_stamped_by_index():
    candidate = {"resulting_actions": []}
    findings, _eligible = _run(candidate, {})
    for index, finding in enumerate(findings):
        assert finding["source"] == f"policy.hard_constraints[{index}]"
