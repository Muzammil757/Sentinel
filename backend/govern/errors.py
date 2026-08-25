class GovernInputError(ValueError):
    """Raised when weigh_output, agent_actions, case_context, or the policy
    identity binding them together is structurally invalid -- i.e. the
    integration between layers is broken."""


class GovernPolicyError(ValueError):
    """Raised when the policy bundle is missing governance data GOVERN needs,
    or configures it in a way GOVERN must refuse to act on (e.g. no
    escalation.thresholds.mid_band_outcome, a fallback token GOVERN cannot
    map onto an outcome, or a claude.may_* invariant that is not false).

    Design §Q: policy gaps raise, evidence gaps are reported."""
