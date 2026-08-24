from dataclasses import dataclass


# Static, deterministic priority order between agent domains.
# Lower index = higher priority when a conflict carries no other signal.
# Dispute/RTO (financial-loss and fraud risk) outrank the operational
# Payouts agent, which outranks the discretionary Retention agent.
AGENT_PRIORITY_ORDER = [
    "dispute",
    "rto",
    "payouts",
    "retention",
]


@dataclass(frozen=True)
class ResolutionRule:
    action_a: str
    action_b: str
    entity_type: str
    strategy: str
    rule_id: str


# Mirrors conflict_matrix.matrix.CONFLICT_RULES in shape and intent:
# a static table of known conflict pairs mapped to the deterministic
# resolution strategy RESOLVE should propose as a candidate.
RESOLUTION_RULES = [
    ResolutionRule(
        action_a="RELEASE_PAYMENT",
        action_b="HOLD_RELATED_ACTIONS",
        entity_type="order_vendor",
        strategy="DEFER_TO_AGENT",
        rule_id="release_payment_vs_hold_related_actions",
    ),
    ResolutionRule(
        action_a="HOLD_ORDER",
        action_b="PRESERVE_EXPERIENCE",
        entity_type="customer",
        strategy="DEFER_TO_AGENT",
        rule_id="hold_order_vs_preserve_experience",
    ),
    ResolutionRule(
        action_a="HOLD_ORDER",
        action_b="WIN_BACK_OFFER",
        entity_type="customer",
        strategy="DEFER_TO_AGENT",
        rule_id="hold_order_vs_win_back_offer",
    ),
]


def _normalize_pair(action_a: str, action_b: str) -> tuple[str, str]:
    return tuple(sorted((action_a.upper(), action_b.upper())))


def find_resolution_rule(action_a: str, action_b: str, entity_type: str):
    normalized_pair = _normalize_pair(action_a, action_b)

    for rule in RESOLUTION_RULES:
        rule_pair = _normalize_pair(rule.action_a, rule.action_b)

        if rule_pair == normalized_pair and rule.entity_type == entity_type:
            return rule

    return None
