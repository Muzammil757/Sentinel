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
from dataclasses import dataclass
from typing import Any, Callable

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
    ]
}


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> Scenario | None:
    return SCENARIOS.get(scenario_id)
