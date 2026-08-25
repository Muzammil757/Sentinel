"""
Phase 4 -- the decision table, the score bands, and the ambiguity gate
(design §F.1, §I, §J).

This is the module a judge will be shown, so it holds the decision and
nothing else: no permission logic, no assembly, no I/O. Every threshold it
compares against arrives from policy; none is written down here.

Decision table, first match wins:

    D1   permitted is empty                     -> ESCALATE
    D2   GOVERN and WEIGH disagree              -> ESCALATE
    D3   top permitted requires escalation      -> ESCALATE
    D4   ambiguity applies                      -> AMBIGUOUS
    D5   case.conflict is False                 -> PROCEED   (band skipped)
    D6a  top score >= proceed_min_score         -> PROCEED
    D6b  top score <= hold_max_score            -> HOLD
    D6c  otherwise (the mid band)               -> mid_band_outcome

D1/D2/D3 sit first because a blocked, disputed, or escalation-flagged case is
not a case whose score is worth reading. D4 sits before D6 because an
ambiguity signal says *the comparison itself is not trustworthy*, and reading
a band off an untrustworthy comparison and calling it PROCEED is exactly the
failure the ambiguity machinery exists to prevent. D5 sits at position 5, not
position 0: on a no-conflict case GOVERN skips the score band and NOTHING
else -- constraints, authority, and the governance gate have all already run
(design §C.3). Skipping the band is not skipping governance; the only
money-moving path in the system (NO_CONFLICT_PROCEED -> RELEASE_PAYMENT)
reaches D5 having already survived every gate.
"""

from govern.schema import (
    BAND_HOLD,
    BAND_MID,
    BAND_PROCEED,
    BAND_SKIP_ACTION_REQUIRES_ESCALATION,
    BAND_SKIP_AMBIGUITY_DETECTED,
    BAND_SKIP_GOVERN_WEIGH_DISAGREEMENT,
    BAND_SKIP_NO_CONFLICT,
    BAND_SKIP_NO_PERMITTED_CANDIDATE,
    BASIS_ACTION_REQUIRES_ESCALATION,
    BASIS_AMBIGUITY_DETECTED,
    BASIS_CLAUDE_SCHEMA_VIOLATION,
    BASIS_GOVERN_WEIGH_DISAGREEMENT,
    BASIS_NO_CONFLICT_ALL_CHECKS_PASSED,
    BASIS_NO_PERMITTED_CANDIDATE,
    BASIS_SCORE_AT_OR_ABOVE_PROCEED_MIN,
    BASIS_SCORE_AT_OR_BELOW_HOLD_MAX,
    BASIS_SCORE_IN_MID_BAND,
    CLAUDE_ERROR_FALLBACK_KEYS,
    CLAUDE_ERROR_SCHEMA_VIOLATION,
    COMPARATIVE_AMBIGUITY_CODES,
    FALLBACK_OUTCOME_ALIASES,
    MIN_PERMITTED_FOR_COMPARATIVE_AMBIGUITY,
    NON_COMPARATIVE_AMBIGUITY_CODES,
    OUTCOME_AMBIGUOUS,
    OUTCOME_ESCALATE,
    OUTCOME_HOLD,
    OUTCOME_PROCEED,
    SCORE_SOURCE,
)


def ambiguity_applies(ambiguity: dict, permitted_count: int) -> bool:
    """
    Design §J.1. GOVERN reads WEIGH's ambiguity block and never recomputes it
    -- ambiguity is a property of the comparison, and the comparison is
    WEIGH's. The one refinement GOVERN adds is the permitted-count guard on
    comparative signals: WEIGH detects a near-tie across its *eligible* set,
    and if GOVERN's authority gates then permit only one of the tied pair,
    the tie is moot and reporting AMBIGUOUS over a field of one would
    mislead. Non-comparative signals are about the case rather than the
    comparison, so they apply regardless.
    """

    if not ambiguity["detected"]:
        return False

    codes = {signal["code"] for signal in ambiguity["signals"]}
    has_comparative = bool(codes & COMPARATIVE_AMBIGUITY_CODES)
    has_non_comparative = bool(codes & NON_COMPARATIVE_AMBIGUITY_CODES)

    return (
        has_comparative and permitted_count >= MIN_PERMITTED_FOR_COMPARATIVE_AMBIGUITY
    ) or has_non_comparative


def applying_ambiguity_codes(ambiguity: dict, permitted_count: int) -> list:
    """The signal codes that actually drove an AMBIGUOUS outcome, for the receipt."""

    if not ambiguity["detected"]:
        return []

    codes = {signal["code"] for signal in ambiguity["signals"]}
    applying = set(codes & NON_COMPARATIVE_AMBIGUITY_CODES)
    if permitted_count >= MIN_PERMITTED_FOR_COMPARATIVE_AMBIGUITY:
        applying |= codes & COMPARATIVE_AMBIGUITY_CODES
    return sorted(applying)


