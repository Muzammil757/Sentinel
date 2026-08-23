from matrix import check_conflict

def evaluate_agent_actions(
    action_a: dict,
    action_b: dict,
    entity_type: str,
) -> dict:
    """
    Compare two independent agent recommendations
    using the deterministic Conflict Matrix.
    """

    result = check_conflict(
        action_a=action_a["proposed_action"],
        action_b=action_b["proposed_action"],
        entity_type=entity_type,
    )

    return {
        "agent_a": action_a["agent"],
        "agent_b": action_b["agent"],
        "action_a": result["action_a"],
        "action_b": result["action_b"],
        "entity_type": entity_type,
        "conflict": result["conflict"],
        "reason": result["reason"],
    }