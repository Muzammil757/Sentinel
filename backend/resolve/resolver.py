from resolve.rules import AGENT_PRIORITY_ORDER, find_resolution_rule


def _priority_rank(agent_name: str) -> int:
    try:
        return AGENT_PRIORITY_ORDER.index(agent_name)
    except ValueError:
        return len(AGENT_PRIORITY_ORDER)


def _no_conflict_candidate(action_a_detail: dict, action_b_detail: dict) -> dict:
    return {
        "candidate_id": "no_conflict_proceed-1",
        "strategy": "NO_CONFLICT_PROCEED",
        "preferred_agent": None,
        "resulting_actions": [
            action_a_detail["proposed_action"],
            action_b_detail["proposed_action"],
        ],
        "rationale": "No conflict was detected between the two actions; both may proceed independently.",
        "source_rule": "no_conflict_passthrough",
    }


def _priority_candidate(
    strategy: str,
    agent_a: str,
    agent_b: str,
    action_a_detail: dict,
    action_b_detail: dict,
    rule_id: str,
) -> dict:
    if _priority_rank(agent_a) <= _priority_rank(agent_b):
        preferred_agent = agent_a
        resulting_actions = [action_a_detail["proposed_action"]]
    else:
        preferred_agent = agent_b
        resulting_actions = [action_b_detail["proposed_action"]]

    return {
        "candidate_id": "defer_to_agent-1",
        "strategy": strategy,
        "preferred_agent": preferred_agent,
        "resulting_actions": resulting_actions,
        "rationale": (
            f"Static agent priority order favors '{preferred_agent}' for this "
            f"conflict type; its action is proposed to take precedence."
        ),
        "source_rule": rule_id,
    }


def _hold_both_pending_review_candidate(candidate_id: str, rule_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "strategy": "HOLD_BOTH_PENDING_REVIEW",
        "preferred_agent": None,
        "resulting_actions": [],
        "rationale": (
            "Conservative fallback: hold both actions pending human/governance "
            "review rather than automatically preferring either agent."
        ),
        "source_rule": rule_id,
    }


def generate_resolution_candidates(
    conflict_result: dict,
    action_a_detail: dict,
    action_b_detail: dict,
) -> dict:
    """
    Deterministic RESOLVE layer.

    Consumes the structured output of conflict_matrix.integration.evaluate_agent_actions
    plus the two original agent action payloads, and produces a list of candidate
    ways to resolve the conflict. Does not select a winner and does not execute
    any action -- that is the responsibility of the downstream WEIGH/GOVERN layers.
    """

    entity_type = conflict_result["entity_type"]
    agent_a = conflict_result["agent_a"]
    agent_b = conflict_result["agent_b"]
    conflict = conflict_result["conflict"]

    if not conflict:
        return {
            "entity_type": entity_type,
            "agent_a": agent_a,
            "agent_b": agent_b,
            "conflict": False,
            "unresolved": False,
            "candidates": [_no_conflict_candidate(action_a_detail, action_b_detail)],
        }

    rule = find_resolution_rule(
        conflict_result["action_a"],
        conflict_result["action_b"],
        entity_type,
    )

    if rule is None:
        return {
            "entity_type": entity_type,
            "agent_a": agent_a,
            "agent_b": agent_b,
            "conflict": True,
            "unresolved": True,
            "candidates": [
                _hold_both_pending_review_candidate(
                    "hold_both_pending_review-1", "no_matching_resolution_rule"
                )
            ],
        }

    candidates = [
        _priority_candidate(
            rule.strategy, agent_a, agent_b, action_a_detail, action_b_detail, rule.rule_id
        ),
        _hold_both_pending_review_candidate("hold_both_pending_review-2", rule.rule_id),
    ]

    return {
        "entity_type": entity_type,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "conflict": True,
        "unresolved": False,
        "candidates": candidates,
    }
