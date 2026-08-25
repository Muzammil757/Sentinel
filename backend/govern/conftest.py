"""
Shared GOVERN test fixtures.

Design §U.3: cases are built by running the REAL pipeline
(evaluate_agent_actions -> generate_resolution_candidates ->
evaluate_candidates), so the scores the GOVERN tests assert on stay honest
rather than being hand-written numbers that can drift from what WEIGH
actually produces. Each test then mutates one thing.

Advisor fakes are tiny local objects -- never a network client. There is no
`anthropic` dependency in this project and nothing here adds one.
"""

import copy

from conflict_matrix.integration import evaluate_agent_actions
from policy.loader import load_policy
from resolve.resolver import generate_resolution_candidates
from weigh import evaluate_candidates

from govern.advisor import AdvisorTimeout
from govern.schema import ADVISORY_VERSION


def real_policy():
    return load_policy()


def variant_policy(**threshold_overrides):
    """A deepcopy of the real policy with escalation.thresholds overridden.

    Mirrors weigh/test_policy_sensitivity.py: policy variants live in memory,
    the YAML on disk is never touched by a test.
    """

    policy = copy.deepcopy(load_policy())
    policy["escalation"]["thresholds"].update(threshold_overrides)
    return policy


def build_case(action_a, action_b, entity_type, case_context, extra_agents=None, policy=None):
    """Run the real pipeline and return (weigh_output, agent_actions, case_context, policy)."""

    policy = policy if policy is not None else real_policy()
    conflict_result = evaluate_agent_actions(action_a, action_b, entity_type)
    resolve_output = generate_resolution_candidates(conflict_result, action_a, action_b)

    agent_actions = {action_a["agent"]: action_a, action_b["agent"]: action_b}
    for extra in extra_agents or []:
        agent_actions[extra["agent"]] = extra

    weigh_output = evaluate_candidates(resolve_output, agent_actions, case_context, policy)
    return weigh_output, agent_actions, case_context, policy


# --- the three worked examples from design §S -----------------------------


def payout_vs_dispute_case(policy=None, case_context=None):
    """§S.1 -- defer_to_agent-1 scores exactly 0.7500, the proceed boundary."""

    payouts = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.95,
        "amount": 42000,
        "days_overdue": 9,
    }
    dispute = {
        "agent": "dispute",
        "proposed_action": "HOLD_RELATED_ACTIONS",
        "confidence": 0.95,
        "dispute_status": "OPEN",
        "disputed_amount": 42000,
    }
    context = case_context if case_context is not None else {"case_id": "case-Q", "merchant_id": "mrch_001"}
    return build_case(payouts, dispute, "order_vendor", context, policy=policy)


def rto_vs_retention_case(policy=None):
    """§S.2 -- 0.6300 vs 0.6200: a near tie, and the case Claude exists for."""

    rto = {
        "agent": "rto",
        "proposed_action": "HOLD_ORDER",
        "confidence": 0.95,
        "rto_score": 0.82,
        "shipment_status": "IN_TRANSIT",
    }
    retention = {
        "agent": "retention",
        "proposed_action": "WIN_BACK_OFFER",
        "confidence": 0.95,
        "churn_risk": 0.80,
        "customer_value_score": 0.9,
    }
    return build_case(rto, retention, "customer", {"case_id": "case-R"}, policy=policy)


