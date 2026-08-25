"""
The Claude boundary (design §L, §M).

Claude is a **port, not a dependency**. This package must not import
`anthropic`, an HTTP client, or any SDK -- an ast-based test proves that
structurally rather than by convention. A real Anthropic-backed adapter, if
the team wants one for the demo, lives outside this package and is wired by
the orchestrator; nothing here requires it and no invariant depends on it.

Everything the advisor can do is bounded three ways, not one:

  (a) the gate -- it is reachable only on an AMBIGUOUS case with no blocking
      constraint anywhere and with execution_authorized already False;
  (b) the response validator below -- an exact five-key allowlist, a
      recursive denylist, and a candidate-id check against the permitted set;
  (c) the assembly order -- decision_id and execution_authorized are computed
      in Phase 5, before an advisor exists in Phase 6.

Advisory text is inert. It is never eval'd, never parsed as JSON, never used
as a dict key, and never used to look anything up. It is copied into
rationale.claude_narrative and stored under claude.advisory, and nowhere else.

This module never decides an outcome. It reports what happened to the caller,
and govern.py applies the one documented transition through outcome.py -- so
"the advisor changed the outcome" is not expressible here.
"""

from typing import Optional, Protocol

from govern.errors import GovernPolicyError
from govern.schema import (
    ADVISOR_REQUEST_CANDIDATE_FIELDS,
    ADVISOR_REQUEST_CASE_FIELDS,
    ADVISOR_REQUEST_FIELDS,
    ADVISORY_FORBIDDEN_KEYS,
    ADVISORY_MAX_TRADEOFFS,
    ADVISORY_QUESTION,
    ADVISORY_REQUEST_VERSION,
    ADVISORY_REQUIRED_KEYS,
    ADVISORY_SUMMARY_MAX,
    ADVISORY_TEXT_MAX,
    ADVISORY_VERSION,
    BLOCKING_CONSTRAINT_STATUSES,
    CLAUDE_ERROR_INVALID_RESPONSE,
    CLAUDE_ERROR_SCHEMA_VIOLATION,
    CLAUDE_ERROR_TIMEOUT,
    CLAUDE_ERROR_UNAVAILABLE,
    CLAUDE_FORBIDDEN_CAPABILITY_FLAGS,
    GATE_BLOCKING_CONSTRAINT_PRESENT,
    GATE_EXECUTION_AUTHORIZED,
    GATE_NO_ADVISOR_INJECTED,
    GATE_OUTCOME_NOT_AMBIGUOUS,
    OUTCOME_AMBIGUOUS,
)


class AdvisorTimeout(Exception):
    """Raised by an adapter whose own deadline expired.

    GOVERN never sleeps, never retries, and never sets a deadline -- the port
    owns its timeout (design §N.3), and this is how it says so. Any other
    exception from an adapter is treated as UNAVAILABLE.
    """


class Advisor(Protocol):
    def explain(self, request: dict) -> Optional[dict]:
        """Return an advisory dict, or None if unavailable. Should not raise;
        if it does, GOVERN treats it as UNAVAILABLE. Owns its own timeout."""


class NullAdvisor:
    """The default. With no advisor injected, GOVERN is pure deterministic
    arithmetic over policy data and no model is involved at any point."""

    def explain(self, request: dict) -> None:
        return None


def evaluate_gate(outcome, execution_authorized, all_constraint_rechecks, advisor) -> dict:
    """
    Design §L.2. All four conditions must hold, and all four are recorded.

    Condition 3 (execution_authorized is False) is redundant with condition 1
    today, since D4 always yields AMBIGUOUS and AMBIGUOUS never authorizes.
    It is asserted anyway because it is the invariant that must survive any
    future edit to the decision table: an advisor can never be reached on a
    path that authorizes execution.
    """

    reasons = []

    if outcome != OUTCOME_AMBIGUOUS:
        reasons.append(GATE_OUTCOME_NOT_AMBIGUOUS)

    if any(
        entry["status"] in BLOCKING_CONSTRAINT_STATUSES
        for recheck in all_constraint_rechecks
        for entry in recheck
    ):
        reasons.append(GATE_BLOCKING_CONSTRAINT_PRESENT)

    if execution_authorized:
        reasons.append(GATE_EXECUTION_AUTHORIZED)

    if advisor is None or isinstance(advisor, NullAdvisor):
        reasons.append(GATE_NO_ADVISOR_INJECTED)

    return {"eligible": not reasons, "reasons": sorted(reasons)}


def assert_claude_invariants(policy: dict) -> None:
    """Re-assert the four policy invariants at the call site, where they
    matter, even though policy.loader already enforces them at load time."""

    claude = policy["claude"]
    for flag in CLAUDE_FORBIDDEN_CAPABILITY_FLAGS:
        if claude.get(flag) is not False:
            raise GovernPolicyError(
                f"policy.claude.{flag} must be explicitly false before an "
                f"advisor may be consulted"
            )


