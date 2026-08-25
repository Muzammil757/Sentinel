"""
GOVERN: the only layer that names a winner and the only layer that authorizes
execution (docs/govern_layer_design.md).

decide() is a pure function: same four inputs (plus an absent or deterministic
advisor) produce a byte-identical output every time. It reads no clock, uses
no randomness, performs no I/O, imports no SDK, mutates none of its inputs,
and computes no score of its own -- it orders the permitted set by WEIGH's
total_score and compares that score against policy thresholds.

The seven phases, in order:

    Phase 0  PREFLIGHT   validate weigh_output, validate the policy sections
                         GOVERN needs, assert the policy identity matches
    Phase 1  RE-CHECK    re-derive every hard constraint from RAW evidence and
                         compare against WEIGH's advisory findings
    Phase 2  AUTHORITY   per-agent facts, the governance gate, and the
                         escalation-flag match (strategy AND actions)
    Phase 3  PERMIT      permitted = survivors of Phases 1-2, ordered by
                         (-weigh.total_score, candidate_id)
    Phase 4  OUTCOME     the decision table; exactly one outcome
    Phase 5  AUTHORIZE   execution_authorized = (outcome == "PROCEED");
                         decision_id computed here, BEFORE any advisor exists
    Phase 6  ADVISE      optional bounded advisory; may write only
                         rationale.claude_narrative, claude.*, and the one
                         documented AMBIGUOUS -> ESCALATE transition
    Phase 7  ASSEMBLE    output construction; audit-field completeness check

This module sequences and assembles. Every rule lives in permissions.py,
authority.py, outcome.py, or advisor.py, so no governance decision can hide
inside the orchestration.
"""

import copy
import hashlib
import json

from govern.advisor import (
    assert_claude_invariants,
    build_request,
    consult,
    evaluate_gate,
)
from govern.authority import authority_exceeded_codes, evaluate_authority
from govern.errors import GovernInputError, GovernPolicyError
from govern.outcome import (
    apply_advisor_fallback,
    applying_ambiguity_codes,
    decide_outcome,
)
from govern.permissions import blocking_constraint_codes, recheck_candidate
from govern.schema import (
    AUDIT_FIELD_PATHS,
    BASIS_ACTION_REQUIRES_ESCALATION,
    BASIS_AMBIGUITY_DETECTED,
    BASIS_CLAUDE_SCHEMA_VIOLATION,
    BASIS_GOVERN_WEIGH_DISAGREEMENT,
    BASIS_NO_CONFLICT_ALL_CHECKS_PASSED,
    BASIS_NO_PERMITTED_CANDIDATE,
    BASIS_SCORE_AT_OR_ABOVE_PROCEED_MIN,
    BASIS_SCORE_AT_OR_BELOW_HOLD_MAX,
    BASIS_SCORE_IN_MID_BAND,
    CLAUDE_ERROR_SCHEMA_VIOLATION,
    DECISION_METHOD,
    EXPECTED_WEIGH_CONSTRAINT_AUTHORITY,
    EXPECTED_WEIGH_RECHECKED_BY,
    FALLBACK_OUTCOME_ALIASES,
    GOVERN_CONSTRAINT_AUTHORITY,
    GOVERN_VERSION,
    MID_BAND_OUTCOMES,
    ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS,
    ORDERING_SOURCE,
    OUTCOME_ESCALATE,
    OUTCOME_PROCEED,
    REQUIRED_FALLBACK_KEYS,
    REQUIRED_OUTCOMES,
    REQUIRED_POLICY_SECTIONS,
    REQUIRED_WEIGH_AMBIGUITY_KEYS,
    REQUIRED_WEIGH_CANDIDATE_KEYS,
    REQUIRED_WEIGH_CASE_KEYS,
    REQUIRED_WEIGH_CONSTRAINT_EVAL_KEYS,
    REQUIRED_WEIGH_EVIDENCE_KEYS,
    REQUIRED_WEIGH_KEYS,
    REQUIRED_WEIGH_PROFILE_KEYS,
    REQUIRED_WEIGH_RANKING_KEYS,
)
from policy.loader import compute_policy_hash
from weigh.constraints import CONSTRAINT_EVALUATORS
from weigh.schema import FORBIDDEN_OUTPUT_KEYS

_MISSING = object()


# --------------------------------------------------------------------------
# Phase 0 -- preflight
# --------------------------------------------------------------------------