def no_conflict_release_case(amount, with_rto_verdict=True, policy=None):
    """
    §S.3 -- RELEASE_PAYMENT + CLOSE_CASE, the only money-moving path in the
    system and the only path by which RELEASE_PAYMENT reaches GOVERN at all.
    WEIGH scores it 0.3100 at every amount.
    """

    payouts = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.95,
        "amount": amount,
        "days_overdue": 9,
    }
    dispute = {
        "agent": "dispute",
        "proposed_action": "CLOSE_CASE",
        "confidence": 0.90,
        "dispute_status": "CLOSED",
        "disputed_amount": 0,
    }
    extra = (
        [{"agent": "rto", "proposed_action": "ALLOW_ORDER", "confidence": 0.90}]
        if with_rto_verdict
        else []
    )
    # A distinct release is a distinct case. weigh_output is byte-identical
    # at every amount (the score never moves), so case_id is what separates
    # two releases in the decision_id -- exactly as design §P.2 describes.
    return build_case(
        payouts,
        dispute,
        "order_vendor",
        {"case_id": f"case-P-{amount}"},
        extra_agents=extra,
        policy=policy,
    )


def unresolved_case(policy=None):
    """
    RESOLVE's `unresolved: true` path (hold_both_pending_review-1 as the sole
    candidate). Every conflicting pair in CONFLICT_RULES currently has a
    matching RESOLUTION_RULE, so this path needs a synthetic conflict_result
    to reach -- it is unreachable through the shipped tables.
    """

    policy = policy if policy is not None else real_policy()
    rto = {"agent": "rto", "proposed_action": "HOLD_ORDER", "confidence": 0.95}
    retention = {"agent": "retention", "proposed_action": "RETENTION_MESSAGE", "confidence": 0.95}

    conflict_result = {
        "agent_a": "rto",
        "agent_b": "retention",
        "action_a": "HOLD_ORDER",
        "action_b": "RETENTION_MESSAGE",
        "entity_type": "customer",
        "conflict": True,
        "reason": "synthetic conflict with no matching resolution rule",
    }
    resolve_output = generate_resolution_candidates(conflict_result, rto, retention)
    agent_actions = {"rto": rto, "retention": retention}
    case_context = {"case_id": "case-U"}
    weigh_output = evaluate_candidates(resolve_output, agent_actions, case_context, policy)
    return weigh_output, agent_actions, case_context, policy


# --- advisor fakes ---------------------------------------------------------


def valid_advisory(suggested_candidate_id=None, summary="The two options are close."):
    return {
        "advisory_version": ADVISORY_VERSION,
        "summary": summary,
        "key_tradeoffs": ["Holding the order protects revenue but costs goodwill."],
        "suggested_candidate_id": suggested_candidate_id,
        "confidence_note": "Both agents reported high confidence.",
    }


class ValidAdvisor:
    def __init__(self, response=None):
        self.response = response if response is not None else valid_advisory()
        self.requests = []

    def explain(self, request):
        self.requests.append(copy.deepcopy(request))
        return self.response


class NoneAdvisor:
    """An adapter that is simply unavailable."""

    def __init__(self):
        self.calls = 0

    def explain(self, request):
        self.calls += 1
        return None


class RaisingAdvisor:
    def __init__(self, exc=None):
        self.exc = exc if exc is not None else RuntimeError("connection reset")

    def explain(self, request):
        raise self.exc


class TimingOutAdvisor:
    """The port owns its own deadline; this is how it reports expiry."""

    def explain(self, request):
        raise AdvisorTimeout("advisor deadline expired")


class MalformedAdvisor:
    """Well-shaped keys, invalid values."""

    def __init__(self, response=None):
        self.response = (
            response
            if response is not None
            else {
                "advisory_version": ADVISORY_VERSION,
                "summary": "",
                "key_tradeoffs": [],
                "suggested_candidate_id": None,
                "confidence_note": None,
            }
        )

    def explain(self, request):
        return self.response


class ViolatingAdvisor:
    """An advisor that tries to name the decision."""

    def __init__(self, response=None):
        self.response = (
            response
            if response is not None
            else {
                "advisory_version": ADVISORY_VERSION,
                "summary": "Release the payment.",
                "key_tradeoffs": [],
                "suggested_candidate_id": None,
                "confidence_note": None,
                "outcome": "PROCEED",
                "execution_authorized": True,
            }
        )

    def explain(self, request):
        return self.response
