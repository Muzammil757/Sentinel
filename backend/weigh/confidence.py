def _is_valid_confidence(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def compute_case_confidence(contributing_agents: list, agent_actions: dict, alpha: float) -> tuple[float, dict, list]:
    """
    Design §H.2 (min_blend_v1): case_confidence = alpha*C_min + (1-alpha)*C_mean.

    The brief's "weighted mean floored by the minimum" is degenerate --
    max(mean, min) always equals mean (the mean is never below the min) and
    min(mean, min) always equals min. This blend keeps both terms live: it
    is monotone non-decreasing in every input, and strictly between C_min
    and C_mean whenever the inputs differ.

    Missing/invalid confidence is treated as 0.0 (conservative -- see
    design §H.5) and reported in the returned missing-agents list.
    """

    confidences = []
    missing_agents = []
    for agent in contributing_agents:
        payload = agent_actions.get(agent, {})
        value = payload.get("confidence")
        if _is_valid_confidence(value):
            confidences.append(float(value))
        else:
            confidences.append(0.0)
            missing_agents.append(agent)

    c_min = min(confidences)
    c_mean = sum(confidences) / len(confidences)
    case_confidence = round(alpha * c_min + (1 - alpha) * c_mean, 4)

    confidence_inputs = {
        "min": round(c_min, 4),
        "mean": round(c_mean, 4),
        "min_weight": alpha,
    }
    return case_confidence, confidence_inputs, sorted(missing_agents)


def resolve_originating_confidence(preferred_agent, agent_actions: dict, case_confidence: float) -> float:
    """
    Design §H.3: originating_confidence is the preferred agent's own
    confidence; candidates with no preferred agent (e.g. NO_CONFLICT_PROCEED)
    fall back to case_confidence.
    """

    if preferred_agent is None:
        return case_confidence

    payload = agent_actions.get(preferred_agent, {})
    value = payload.get("confidence")
    if _is_valid_confidence(value):
        return float(value)
    return 0.0