def _require_keys(mapping, required, label):
    if not isinstance(mapping, dict):
        raise GovernInputError(f"{label} must be a mapping")
    missing = set(required) - mapping.keys()
    if missing:
        raise GovernInputError(f"{label} is missing required key(s): {sorted(missing)}")


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def _validate_weigh_output(weigh_output, agent_actions, case_context):
    if not isinstance(agent_actions, dict):
        raise GovernInputError("agent_actions must be a mapping of agent name to payload")
    if not isinstance(case_context, dict):
        raise GovernInputError("case_context must be a mapping")

    _require_keys(weigh_output, REQUIRED_WEIGH_KEYS, "weigh_output")
    _require_keys(weigh_output["case"], REQUIRED_WEIGH_CASE_KEYS, "weigh_output.case")
    _require_keys(weigh_output["profile"], REQUIRED_WEIGH_PROFILE_KEYS, "weigh_output.profile")
    _require_keys(weigh_output["evidence"], REQUIRED_WEIGH_EVIDENCE_KEYS, "weigh_output.evidence")
    _require_keys(
        weigh_output["ambiguity"], REQUIRED_WEIGH_AMBIGUITY_KEYS, "weigh_output.ambiguity"
    )
    _require_keys(
        weigh_output["constraint_evaluation"],
        REQUIRED_WEIGH_CONSTRAINT_EVAL_KEYS,
        "weigh_output.constraint_evaluation",
    )

    candidates = weigh_output["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise GovernInputError("weigh_output.candidates must be a non-empty list")

    candidate_ids = []
    for index, candidate in enumerate(candidates):
        _require_keys(
            candidate, REQUIRED_WEIGH_CANDIDATE_KEYS, f"weigh_output.candidates[{index}]"
        )
        if not isinstance(candidate["constraint_findings"], list):
            raise GovernInputError(
                f"weigh_output.candidates[{index}].constraint_findings must be a list"
            )
        candidate_ids.append(candidate["candidate_id"])

    if len(candidate_ids) != len(set(candidate_ids)):
        raise GovernInputError("weigh_output.candidates contains duplicate candidate_id values")

    ranking = weigh_output["ranking"]
    if not isinstance(ranking, list):
        raise GovernInputError("weigh_output.ranking must be a list")
    for index, entry in enumerate(ranking):
        _require_keys(entry, REQUIRED_WEIGH_RANKING_KEYS, f"weigh_output.ranking[{index}]")
    if {entry["candidate_id"] for entry in ranking} != set(candidate_ids):
        raise GovernInputError(
            "weigh_output.ranking does not cover exactly weigh_output.candidates"
        )

    # WEIGH declares itself advisory. If a future WEIGH ever claimed
    # enforcement authority, GOVERN refuses to run rather than silently
    # deferring to it.
    constraint_evaluation = weigh_output["constraint_evaluation"]
    if constraint_evaluation["authority"] != EXPECTED_WEIGH_CONSTRAINT_AUTHORITY:
        raise GovernInputError(
            f"weigh_output.constraint_evaluation.authority must be "
            f"{EXPECTED_WEIGH_CONSTRAINT_AUTHORITY!r}, got "
            f"{constraint_evaluation['authority']!r}"
        )
    if constraint_evaluation["rechecked_by"] != EXPECTED_WEIGH_RECHECKED_BY:
        raise GovernInputError(
            f"weigh_output.constraint_evaluation.rechecked_by must be "
            f"{EXPECTED_WEIGH_RECHECKED_BY!r}, got "
            f"{constraint_evaluation['rechecked_by']!r}"
        )

    # GOVERN validates the layer above it rather than trusting it: a
    # weigh_output carrying a key WEIGH is forbidden to emit did not come from
    # WEIGH unmodified.
    forbidden_present = sorted(set(_walk_keys(weigh_output)) & FORBIDDEN_OUTPUT_KEYS)
    if forbidden_present:
        raise GovernInputError(
            f"weigh_output contains forbidden WEIGH output key(s): {forbidden_present}"
        )

    case = weigh_output["case"]
    for role in ("agent_a", "agent_b"):
        if case[role] not in agent_actions:
            raise GovernInputError(
                f"agent_actions is missing entry for {role} {case[role]!r}"
            )
    for candidate in candidates:
        preferred = candidate["preferred_agent"]
        if preferred is not None and preferred not in agent_actions:
            raise GovernInputError(
                f"candidate {candidate['candidate_id']!r} preferred_agent "
                f"{preferred!r} is not present in agent_actions"
            )


def _validate_policy(policy):
    if not isinstance(policy, dict):
        raise GovernPolicyError("policy must be a mapping")

    for section in REQUIRED_POLICY_SECTIONS:
        if section not in policy:
            raise GovernPolicyError(f"policy is missing required section {section!r}")

    escalation = policy["escalation"]
    outcomes = set(escalation.get("outcomes") or [])
    missing_outcomes = REQUIRED_OUTCOMES - outcomes
    if missing_outcomes:
        raise GovernPolicyError(
            f"policy.escalation.outcomes is missing required outcome(s): "
            f"{sorted(missing_outcomes)}"
        )

    thresholds = escalation.get("thresholds")
    if not isinstance(thresholds, dict):
        raise GovernPolicyError("policy.escalation.thresholds must be a mapping")

    for key in ("proceed_min_score", "hold_max_score"):
        value = thresholds.get(key, _MISSING)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GovernPolicyError(
                f"policy.escalation.thresholds.{key} must be numeric, got {value!r}"
            )
    if thresholds["hold_max_score"] > thresholds["proceed_min_score"]:
        raise GovernPolicyError(
            f"policy.escalation.thresholds.hold_max_score "
            f"({thresholds['hold_max_score']}) must not exceed proceed_min_score "
            f"({thresholds['proceed_min_score']})"
        )

    # The band hold_max_score < score < proceed_min_score has no rule without
    # this field, and it is reachable in ordinary operation. GOVERN reads the
    # band outcome from policy and refuses to guess -- hard-coding it would
    # put a governance threshold in application code, and inventing a third
    # threshold would be worse. Design §I.2 / §R.1.
    mid_band_outcome = thresholds.get("mid_band_outcome", _MISSING)
    if mid_band_outcome not in MID_BAND_OUTCOMES:
        raise GovernPolicyError(
            f"policy.escalation.thresholds.mid_band_outcome must be one of "
            f"{sorted(MID_BAND_OUTCOMES)} (an undefined score band may never "
            f"auto-execute), got "
            f"{'<missing>' if mid_band_outcome is _MISSING else repr(mid_band_outcome)}"
        )

    fallback = policy["fallback"]
    for key in REQUIRED_FALLBACK_KEYS:
        value = fallback.get(key, _MISSING)
        if value not in FALLBACK_OUTCOME_ALIASES:
            raise GovernPolicyError(
                f"policy.fallback.{key} = "
                f"{'<missing>' if value is _MISSING else repr(value)} cannot be "
                f"mapped onto a governance outcome; expected one of "
                f"{sorted(FALLBACK_OUTCOME_ALIASES)}"
            )

    assert_claude_invariants(policy)

    if not isinstance(policy["hard_constraints"], list):
        raise GovernPolicyError("policy.hard_constraints must be a list")
    for constraint in policy["hard_constraints"]:
        if not isinstance(constraint, dict) or constraint.get("id") not in CONSTRAINT_EVALUATORS:
            raise GovernPolicyError(
                f"No evaluator registered for hard constraint "
                f"{(constraint or {}).get('id') if isinstance(constraint, dict) else constraint!r}"
            )

    if not isinstance(policy["authority"].get("agents"), dict):
        raise GovernPolicyError("policy.authority.agents must be a mapping")

    if not isinstance(policy["audit"], dict):
        raise GovernPolicyError("policy.audit must be a mapping")
    required_fields = policy["audit"].get("required_fields") or []
    unsupported = sorted(
        field
        for field in required_fields
        if field not in AUDIT_FIELD_PATHS
        and field not in ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS
    )
    if unsupported:
        raise GovernPolicyError(
            f"policy.audit.required_fields names field(s) GOVERN cannot supply: "
            f"{unsupported}"
        )


def _preflight(weigh_output, agent_actions, case_context, policy):
    _validate_weigh_output(weigh_output, agent_actions, case_context)
    _validate_policy(policy)

    # It must be impossible to enforce policy B against numbers produced
    # under policy A.
    actual_hash = compute_policy_hash(policy)
    if actual_hash != weigh_output["policy_hash"]:
        raise GovernInputError(
            f"policy identity mismatch: weigh_output.policy_hash is "
            f"{weigh_output['policy_hash']!r} but the supplied policy hashes to "
            f"{actual_hash!r}"
        )


# --------------------------------------------------------------------------
# Phases 1-3 -- re-check, authority, permit
# --------------------------------------------------------------------------


def _evaluate_candidates(weigh_output, agent_actions, case_context, policy):
    case_confidence = weigh_output["evidence"]["case_confidence"]
    score_rank_by_id = {
        entry["candidate_id"]: entry["score_rank"] for entry in weigh_output["ranking"]
    }

    records = []
    disagreements = []

    for weigh_candidate in weigh_output["candidates"]:
        constraint_recheck, unauthorized_observed, candidate_disagreements = recheck_candidate(
            weigh_candidate, agent_actions, case_context, policy, case_confidence
        )
        disagreements.extend(candidate_disagreements)

        authority_block, governance_gate, gate_blocking = evaluate_authority(
            weigh_candidate, unauthorized_observed, policy
        )

        blocking = sorted(
            set(blocking_constraint_codes(constraint_recheck, weigh_candidate))
            | set(gate_blocking)
        )
        permitted = not blocking

        records.append(
            {
                "candidate_id": weigh_candidate["candidate_id"],
                "strategy": weigh_candidate["strategy"],
                "resulting_actions": list(weigh_candidate["resulting_actions"]),
                "total_score": weigh_candidate["total_score"],
                "score_rank": score_rank_by_id[weigh_candidate["candidate_id"]],
                "constraint_recheck": constraint_recheck,
                "authority": authority_block,
                "governance_gate": governance_gate,
                "permitted": permitted,
                "permission_basis": (
                    "all_checks_passed" if permitted else "blocked_by:" + ",".join(blocking)
                ),
                "blocking_reasons": blocking,
            }
        )

    # WEIGH's score, GOVERN's filter. Ordering the full record list the same
    # way makes the whole output invariant under a permutation of
    # weigh_output.candidates, and makes the receipt read top-down.
    records.sort(key=lambda record: (-record["total_score"], record["candidate_id"]))
    disagreements.sort(key=lambda d: (d["candidate_id"], d["constraint_id"]))

    permitted = [record for record in records if record["permitted"]]
    return records, permitted, disagreements


# --------------------------------------------------------------------------
# Phase 5 -- decision_id
# --------------------------------------------------------------------------


def _compute_decision_id(weigh_output, case_context):
    """
    A content fingerprint, not a unique event id: re-running the same case
    yields the same id, which is the desirable property for a receipt. The
    orchestrator pairs it with `timestamp` when per-run uniqueness is needed.

    case_context is included because weigh_output does not carry the amount.
    Two releases at different amounts produce byte-identical weigh_output (the
    score is 0.3100 at every amount), so without case_context their receipts
    would share a fingerprint -- including a 50 000 that is authorized and a
    50 001 that is not.

    Computed in Phase 5, before an advisor exists, so advisory content is
    structurally excluded and the id is identical with and without Claude.
    """

    payload = {
        "govern_version": GOVERN_VERSION,
        "policy_hash": weigh_output["policy_hash"],
        "case_context": case_context,
        "weigh_output": weigh_output,
    }
    try:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
    except (TypeError, ValueError) as exc:
        # A receipt that cannot be fingerprinted is not a receipt. Inputs
        # carrying non-serializable values are an integration fault, not an
        # evidence gap.
        raise GovernInputError(
            f"case_context and weigh_output must be JSON-serializable to compute "
            f"decision_id: {exc}"
        ) from exc

    return f"dec_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


# --------------------------------------------------------------------------
# Phase 7 -- assembly helpers
# --------------------------------------------------------------------------


def _escalation_reasons(records, permitted, disagreements, outcome_basis, claude_error):
    """
    Sorted, stable machine codes so the receipt and the UI can render an
    escalation without parsing prose (design §K). Populated only when the case
    is actually being escalated; per-candidate blocking detail lives in
    permission_evaluation.candidates[].blocking_reasons for every other
    outcome.
    """

    reasons = set()

    if not permitted:
        reasons.add(BASIS_NO_PERMITTED_CANDIDATE)

    for record in records:
        reasons.update(record["blocking_reasons"])
        reasons.update(authority_exceeded_codes(record["authority"]))

    for disagreement in disagreements:
        reasons.add(
            f"GOVERN_WEIGH_DISAGREEMENT:{disagreement['candidate_id']}:"
            f"{disagreement['constraint_id']}"
        )

    if outcome_basis == BASIS_ACTION_REQUIRES_ESCALATION and permitted:
        for match in permitted[0]["authority"]["escalation_matches"]:
            reasons.add(f"ACTION_REQUIRES_ESCALATION:{match}")

    if (
        outcome_basis == BASIS_CLAUDE_SCHEMA_VIOLATION
        or claude_error == CLAUDE_ERROR_SCHEMA_VIOLATION
    ):
        reasons.add(BASIS_CLAUDE_SCHEMA_VIOLATION)

    return sorted(reasons)


_OUTCOME_SENTENCES = {
    BASIS_NO_PERMITTED_CANDIDATE: (
        "ESCALATE: no candidate is permitted under this policy -- every option was "
        "blocked by a hard constraint or an authority rule, so nothing may execute "
        "autonomously."
    ),
    BASIS_GOVERN_WEIGH_DISAGREEMENT: (
        "ESCALATE: GOVERN's independent hard-constraint re-check disagreed with "
        "WEIGH's advisory finding, so no action may execute autonomously until a "
        "human resolves the disagreement."
    ),
}


def _outcome_sentence(outcome, outcome_basis, permitted, score_band, thresholds, ambiguity_codes):
    if outcome_basis in _OUTCOME_SENTENCES:
        return _OUTCOME_SENTENCES[outcome_basis]

    top_id = permitted[0]["candidate_id"] if permitted else None

    if outcome_basis == BASIS_ACTION_REQUIRES_ESCALATION:
        match = permitted[0]["authority"]["escalation_match"]
        return (
            f"ESCALATE: the top permitted candidate {top_id!r} matches an authority "
            f"rule requiring escalation ({match}), so it may be reviewed by a human "
            f"but never executed autonomously."
        )

    if outcome_basis == BASIS_AMBIGUITY_DETECTED:
        return (
            f"AMBIGUOUS: the comparison between the permitted candidates is not "
            f"decisive ({', '.join(ambiguity_codes)}), so candidate {top_id!r} is put "
            f"to a human reviewer rather than executed."
        )

    if outcome_basis == BASIS_NO_CONFLICT_ALL_CHECKS_PASSED:
        return (
            f"PROCEED: no conflict was detected, and candidate {top_id!r} passed every "
            f"hard-constraint re-check and authority check; the score band is not "
            f"read on a no-conflict case because there is nothing to compare against."
        )

    score = score_band["evaluated_score"]

    if outcome_basis == BASIS_SCORE_AT_OR_ABOVE_PROCEED_MIN:
        return (
            f"PROCEED: candidate {top_id!r} is permitted and its WEIGH score {score} "
            f"meets proceed_min_score {thresholds['proceed_min_score']}."
        )

    if outcome_basis == BASIS_SCORE_AT_OR_BELOW_HOLD_MAX:
        return (
            f"HOLD: candidate {top_id!r} is permitted but its WEIGH score {score} is at "
            f"or below hold_max_score {thresholds['hold_max_score']}."
        )

    if outcome_basis == BASIS_SCORE_IN_MID_BAND:
        return (
            f"{outcome}: candidate {top_id!r} is permitted but its WEIGH score {score} "
            f"falls between hold_max_score {thresholds['hold_max_score']} and "
            f"proceed_min_score {thresholds['proceed_min_score']}, which policy "
            f"resolves to {outcome} via mid_band_outcome."
        )

    # The only remaining basis is the post-advisor transition.
    return (
        "ESCALATE: the advisory response violated its response schema, so the case is "
        "routed to a human. Governance authorized nothing on either side of that "
        "transition."
    )


def _rationale_reasons(records, permitted, outcome_basis, ambiguity_codes):
    reasons = []

    any_blocking_constraint = any(
        entry["status"] in ("VIOLATED", "INDETERMINATE")
        for record in records
        for entry in record["constraint_recheck"]
    )
    reasons.append(
        "CONSTRAINTS_BLOCKING" if any_blocking_constraint else "CONSTRAINTS_RECHECKED_CLEAN"
    )

    any_authority_problem = any(
        authority_exceeded_codes(record["authority"]) for record in records
    ) or (bool(permitted) and permitted[0]["authority"]["requires_escalation"])
    reasons.append(
        "AUTHORITY_ESCALATION_REQUIRED" if any_authority_problem else "AUTHORITY_SATISFIED"
    )

    reasons.extend(f"AMBIGUITY_SIGNAL:{code}" for code in ambiguity_codes)
    reasons.append(outcome_basis)
    return reasons


def _resolve_path(output, path):
    node = output
    for step in path:
        if not isinstance(node, dict) or step not in node:
            return _MISSING
        node = node[step]
    return node


def _assert_audit_fields_supplied(output, policy):
    """
    A future policy edit that adds a required field fails loudly here instead
    of producing a quietly incomplete receipt.
    """

    for field in policy["audit"].get("required_fields") or []:
        if field in ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS:
            continue
        if _resolve_path(output, AUDIT_FIELD_PATHS[field]) is _MISSING:
            raise GovernPolicyError(
                f"audit.required_fields names {field!r}, which GOVERN's output does "
                f"not supply at {'.'.join(AUDIT_FIELD_PATHS[field])}"
            )


def _selected_candidate_view(record):
    return {
        "candidate_id": record["candidate_id"],
        "strategy": record["strategy"],
        "resulting_actions": list(record["resulting_actions"]),
        "total_score": record["total_score"],
        "score_rank": record["score_rank"],
        "permission_basis": record["permission_basis"],
    }


# --------------------------------------------------------------------------
# The public entry point
# --------------------------------------------------------------------------


def decide(weigh_output, agent_actions, case_context, policy, advisor=None):
    """
    Decide which candidate -- if any -- is actually permitted to execute under
    this policy, and what the case's governance outcome is.

    `advisor` is an optional injected port (govern.advisor.Advisor). None is
    the default and the demo-safe path: with no advisor, GOVERN is pure
    deterministic arithmetic over policy data and no model is involved.
    execution_authorized and decision_id are identical whether the advisor is
    present, absent, raising, timing out, or violating its schema.
    """

    # Phase 0 -- everything is checked before any work is done, so GOVERN
    # never emits a partial output.
    _preflight(weigh_output, agent_actions, case_context, policy)

    thresholds = policy["escalation"]["thresholds"]
    case = weigh_output["case"]
    ambiguity = weigh_output["ambiguity"]

    # Phases 1-3.
    records, permitted, disagreements = _evaluate_candidates(
        weigh_output, agent_actions, case_context, policy
    )
    agreed = not disagreements

    # Phase 4.
    outcome, outcome_basis, score_band = decide_outcome(
        permitted, agreed, ambiguity, case["conflict"], thresholds
    )

    # Phase 5 -- the single assignment of execution_authorized in the layer,
    # and the only place decision_id is computed. Both happen before an
    # advisor is reachable.
    execution_authorized = outcome == OUTCOME_PROCEED
    selected_candidate = (
        _selected_candidate_view(permitted[0]) if execution_authorized else None
    )
    authorized_actions = (
        list(permitted[0]["resulting_actions"]) if execution_authorized else []
    )
    candidate_under_review = permitted[0]["candidate_id"] if permitted else None
    decision_id = _compute_decision_id(weigh_output, case_context)

    permitted_candidate_ids = [record["candidate_id"] for record in permitted]
    ambiguity_codes = (
        applying_ambiguity_codes(ambiguity, len(permitted))
        if outcome_basis == BASIS_AMBIGUITY_DETECTED
        else []
    )

    # Phase 6 -- the advisor, if any. The outcome above is already final;
    # the only change reachable from here is the documented
    # AMBIGUOUS -> ESCALATE transition, which moves toward caution.
    gate = evaluate_gate(
        outcome,
        execution_authorized,
        [record["constraint_recheck"] for record in records],
        advisor,
    )

    claude = {
        "gate": gate,
        "invoked": False,
        "output_used": False,
        "error": None,
        "fallback_applied": None,
        "advisory": None,
    }
    claude_narrative = None
    notes = []

    if gate["eligible"]:
        assert_claude_invariants(policy)
        request = build_request(weigh_output, permitted)
        advisory, error = consult(advisor, request, permitted_candidate_ids)
        claude["invoked"] = True

        if error is None:
            claude["advisory"] = advisory
            claude["output_used"] = True
            claude_narrative = advisory["summary"]
        else:
            claude["error"] = error
            previous_outcome, previous_basis = outcome, outcome_basis
            outcome, outcome_basis, fallback_applied = apply_advisor_fallback(
                outcome, outcome_basis, error, policy
            )
            claude["fallback_applied"] = fallback_applied
            notes.append(
                {
                    "code": "G_CLAUDE_FALLBACK_APPLIED",
                    "message": (
                        f"Advisor failed with {error}; policy fallback "
                        f"{fallback_applied} recorded."
                    ),
                    "candidate_id": None,
                }
            )
            if outcome != previous_outcome:
                notes.append(
                    {
                        "code": "G_OUTCOME_TRANSITIONED",
                        "message": (
                            f"{previous_outcome} ({previous_basis}) transitioned to "
                            f"{outcome} on {error}; execution remained unauthorized "
                            f"throughout."
                        ),
                        "candidate_id": None,
                    }
                )

    # Phase 7 -- assembly.
    if score_band["reason_not_evaluated"] == "no_conflict_single_candidate":
        notes.append(
            {
                "code": "G_BAND_SKIPPED_NO_CONFLICT",
                "message": (
                    "No conflict: the score band was skipped and nothing else was. "
                    "Hard-constraint re-checks, authority enforcement, and the "
                    "governance gate all ran."
                ),
                "candidate_id": None,
            }
        )
    if outcome_basis == BASIS_SCORE_IN_MID_BAND:
        notes.append(
            {
                "code": "G_MID_BAND_OUTCOME_APPLIED",
                "message": (
                    f"Score fell between hold_max_score and proceed_min_score; policy "
                    f"mid_band_outcome resolved it to {outcome}."
                ),
                "candidate_id": None,
            }
        )
    for disagreement in disagreements:
        notes.append(
            {
                "code": "G_WEIGH_DISAGREEMENT",
                "message": (
                    f"GOVERN re-derived {disagreement['constraint_id']} as "
                    f"{disagreement['govern_status']}; WEIGH reported "
                    f"{disagreement['weigh_status']}."
                ),
                "candidate_id": disagreement["candidate_id"],
            }
        )

    objectives_considered = sorted(
        {
            objective
            for candidate in weigh_output["candidates"]
            for objective in candidate["objective_impacts"]
        }
    )

    output = {
        "govern_version": GOVERN_VERSION,
        "decision_method": DECISION_METHOD,
        "policy_id": weigh_output["policy_id"],
        "policy_version": weigh_output["policy_version"],
        "policy_hash": weigh_output["policy_hash"],
        "decision_id": decision_id,
        "case": copy.deepcopy(case),
        "profile_selected": weigh_output["profile"]["profile_name"],
        "weights_used": copy.deepcopy(weigh_output["profile"]["weights"]),
        "objectives_considered": objectives_considered,
        "outcome": outcome,
        "outcome_basis": outcome_basis,
        "execution_authorized": execution_authorized,
        "selected_candidate": selected_candidate,
        "authorized_actions": authorized_actions,
        "candidate_under_review": candidate_under_review,
        "score_band": score_band,
        "permission_evaluation": {
            "authority": GOVERN_CONSTRAINT_AUTHORITY,
            "constraints_checked": sorted(hc["id"] for hc in policy["hard_constraints"]),
            "candidates": records,
            "permitted_candidate_ids": permitted_candidate_ids,
            "ordering_source": ORDERING_SOURCE,
            "weigh_agreement": {"agreed": agreed, "disagreements": disagreements},
        },
        "escalation": {
            "required": outcome == OUTCOME_ESCALATE,
            "reasons": (
                _escalation_reasons(
                    records, permitted, disagreements, outcome_basis, claude["error"]
                )
                if outcome == OUTCOME_ESCALATE
                else []
            ),
            "actions_requiring_governance_matched": sorted(
                {
                    action
                    for record in records
                    for action in record["authority"]["requires_governance_actions"]
                }
            ),
            "escalation_matches": (
                list(permitted[0]["authority"]["escalation_matches"]) if permitted else []
            ),
        },
        "claude": claude,
        "rationale": {
            "outcome_sentence": _outcome_sentence(
                outcome, outcome_basis, permitted, score_band, thresholds, ambiguity_codes
            ),
            "reasons": _rationale_reasons(records, permitted, outcome_basis, ambiguity_codes),
            # The only field advisory text may ever occupy.
            "claude_narrative": claude_narrative,
        },
        "notes": sorted(notes, key=lambda note: (note["code"], note["candidate_id"] or "")),
    }

    _assert_audit_fields_supplied(output, policy)
    return output
