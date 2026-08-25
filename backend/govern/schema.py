"""
GOVERN constants: versions, the closed outcome vocabulary, the machine-readable
code sets, and the required-key sets used to validate the layer above.

Constants only -- no logic, mirroring weigh/schema.py.
"""

GOVERN_VERSION = "1.0.0"
DECISION_METHOD = "policy_gated_v1"

# --- outcomes -------------------------------------------------------------

OUTCOME_PROCEED = "PROCEED"
OUTCOME_HOLD = "HOLD"
OUTCOME_ESCALATE = "ESCALATE"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"

# GOVERN reads the legal set from policy.escalation.outcomes, but refuses to
# run against a policy that does not define all four -- every branch of the
# decision table needs a name to assign.
REQUIRED_OUTCOMES = frozenset(
    {OUTCOME_PROCEED, OUTCOME_HOLD, OUTCOME_ESCALATE, OUTCOME_AMBIGUOUS}
)

# Design §R.1: an undefined score band may never auto-execute, so PROCEED is
# not a legal mid_band_outcome. AMBIGUOUS is excluded too -- ambiguity is
# derived from ambiguity signals, and letting a score band also name it would
# give one outcome two unrelated sources.
MID_BAND_OUTCOMES = frozenset({OUTCOME_HOLD, OUTCOME_ESCALATE})

BAND_PROCEED = "PROCEED_BAND"
BAND_MID = "MID_BAND"
BAND_HOLD = "HOLD_BAND"

# --- outcome_basis codes (design §F.1) ------------------------------------

BASIS_NO_PERMITTED_CANDIDATE = "NO_PERMITTED_CANDIDATE"
BASIS_GOVERN_WEIGH_DISAGREEMENT = "GOVERN_WEIGH_DISAGREEMENT"
BASIS_ACTION_REQUIRES_ESCALATION = "ACTION_REQUIRES_ESCALATION"
BASIS_AMBIGUITY_DETECTED = "AMBIGUITY_DETECTED"
BASIS_NO_CONFLICT_ALL_CHECKS_PASSED = "NO_CONFLICT_ALL_CHECKS_PASSED"
BASIS_SCORE_AT_OR_ABOVE_PROCEED_MIN = "SCORE_AT_OR_ABOVE_PROCEED_MIN"
BASIS_SCORE_AT_OR_BELOW_HOLD_MAX = "SCORE_AT_OR_BELOW_HOLD_MAX"
BASIS_SCORE_IN_MID_BAND = "SCORE_IN_MID_BAND"
BASIS_CLAUDE_SCHEMA_VIOLATION = "CLAUDE_SCHEMA_VIOLATION"

# Why the score band was not read: one stable code per decision-table row
# that settled the outcome before the band could matter.
BAND_SKIP_NO_PERMITTED_CANDIDATE = "no_permitted_candidate"
BAND_SKIP_GOVERN_WEIGH_DISAGREEMENT = "govern_weigh_disagreement"
BAND_SKIP_ACTION_REQUIRES_ESCALATION = "action_requires_escalation"
BAND_SKIP_AMBIGUITY_DETECTED = "ambiguity_detected"
BAND_SKIP_NO_CONFLICT = "no_conflict_single_candidate"

SCORE_SOURCE = "weigh.total_score"
ORDERING_SOURCE = "weigh.total_score"

# --- constraint statuses ---------------------------------------------------

STATUS_VIOLATED = "VIOLATED"
STATUS_INDETERMINATE = "INDETERMINATE"
STATUS_SATISFIED = "SATISFIED"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

# Inherited unchanged from WEIGH §I.3: an unverifiable constraint is never
# treated as satisfied, so INDETERMINATE blocks exactly like VIOLATED.
BLOCKING_CONSTRAINT_STATUSES = frozenset({STATUS_VIOLATED, STATUS_INDETERMINATE})

# --- authority results (design §E.3) --------------------------------------

AUTHORITY_AUTHORIZED = "AUTHORIZED"
AUTHORITY_NOT_AUTHORIZED = "NOT_AUTHORIZED"
AUTHORITY_INDETERMINATE = "INDETERMINATE"

