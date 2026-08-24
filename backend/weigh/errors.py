class WeighInputError(ValueError):
    """Raised when resolve_output, agent_actions, or case_context is structurally invalid."""


class WeighPolicyError(ValueError):
    """Raised when the policy bundle is missing data WEIGH needs, or references
    something WEIGH has no registered way to evaluate (e.g. an action with no
    scoring.action_effects entry, or a hard constraint with no evaluator)."""
