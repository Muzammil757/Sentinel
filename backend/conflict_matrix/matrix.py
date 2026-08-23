from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ConflictRule:
    action_a: str
    action_b: str
    entity_type: str
    conflict: bool
    reason: str


CONFLICT_RULES = [
    ConflictRule(
        action_a="RELEASE_PAYMENT",
        action_b="HOLD_RELATED_ACTIONS",
        entity_type="order_vendor",
        conflict=True,
        reason="Payment release overlaps with a dispute-related hold.",
    ),
    ConflictRule(
        action_a="HOLD_ORDER",
        action_b="PRESERVE_EXPERIENCE",
        entity_type="customer",
        conflict=True,
        reason="Order hold conflicts with retention's experience-preservation action.",
    ),
    ConflictRule(
        action_a="RELEASE_PAYMENT",
        action_b="CLOSE_CASE",
        entity_type="order_vendor",
        conflict=False,
        reason="Closed dispute case creates no active payment conflict.",
    ),
    ConflictRule(
        action_a="HOLD_ORDER",
        action_b="WIN_BACK_OFFER",
        entity_type="customer",
        conflict=True,
        reason="Order hold may conflict with a retention win-back action.",
    ),
]


def _normalize_pair(action_a: str, action_b: str) -> tuple[str, str]:
    return tuple(sorted((action_a.upper(), action_b.upper())))


def check_conflict(
    action_a: str,
    action_b: str,
    entity_type: str,
) -> dict:
    normalized_pair = _normalize_pair(action_a, action_b)

    for rule in CONFLICT_RULES:
        rule_pair = _normalize_pair(rule.action_a, rule.action_b)

        if (
            rule_pair == normalized_pair
            and rule.entity_type == entity_type
        ):
            return {
                "conflict": rule.conflict,
                "action_a": action_a.upper(),
                "action_b": action_b.upper(),
                "entity_type": entity_type,
                "reason": rule.reason,
            }

    return {
        "conflict": False,
        "action_a": action_a.upper(),
        "action_b": action_b.upper(),
        "entity_type": entity_type,
        "reason": "No known conflict rule matched.",
    }