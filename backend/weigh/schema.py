WEIGH_VERSION = "1.0.0"
SCORING_METHOD = "weighted_linear_v1"
CONFIDENCE_METHOD = "min_blend_v1"

# Design doc §E.6 -- WEIGH must never name a governance winner. Checked
# recursively over the full output in test_weigh.py.
FORBIDDEN_OUTPUT_KEYS = {
    "final_action",
    "decision",
    "selected_candidate",
    "selected",
    "winner",
    "chosen_candidate",
    "recommended_action",
    "recommendation",
    "action_to_execute",
    "execute",
    "outcome",
    "verdict",
    "approved",
    "resolution",
}

REQUIRED_RESOLVE_KEYS = {
    "entity_type",
    "agent_a",
    "agent_b",
    "conflict",
    "unresolved",
    "candidates",
}

REQUIRED_CANDIDATE_KEYS = {
    "candidate_id",
    "strategy",
    "preferred_agent",
    "resulting_actions",
    "rationale",
    "source_rule",
}

REQUIRED_POLICY_SECTIONS = (
    "policy",
    "objectives",
    "weights",
    "scoring",
    "profile_selection",
    "hard_constraints",
    "authority",
    "ambiguity",
)
