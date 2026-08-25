"""
The mock action registry: the closed set of actions EXECUTOR knows how to
perform, and the deterministic simulated effect of each.

This is a CAPABILITY registry, not a policy. It answers exactly one question
-- "do I know how to perform this action?" -- and never "is this action
allowed?". Permission was settled by GOVERN before anything here runs, and an
action being present in this table grants it nothing.

The vocabulary is the project's existing one: the actions the mock agents
propose (mock_agents/) and that the policy bundle prices in
scoring.action_effects. No action name is invented here.

Every effect is simulated in-process: no money moves, no external system is
called, nothing is written anywhere. `perform` is a pure lookup -- the same
action always yields the same effect record.
"""

import copy

SUPPORTED_ACTIONS = {
    "RELEASE_PAYMENT": {
        "effect": "PAYOUT_RELEASE_SIMULATED",
        "target": "vendor_payout",
        "detail": "Mock: the vendor payout was marked released. No funds moved.",
    },
    "HOLD_RELATED_ACTIONS": {
        "effect": "RELATED_ACTIONS_HELD",
        "target": "dispute_case",
        "detail": "Mock: actions related to the disputed case were placed on hold.",
    },
    "CLOSE_CASE": {
        "effect": "CASE_CLOSED",
        "target": "dispute_case",
        "detail": "Mock: the dispute case was marked closed.",
    },
    "HOLD_ORDER": {
        "effect": "ORDER_HELD",
        "target": "order",
        "detail": "Mock: the order was placed on hold pending review.",
    },
    "REVIEW_ORDER": {
        "effect": "ORDER_FLAGGED_FOR_REVIEW",
        "target": "order",
        "detail": "Mock: the order was flagged into the manual review queue.",
    },
    "ALLOW_ORDER": {
        "effect": "ORDER_ALLOWED",
        "target": "order",
        "detail": "Mock: the order was allowed to continue.",
    },
    "WIN_BACK_OFFER": {
        "effect": "WIN_BACK_OFFER_SENT",
        "target": "customer",
        "detail": "Mock: a win-back offer was queued for the customer.",
    },
    "RETENTION_MESSAGE": {
        "effect": "RETENTION_MESSAGE_SENT",
        "target": "customer",
        "detail": "Mock: a retention message was queued for the customer.",
    },
    "NO_RETENTION_ACTION": {
        "effect": "NO_OP",
        "target": "customer",
        "detail": "Mock: no retention action was taken, by design.",
    },
}


def is_supported(action) -> bool:
    return isinstance(action, str) and action in SUPPORTED_ACTIONS


def unsupported(actions) -> list:
    """The sorted, de-duplicated actions EXECUTOR has no way to perform."""

    return sorted({str(action) for action in actions if not is_supported(action)})


def perform(action: str) -> dict:
    """
    Simulate one authorized action and return its effect record.

    Callers reach this only after the authorization ladder has already
    confirmed the action is both authorized by GOVERN and supported here; an
    unknown action raises rather than being quietly skipped, so a bug in the
    caller can never turn into a silent non-execution.
    """

    entry = SUPPORTED_ACTIONS[action]
    return {
        "action": action,
        "effect": entry["effect"],
        "target": entry["target"],
        "detail": entry["detail"],
    }


def perform_all(actions) -> list:
    """Simulate the authorized actions in the order GOVERN authorized them."""

    return [perform(action) for action in actions]


def registry_snapshot() -> dict:
    """A defensive copy, so a caller inspecting the registry cannot edit it."""

    return copy.deepcopy(SUPPORTED_ACTIONS)