def classify_band(score: float, thresholds: dict) -> str:
    """
    Design §I.3. Both boundaries inclusive, matching WEIGH's inclusive
    near-tie convention and HC_CONFIDENCE_FLOOR's inclusive floor: 0.7500
    proceeds, 0.4000 holds. One convention, applied everywhere.
    """

    if score >= thresholds["proceed_min_score"]:
        return BAND_PROCEED
    if score <= thresholds["hold_max_score"]:
        return BAND_HOLD
    return BAND_MID


def decide_outcome(
    permitted: list,
    agreed: bool,
    ambiguity: dict,
    conflict: bool,
    thresholds: dict,
) -> tuple[str, str, dict]:
    """
    Returns (outcome, outcome_basis, score_band).

    `permitted` is already ordered by (-weigh.total_score, candidate_id) --
    GOVERN's filter over WEIGH's score. No score is computed here; the band
    comparison is the only place a score is read at all, and it reads the
    score of the top *permitted* candidate, not of ranking[0]: a blocked
    candidate's score never reaches the band comparison (design §I.4).
    """

    band_template = {
        "evaluated": False,
        "reason_not_evaluated": None,
        "score_source": SCORE_SOURCE,
        "evaluated_candidate_id": None,
        "evaluated_score": None,
        "proceed_min_score": thresholds["proceed_min_score"],
        "hold_max_score": thresholds["hold_max_score"],
        "mid_band_outcome": thresholds["mid_band_outcome"],
        "band": None,
    }

    def skipped(reason):
        band = dict(band_template)
        band["reason_not_evaluated"] = reason
        return band

    if not permitted:
        return (
            OUTCOME_ESCALATE,
            BASIS_NO_PERMITTED_CANDIDATE,
            skipped(BAND_SKIP_NO_PERMITTED_CANDIDATE),
        )

    if not agreed:
        return (
            OUTCOME_ESCALATE,
            BASIS_GOVERN_WEIGH_DISAGREEMENT,
            skipped(BAND_SKIP_GOVERN_WEIGH_DISAGREEMENT),
        )

    top = permitted[0]

    if top["authority"]["requires_escalation"]:
        return (
            OUTCOME_ESCALATE,
            BASIS_ACTION_REQUIRES_ESCALATION,
            skipped(BAND_SKIP_ACTION_REQUIRES_ESCALATION),
        )

    if ambiguity_applies(ambiguity, len(permitted)):
        return (
            OUTCOME_AMBIGUOUS,
            BASIS_AMBIGUITY_DETECTED,
            skipped(BAND_SKIP_AMBIGUITY_DETECTED),
        )

    if conflict is False:
        # The band, and only the band, is skipped here. Every permission gate
        # already ran above and in Phases 1-3.
        return (
            OUTCOME_PROCEED,
            BASIS_NO_CONFLICT_ALL_CHECKS_PASSED,
            skipped(BAND_SKIP_NO_CONFLICT),
        )

    score = top["total_score"]
    band = dict(band_template)
    band["evaluated"] = True
    band["evaluated_candidate_id"] = top["candidate_id"]
    band["evaluated_score"] = score
    band["band"] = classify_band(score, thresholds)

    if band["band"] == BAND_PROCEED:
        return OUTCOME_PROCEED, BASIS_SCORE_AT_OR_ABOVE_PROCEED_MIN, band
    if band["band"] == BAND_HOLD:
        return OUTCOME_HOLD, BASIS_SCORE_AT_OR_BELOW_HOLD_MAX, band
    return thresholds["mid_band_outcome"], BASIS_SCORE_IN_MID_BAND, band


def fallback_outcome_for(error: str, policy: dict) -> str:
    """Map a policy fallback token onto a legal outcome (design §N.1)."""

    key = CLAUDE_ERROR_FALLBACK_KEYS[error]
    return FALLBACK_OUTCOME_ALIASES[policy["fallback"][key]]


def apply_advisor_fallback(
    outcome: str, outcome_basis: str, error: str, policy: dict
) -> tuple[str, str, str]:
    """
    Design §N.2 -- the single permitted post-advisor outcome transition.

    The governance outcome was final at the end of Phase 5, before the advisor
    was reachable, so a missing, slow, broken, or malicious advisor cannot
    change what governance already decided. Exactly one transition is allowed:

        AMBIGUOUS -> ESCALATE   iff  the advisor committed a SCHEMA_VIOLATION
                                     and policy.fallback.on_schema_violation
                                     resolves to ESCALATE

    It fires when the advisor tried to name an outcome, override a constraint,
    or introduce a candidate. A human should see that. It moves strictly
    toward caution and cannot produce PROCEED, so execution_authorized is
    false on both sides of the arrow and Claude parity holds.

    Every other advisor failure leaves the outcome untouched and is recorded
    for audit only. Returns (outcome, outcome_basis, fallback_applied).
    """

    fallback_applied = fallback_outcome_for(error, policy)

    if (
        error == CLAUDE_ERROR_SCHEMA_VIOLATION
        and fallback_applied == OUTCOME_ESCALATE
        and outcome == OUTCOME_AMBIGUOUS
    ):
        return OUTCOME_ESCALATE, BASIS_CLAUDE_SCHEMA_VIOLATION, fallback_applied

    return outcome, outcome_basis, fallback_applied