def build_request(weigh_output: dict, permitted: list) -> dict:
    """
    Design §L.3. The request is BUILT from an explicit whitelist, never
    filtered out of an upstream payload -- so adding a field to any upstream
    structure cannot silently widen what leaves the process.

    agent_actions, case_context, and the policy dict are never passed.
    Amounts, merchant identifiers, case ids, dispute ids, and raw agent
    payloads are excluded: an explanation of *why two governance options are
    close* does not need them.
    """

    weigh_by_id = {c["candidate_id"]: c for c in weigh_output["candidates"]}
    case = weigh_output["case"]

    candidates = []
    for record in permitted:
        weigh_candidate = weigh_by_id[record["candidate_id"]]
        available = {
            "candidate_id": record["candidate_id"],
            "strategy": record["strategy"],
            "resulting_actions": list(record["resulting_actions"]),
            "total_score": record["total_score"],
            "objective_contributions": {
                objective: impact["contribution"]
                for objective, impact in sorted(weigh_candidate["objective_impacts"].items())
            },
        }
        candidates.append(
            {field: available[field] for field in ADVISOR_REQUEST_CANDIDATE_FIELDS}
        )

    constraint_summary = sorted(
        {
            (entry["constraint_id"], entry["status"])
            for record in permitted
            for entry in record["constraint_recheck"]
        }
    )

    request = {
        "advisory_request_version": ADVISORY_REQUEST_VERSION,
        "question": ADVISORY_QUESTION,
        "case": {field: case[field] for field in ADVISOR_REQUEST_CASE_FIELDS},
        "profile": weigh_output["profile"]["profile_name"],
        "ambiguity_signals": [
            {"code": signal["code"], "detail": signal.get("detail", {})}
            for signal in weigh_output["ambiguity"]["signals"]
        ],
        "candidates": candidates,
        "constraint_summary": [
            {"constraint_id": constraint_id, "status": status}
            for constraint_id, status in constraint_summary
        ],
    }

    # Whitelist projection: identical content, built to prove the key set is
    # closed rather than merely believed to be.
    return {field: request[field] for field in ADVISOR_REQUEST_FIELDS}


def _is_text(value, max_length: int) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= max_length


def _contains_forbidden_key(node) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ADVISORY_FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_key(value):
                return True
    elif isinstance(node, list):
        return any(_contains_forbidden_key(item) for item in node)
    return False


def validate_advisory(raw, permitted_candidate_ids: list) -> tuple[Optional[dict], Optional[str]]:
    """
    Design §M.3 -- deterministic, in GOVERN, no model involved.

    Any failure discards the advisory WHOLE: no partial acceptance, no
    field-level salvage. Returns (advisory, error_code); exactly one is None.
    """

    if not isinstance(raw, dict) or set(raw.keys()) != set(ADVISORY_REQUIRED_KEYS):
        return None, CLAUDE_ERROR_SCHEMA_VIOLATION

    if raw["advisory_version"] != ADVISORY_VERSION:
        return None, CLAUDE_ERROR_INVALID_RESPONSE

    if not _is_text(raw["summary"], ADVISORY_SUMMARY_MAX):
        return None, CLAUDE_ERROR_INVALID_RESPONSE

    tradeoffs = raw["key_tradeoffs"]
    if not isinstance(tradeoffs, list) or len(tradeoffs) > ADVISORY_MAX_TRADEOFFS:
        return None, CLAUDE_ERROR_INVALID_RESPONSE
    if not all(_is_text(item, ADVISORY_TEXT_MAX) for item in tradeoffs):
        return None, CLAUDE_ERROR_INVALID_RESPONSE

    note = raw["confidence_note"]
    if note is not None and not _is_text(note, ADVISORY_TEXT_MAX):
        return None, CLAUDE_ERROR_INVALID_RESPONSE

    # Anything other than null or an id GOVERN itself permitted -- including a
    # valid-looking id GOVERN did not permit, or an entirely new one -- is an
    # attempt to introduce a candidate, which is a schema violation, not a
    # malformed value.
    suggested = raw["suggested_candidate_id"]
    if suggested is not None and suggested not in permitted_candidate_ids:
        return None, CLAUDE_ERROR_SCHEMA_VIOLATION

    if _contains_forbidden_key(raw):
        return None, CLAUDE_ERROR_SCHEMA_VIOLATION

    advisory = {
        "advisory_version": raw["advisory_version"],
        "summary": raw["summary"],
        "key_tradeoffs": list(tradeoffs),
        # Survives validation as NON-BINDING narrative. On an AMBIGUOUS case a
        # human is reviewing anyway, and "of the two permitted options 0.01
        # apart, the advisor points at the hold, because ..." is genuinely
        # useful -- it costs nothing, because the outcome is already
        # AMBIGUOUS and execution_authorized is already false.
        "suggested_candidate_id": suggested,
        "confidence_note": note,
    }
    return advisory, None


def consult(advisor, request: dict, permitted_candidate_ids: list) -> tuple[Optional[dict], Optional[str]]:
    """
    Call the injected port and contain every way it can fail.

    An unavailable model must never take the governance layer down, so no
    exception from an adapter escapes this function.
    """

    try:
        raw = advisor.explain(request)
    except AdvisorTimeout:
        return None, CLAUDE_ERROR_TIMEOUT
    except Exception:
        return None, CLAUDE_ERROR_UNAVAILABLE

    if raw is None:
        return None, CLAUDE_ERROR_UNAVAILABLE

    return validate_advisory(raw, permitted_candidate_ids)