# weigh.constraints._eval_unauthorized_action speaks constraint vocabulary;
# the receipt reads better in authority vocabulary. Same facts, renamed.
AUTHORITY_RESULT_FROM_CONSTRAINT_STATUS = {
    STATUS_SATISFIED: AUTHORITY_AUTHORIZED,
    STATUS_VIOLATED: AUTHORITY_NOT_AUTHORIZED,
    STATUS_INDETERMINATE: AUTHORITY_INDETERMINATE,
}

UNAUTHORIZED_ACTION_CONSTRAINT_ID = "HC_UNAUTHORIZED_ACTION"

# --- ambiguity (design §J.1) ----------------------------------------------

# Signals about the COMPARISON. They only apply while there is still a
# comparison to make -- i.e. at least two permitted candidates.
COMPARATIVE_AMBIGUITY_CODES = frozenset({"NEAR_TIE", "CONFLICTING_OBJECTIVES"})

# Signals about the CASE (weak or incomplete evidence). They apply however
# many candidates survive GOVERN's gates.
NON_COMPARATIVE_AMBIGUITY_CODES = frozenset({"LOW_CONFIDENCE", "INSUFFICIENT_EVIDENCE"})

MIN_PERMITTED_FOR_COMPARATIVE_AMBIGUITY = 2

# --- Claude ----------------------------------------------------------------

ADVISORY_VERSION = "1.0.0"
ADVISORY_REQUEST_VERSION = "1.0.0"
ADVISORY_QUESTION = "explain_ambiguity"

CLAUDE_ERROR_UNAVAILABLE = "UNAVAILABLE"
CLAUDE_ERROR_TIMEOUT = "TIMEOUT"
CLAUDE_ERROR_INVALID_RESPONSE = "INVALID_RESPONSE"
CLAUDE_ERROR_SCHEMA_VIOLATION = "SCHEMA_VIOLATION"

# Which policy.fallback.* key answers each advisor failure.
CLAUDE_ERROR_FALLBACK_KEYS = {
    CLAUDE_ERROR_UNAVAILABLE: "on_claude_unavailable",
    CLAUDE_ERROR_TIMEOUT: "on_timeout",
    CLAUDE_ERROR_INVALID_RESPONSE: "on_invalid_response",
    CLAUDE_ERROR_SCHEMA_VIOLATION: "on_schema_violation",
}

# Design §N.1 -- the vocabulary bridge. policy.fallback.* speaks
# HOLD_FOR_REVIEW; policy.escalation.outcomes does not contain that token.
# A fallback value is never assigned to `outcome` directly; it is mapped
# here first. Correct against the policy as it stands and against the
# corrected vocabulary proposed in design §R.2, so GOVERN is right either way.
FALLBACK_OUTCOME_ALIASES = {
    "HOLD_FOR_REVIEW": OUTCOME_HOLD,
    "HOLD": OUTCOME_HOLD,
    "ESCALATE": OUTCOME_ESCALATE,
}

# Re-asserted at the advisor call site, where it matters, even though
# policy.loader already enforces them at load time.
CLAUDE_FORBIDDEN_CAPABILITY_FLAGS = (
    "may_invent_candidates",
    "may_bypass_hard_constraints",
    "may_override_authority",
    "may_directly_execute_actions",
)

GATE_OUTCOME_NOT_AMBIGUOUS = "OUTCOME_NOT_AMBIGUOUS"
GATE_BLOCKING_CONSTRAINT_PRESENT = "BLOCKING_CONSTRAINT_PRESENT"
GATE_EXECUTION_AUTHORIZED = "EXECUTION_AUTHORIZED"
GATE_NO_ADVISOR_INJECTED = "NO_ADVISOR_INJECTED"

# The advisory response contract (design §M.2). Exactly these five keys --
# any missing or extra key is a SCHEMA_VIOLATION.
ADVISORY_REQUIRED_KEYS = frozenset(
    {
        "advisory_version",
        "summary",
        "key_tradeoffs",
        "suggested_candidate_id",
        "confidence_note",
    }
)

ADVISORY_SUMMARY_MAX = 500
ADVISORY_TEXT_MAX = 200
ADVISORY_MAX_TRADEOFFS = 5

# Design §M.3 rule 5: any of these as a key at any depth of the advisory is a
# schema violation -- the model attempting to name a decision, an action, or
# a policy object rather than explain one.
ADVISORY_FORBIDDEN_KEYS = frozenset(
    {
        "outcome",
        "decision",
        "execution_authorized",
        "authorized",
        "approve",
        "approved",
        "override",
        "bypass",
        "escalate",
        "execute",
        "action",
        "actions",
        "new_candidate",
        "candidate",
        "policy",
        "authority",
        "constraint",
    }
)

