"""
Scenario Lab: a curated, deterministic set of cases run through the REAL
pipeline (backend.api.orchestrator.run_pipeline), never a mocked API
response. Every scenario's agent evidence mirrors a real fixture already
exercised by the existing test suite (govern/conftest.py's worked examples,
design section S / N) -- this module does not invent a business outcome; it
re-runs the same evidence through the same code path a request to
POST /api/cases/{id}/run would use, and the outcome that comes back is
whatever GOVERN and EXECUTOR actually decide.

Each entry is a zero-argument builder returning the keyword arguments
orchestrator.run_pipeline() accepts, plus a human-readable description of
what the scenario is expected to demonstrate (not what it is hard-coded to
produce -- nothing here asserts an outcome; the pipeline decides it fresh
every run).
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from policy.loader import load_policy


def _variant_policy(**threshold_overrides) -> dict:
    """
    A deepcopy of the real policy with escalation.thresholds overridden --
    the same pattern govern/conftest.py::variant_policy and
    govern/test_govern.py::test_policy_change_changes_outcome_without_code_change
    use to prove GOVERN reads its thresholds from policy, not from a
    hard-coded constant. Reimplemented here (rather than importing
    govern.conftest, which is test infrastructure) so this production module
    depends only on other production code.
    """

    policy = copy.deepcopy(load_policy())
    policy["escalation"]["thresholds"].update(threshold_overrides)
    return policy


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    build: Callable[[], dict[str, Any]]


def _normal_payout_proceed() -> dict:
    return {
        "external_case_id": "scenario-normal-payout",
        "entity_type": "order_vendor",
        "agent_a": {
            "agent": "payouts",
            "proposed_action": "RELEASE_PAYMENT",
            "confidence": 0.95,
            "amount": 42000,
            "days_overdue": 9,
        },
        "agent_b": {
            "agent": "dispute",
            "proposed_action": "HOLD_RELATED_ACTIONS",
            "confidence": 0.95,
            "dispute_status": "OPEN",
            "disputed_amount": 42000,
        },
        "case_context": {"case_id": "scenario-normal-payout", "merchant_id": "mrch_001"},
    }


def _agent_disagreement_hold() -> dict:
    # Same evidence as the PROCEED scenario, scored 0.7500 (the design's own
    # documented boundary) -- a tightened proceed_min_score of 0.76 moves the
    # exact same disagreement from PROCEED to HOLD, without touching a line
    # of pipeline code (mirrors govern/test_govern.py::
    # test_policy_change_changes_outcome_without_code_change).
    return {
        "external_case_id": "scenario-agent-disagreement",
        "entity_type": "order_vendor",
        "agent_a": {
            "agent": "payouts",
            "proposed_action": "RELEASE_PAYMENT",
            "confidence": 0.95,
            "amount": 42000,
            "days_overdue": 9,
        },
        "agent_b": {
            "agent": "dispute",
            "proposed_action": "HOLD_RELATED_ACTIONS",
            "confidence": 0.95,
            "dispute_status": "OPEN",
            "disputed_amount": 42000,
        },
        "case_context": {"case_id": "scenario-agent-disagreement", "merchant_id": "mrch_001"},
        "policy": _variant_policy(proceed_min_score=0.76),
    }


def _authority_cap_escalation() -> dict:
    # design section S.3's over-the-cap variant: the only money-moving path
    # in the system, one currency unit over the authority cap.
    return {
        "external_case_id": "scenario-authority-cap-escalation",
        "entity_type": "order_vendor",
        "agent_a": {
            "agent": "payouts",
            "proposed_action": "RELEASE_PAYMENT",
            "confidence": 0.95,
            "amount": 60000,
            "days_overdue": 9,
        },
        "agent_b": {
            "agent": "dispute",
            "proposed_action": "CLOSE_CASE",
            "confidence": 0.90,
            "dispute_status": "CLOSED",
            "disputed_amount": 0,
        },
        "extra_agents": [{"agent": "rto", "proposed_action": "ALLOW_ORDER", "confidence": 0.90}],
        "case_context": {"case_id": "scenario-authority-cap-escalation"},
    }


def _ambiguous_case() -> dict:
    # design section S.2: a near tie between two permitted candidates.
    return {
        "external_case_id": "scenario-ambiguous",
        "entity_type": "customer",
        "agent_a": {
            "agent": "rto",
            "proposed_action": "HOLD_ORDER",
            "confidence": 0.95,
            "rto_score": 0.82,
            "shipment_status": "IN_TRANSIT",
        },
        "agent_b": {
            "agent": "retention",
            "proposed_action": "WIN_BACK_OFFER",
            "confidence": 0.95,
            "churn_risk": 0.80,
            "customer_value_score": 0.9,
        },
        "case_context": {"case_id": "scenario-ambiguous"},
    }


def _executor_rejection() -> dict:
    # A normal PROCEED case, but the caller's execution_request names a
    # candidate GOVERN did not authorize. EXECUTOR's own authorization
    # ladder (executor/authorization.py check 8, REQUEST_MATCHES_AUTHORIZATION)
    # refuses it -- demonstrating that EXECUTOR rejects on request mismatch
    # even when GOVERN authorized something.
    scenario = _normal_payout_proceed()
    scenario["external_case_id"] = "scenario-executor-rejection"
    scenario["case_context"] = {"case_id": "scenario-executor-rejection", "merchant_id": "mrch_001"}
    scenario["execution_request"] = {"candidate_id": "a-candidate-govern-never-authorized"}
    return scenario


def _pipeline_failure() -> dict:
    # A deliberately malformed agent payload (no proposed_action) -- the API's
    # own request validation (backend.api.schemas.RunRequest) would normally
    # reject this at the HTTP boundary before it ever reaches the pipeline;
    # this scenario bypasses that validation on purpose to demonstrate the
    # orchestrator's real, non-silent failure path (RUN_FAILED audit event,
    # case_run.status == "FAILED") when a pipeline stage genuinely raises.
    return {
        "external_case_id": "scenario-pipeline-failure",
        "entity_type": "order_vendor",
        "agent_a": {"agent": "payouts", "confidence": 0.95, "amount": 42000},
        "agent_b": {
            "agent": "dispute",
            "proposed_action": "HOLD_RELATED_ACTIONS",
            "confidence": 0.95,
            "dispute_status": "OPEN",
            "disputed_amount": 42000,
        },
        "case_context": {"case_id": "scenario-pipeline-failure"},
    }


_GEMINI_MODEL = "gemini-2.5-flash"
_GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"
_GEMINI_TIMEOUT_SECONDS = 15.0


def _is_valid_confidence(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def _call_gemini_agent(
    *,
    agent: str,
    allowed_actions: list[str],
    prompt: str,
    domain_fields: dict,
    fallback_action: str,
    fallback_confidence: float,
    fallback_reasoning: str,
) -> dict:
    """
    One live agent's decision, backed by a real call to the Gemini API.

    This never invents a decision itself -- the result is either Gemini's
    own response (validated: proposed_action must be one of
    `allowed_actions`, confidence a real number in [0, 1]) or `fallback_*`,
    a real response captured once from an actual successful call, used only
    if the live call fails, times out, or returns something that fails that
    validation. GEMINI_API_KEY is read from the environment and sent only as
    a request header -- never logged, printed, or placed in a URL -- and any
    exception from the call is caught here and never re-raised, so a raw
    httpx error (which could otherwise carry request details) never
    propagates past this function.
    """

    def _build_result(action: str, confidence: float, reasoning: str) -> dict:
        return {
            "agent": agent,
            **domain_fields,
            "proposed_action": action,
            "confidence": float(confidence),
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def fallback() -> dict:
        return _build_result(fallback_action, fallback_confidence, fallback_reasoning)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return fallback()

    schema = {
        "type": "OBJECT",
        "properties": {
            "proposed_action": {"type": "STRING", "enum": allowed_actions},
            "confidence": {"type": "NUMBER"},
            "reasoning": {"type": "STRING"},
        },
        "required": ["proposed_action", "confidence", "reasoning"],
        "propertyOrdering": ["proposed_action", "confidence", "reasoning"],
    }

    try:
        response = httpx.post(
            _GEMINI_ENDPOINT,
            headers={"x-goog-api-key": api_key, "content-type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
            },
            timeout=_GEMINI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        parsed = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])

        action = parsed["proposed_action"]
        confidence = parsed["confidence"]
        reasoning = parsed["reasoning"]

        if (
            action not in allowed_actions
            or not _is_valid_confidence(confidence)
            or not isinstance(reasoning, str)
            or not reasoning.strip()
        ):
            raise ValueError("Gemini response failed local validation")

        return _build_result(action, confidence, reasoning)
    except Exception:
        return fallback()


_RISK_ALLOWED_ACTIONS = ["HOLD_ORDER", "ALLOW_ORDER"]
_RETENTION_ALLOWED_ACTIONS = ["PRESERVE_EXPERIENCE", "ESCALATE_TO_RISK"]


def _live_ai_customer_risk() -> dict:
    # A live case: an order carries real fraud signals (new, unverified
    # shipping address; large IP-geolocation delta) for a customer who is
    # also a high-value, no-history loyalty account. Each agent sees only
    # its own domain's facts, exactly like the mock agents' own isolation
    # ("this agent does not access other agents' data") -- Logistics/Risk
    # never sees lifetime spend or loyalty tier; Retention never sees the
    # shipment/IP signals. If both agents hold their domain's position, this
    # is real HOLD_ORDER vs PRESERVE_EXPERIENCE disagreement under
    # entity_type "customer" -- conflict_matrix rule
    # hold_order_vs_preserve_experience, a real conflict pair no other
    # scenario currently exercises.
    risk_prompt = (
        "You are Sentinel's Logistics/Risk agent. You evaluate shipment and "
        "fraud-risk signals for one order. You do not know anything about this "
        "customer's lifetime value, tenure, or retention economics -- that is a "
        "different agent's job. You must choose exactly one proposed_action from "
        "HOLD_ORDER or ALLOW_ORDER.\n\n"
        "Case facts:\n"
        "- order_id: ord_88213\n"
        "- customer_id: cust_5541\n"
        "- order_value: 2150.00 USD\n"
        "- shipment_method: next-day\n"
        "- shipping_address_status: NEW_ADDRESS_NOT_ON_FILE\n"
        "- billing_shipping_match: false\n"
        "- login_ip_geolocation_delta_miles: 340\n"
        "- account_age_days: 1825\n\n"
        "Decide HOLD_ORDER (block shipment pending verification) or ALLOW_ORDER "
        "(let it ship). Give a real confidence between 0 and 1, and a short "
        "genuine reasoning sentence."
    )
    retention_prompt = (
        "You are Sentinel's Retention agent. You evaluate customer lifetime "
        "value and churn risk for one customer. You do not know anything about "
        "shipment fraud signals, IP geolocation, or address-verification status "
        "-- that is a different agent's job. You must choose exactly one "
        "proposed_action from PRESERVE_EXPERIENCE or ESCALATE_TO_RISK.\n\n"
        "Case facts:\n"
        "- customer_id: cust_5541\n"
        "- order_id: ord_88213\n"
        "- account_age_days: 1825\n"
        "- lifetime_spend_usd: 18400.00\n"
        "- past_disputes: 0\n"
        "- loyalty_tier: gold\n"
        "- historical_churn_after_hold_rate: 0.34\n\n"
        "Decide PRESERVE_EXPERIENCE (advocate for not disrupting this customer's "
        "order) or ESCALATE_TO_RISK (defer to risk/logistics judgment on this "
        "order). Give a real confidence between 0 and 1, and a short genuine "
        "reasoning sentence."
    )

    agent_a = _call_gemini_agent(
        agent="rto",
        allowed_actions=_RISK_ALLOWED_ACTIONS,
        prompt=risk_prompt,
        domain_fields={
            "order_id": "ord_88213",
            "customer_id": "cust_5541",
            "shipping_address_status": "NEW_ADDRESS_NOT_ON_FILE",
            "login_ip_geolocation_delta_miles": 340,
        },
        # Captured verbatim from a real successful gemini-2.5-flash call
        # against this exact prompt.
        fallback_action="HOLD_ORDER",
        fallback_confidence=0.9,
        fallback_reasoning=(
            "The high-value, next-day order to a new address with a billing and "
            "shipping mismatch presents a very high fraud risk."
        ),
    )
    agent_b = _call_gemini_agent(
        agent="retention",
        allowed_actions=_RETENTION_ALLOWED_ACTIONS,
        prompt=retention_prompt,
        domain_fields={
            "customer_id": "cust_5541",
            "order_id": "ord_88213",
            "lifetime_spend_usd": 18400.00,
            "historical_churn_after_hold_rate": 0.34,
        },
        # Captured verbatim from a real successful gemini-2.5-flash call
        # against this exact prompt.
        fallback_action="PRESERVE_EXPERIENCE",
        fallback_confidence=0.95,
        fallback_reasoning=(
            "This is a high-value, long-standing Gold tier customer with no past "
            "disputes, and historical data shows a high churn rate after order "
            "holds."
        ),
    )

    return {
        "external_case_id": "scenario-live-ai-agent",
        "entity_type": "customer",
        "agent_a": agent_a,
        "agent_b": agent_b,
        "case_context": {"case_id": "scenario-live-ai-agent"},
    }


SCENARIOS: dict[str, Scenario] = {
    scenario.id: scenario
    for scenario in [
        Scenario(
            id="normal_payout_proceed",
            title="Normal payout release",
            description="Payouts and Dispute disagree; RESOLVE defers to Dispute's hold, WEIGH scores it at the PROCEED boundary, GOVERN authorizes, EXECUTOR executes.",
            build=_normal_payout_proceed,
        ),
        Scenario(
            id="agent_disagreement_hold",
            title="Agent disagreement, held for review",
            description="Identical evidence to the normal payout scenario, but under a tightened proceed_min_score the same score now falls to HOLD -- permitted, but not executed.",
            build=_agent_disagreement_hold,
        ),
        Scenario(
            id="authority_cap_escalation",
            title="Authority-cap escalation",
            description="A payout one unit over the policy's authority cap; GOVERN escalates rather than authorizing, so EXECUTOR has nothing to execute and rejects.",
            build=_authority_cap_escalation,
        ),
        Scenario(
            id="ambiguous_case",
            title="Ambiguous case",
            description="RTO and Retention produce a near-tie between two permitted candidates; GOVERN routes it to a human reviewer instead of choosing.",
            build=_ambiguous_case,
        ),
        Scenario(
            id="executor_rejection",
            title="Executor rejection on request mismatch",
            description="GOVERN authorizes a candidate, but the execution request names a different one; EXECUTOR's authorization ladder refuses it on the record.",
            build=_executor_rejection,
        ),
        Scenario(
            id="pipeline_failure",
            title="Pipeline failure",
            description="A malformed agent payload reaches the real pipeline; the run fails at CONFLICT_OR_RESOLVE, is recorded as RUN_FAILED, and is never reported as a success.",
            build=_pipeline_failure,
        ),
        Scenario(
            id="live_ai_customer_risk",
            title="Live AI: order risk vs. customer retention",
            description="Two live Gemini-backed agents reason independently over the same case from their own domain -- Logistics/Risk (HOLD_ORDER/ALLOW_ORDER) and Retention (PRESERVE_EXPERIENCE/ESCALATE_TO_RISK) -- and the real pipeline decides what their disagreement means. Falls back to a captured real response if the live call fails, times out, or returns an invalid action.",
            build=_live_ai_customer_risk,
        ),
    ]
}


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> Scenario | None:
    return SCENARIOS.get(scenario_id)