# Design §L.3: the advisor request is BUILT from these whitelists, never
# filtered out of an upstream payload -- so adding a field anywhere upstream
# cannot silently widen what leaves the process.
ADVISOR_REQUEST_FIELDS = (
    "advisory_request_version",
    "question",
    "case",
    "profile",
    "ambiguity_signals",
    "candidates",
    "constraint_summary",
)
ADVISOR_REQUEST_CASE_FIELDS = ("entity_type", "conflict")
ADVISOR_REQUEST_CANDIDATE_FIELDS = (
    "candidate_id",
    "strategy",
    "resulting_actions",
    "total_score",
    "objective_contributions",
)

# --- weigh_output contract (design §D.1) ----------------------------------

REQUIRED_WEIGH_KEYS = frozenset(
    {
        "policy_id",
        "policy_version",
        "policy_hash",
        "case",
        "profile",
        "evidence",
        "candidates",
        "ranking",
        "ambiguity",
        "constraint_evaluation",
    }
)
REQUIRED_WEIGH_CASE_KEYS = frozenset(
    {"entity_type", "agent_a", "agent_b", "conflict", "unresolved"}
)
REQUIRED_WEIGH_PROFILE_KEYS = frozenset({"profile_name", "weights"})
REQUIRED_WEIGH_EVIDENCE_KEYS = frozenset({"case_confidence", "contributing_agents"})
REQUIRED_WEIGH_CANDIDATE_KEYS = frozenset(
    {
        "candidate_id",
        "strategy",
        "preferred_agent",
        "resulting_actions",
        "total_score",
        "objective_impacts",
        "constraint_findings",
        "eligible",
        "eligibility_basis",
        "originating_confidence",
        "evidence_complete",
    }
)
REQUIRED_WEIGH_RANKING_KEYS = frozenset(
    {"candidate_id", "rank", "score_rank", "total_score", "eligible", "tie_group"}
)
REQUIRED_WEIGH_AMBIGUITY_KEYS = frozenset(
    {"detected", "signals", "near_tie_group", "top_gap"}
)
REQUIRED_WEIGH_CONSTRAINT_EVAL_KEYS = frozenset(
    {
        "authority",
        "rechecked_by",
        "constraints_checked",
        "violated_candidate_ids",
        "indeterminate_candidate_ids",
    }
)

# WEIGH declares itself advisory. If a future WEIGH ever claimed enforcement
# authority, GOVERN refuses to run rather than silently deferring to it.
EXPECTED_WEIGH_CONSTRAINT_AUTHORITY = "advisory_only"
EXPECTED_WEIGH_RECHECKED_BY = "GOVERN"

# GOVERN's own counterpart value.
GOVERN_CONSTRAINT_AUTHORITY = "enforcing"

REQUIRED_POLICY_SECTIONS = (
    "escalation",
    "authority",
    "hard_constraints",
    "claude",
    "fallback",
    "audit",
)

REQUIRED_FALLBACK_KEYS = (
    "on_claude_unavailable",
    "on_invalid_response",
    "on_timeout",
    "on_schema_violation",
)

# --- audit (design §O) -----------------------------------------------------

# The one required field GOVERN deliberately does not supply: GOVERN reads no
# clock (design §P.1), so the orchestrator stamps the receipt.
ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS = frozenset({"timestamp"})

AUDIT_FIELD_PATHS = {
    "policy_id": ("policy_id",),
    "policy_version": ("policy_version",),
    "policy_hash": ("policy_hash",),
    "decision_id": ("decision_id",),
    "profile_selected": ("profile_selected",),
    "objectives_considered": ("objectives_considered",),
    "weights_used": ("weights_used",),
    "hard_constraints_checked": ("permission_evaluation", "constraints_checked"),
    "candidates_considered": ("permission_evaluation", "candidates"),
    "selected_candidate": ("selected_candidate",),
    "outcome": ("outcome",),
    "rationale": ("rationale",),
    "claude_invoked": ("claude", "invoked"),
    "claude_output_used": ("claude", "output_used"),
}
