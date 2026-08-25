"""
The authorization ladder: every check EXECUTOR runs before it will perform
anything, in a fixed order, each rung able only to REFUSE.

The single rule this module exists to enforce:

    EXECUTOR performs the action GOVERN authorized, or it performs nothing.

There is deliberately no rung that can turn a "no" into a "yes". Each check
either passes and hands control to the next, or fails and ends the ladder
with a rejection code. The ladder ranks nothing, reads no policy, computes no
number of its own, and never looks at a candidate other than the one GOVERN
named -- if the document authorizes candidate A, EXECUTOR does not go looking
for a better B.

Fail-closed is expressed as a returned rejection rather than a raised
exception: a refusal is an auditable outcome that belongs on the receipt, not
an event a caller can swallow with `except`.
"""

import json

from executor.actions import unsupported
from executor.schema import (
    AUTHORIZING_OUTCOME,
    CHECK_ACTIONS_SUPPORTED,
    CHECK_AUTHORIZED_ACTION_PRESENT,
    CHECK_AUTHORIZED_ACTIONS_MATCH_CANDIDATE,
    CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
    CHECK_AUTHORIZED_CANDIDATE_PRESENT,
    CHECK_EXECUTION_AUTHORIZED_BY_GOVERN,
    CHECK_FAIL,
    CHECK_GOVERN_OUTPUT_WELL_FORMED,
    CHECK_OUTCOME_CONSISTENT_WITH_AUTHORIZATION,
    CHECK_PASS,
    CHECK_REQUEST_MATCHES_AUTHORIZATION,
    REJECT_AUTHORIZATION_INCONSISTENT,
    REJECT_AUTHORIZATION_MISSING,
    REJECT_AUTHORIZED_ACTION_MISSING,
    REJECT_AUTHORIZED_CANDIDATE_MISSING,
    REJECT_CANDIDATE_NOT_PERMITTED,
    REJECT_EXECUTION_NOT_AUTHORIZED,
    REJECT_GOVERN_OUTPUT_MALFORMED,
    REJECT_REQUEST_MALFORMED,
    REJECT_REQUESTED_ACTION_MISMATCH,
    REJECT_REQUESTED_CANDIDATE_MISMATCH,
    REJECT_UNSUPPORTED_ACTION,
    REQUEST_FIELDS,
    REQUIRED_GOVERN_KEYS,
    REQUIRED_PERMISSION_EVALUATION_KEYS,
    REQUIRED_PERMISSION_RECORD_KEYS,
    REQUIRED_SELECTED_CANDIDATE_KEYS,
)


class _Ladder:
    """Records the rungs that ran, so the receipt can show the trail."""

    def __init__(self):
        self.checks = []

    def passed(self, check):
        self.checks.append({"check": check, "result": CHECK_PASS})

    def failed(self, check, code, reason, detail=None):
        """End the ladder. Returns verify()'s full (authorized, checks, rejection)."""

        self.checks.append({"check": check, "result": CHECK_FAIL})
        return None, self.checks, {"code": code, "reason": reason, "detail": detail}


def _missing(mapping, required):
    return sorted(set(required) - mapping.keys())


def _is_action_list(value):
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _shape_problem(govern_output):
    """
    The structural contract, checked before any field is trusted. Returns a
    human-readable problem, or None when the document is well formed.

    A malformed document is never patched up. EXECUTOR has no way to know
    which half of a self-contradictory receipt was the real decision, so it
    refuses the whole thing.
    """

    if not isinstance(govern_output, dict):
        return "govern_output must be a mapping"

    missing = _missing(govern_output, REQUIRED_GOVERN_KEYS)
    if missing:
        return f"govern_output is missing required key(s): {missing}"

    if not isinstance(govern_output["execution_authorized"], bool):
        return "govern_output.execution_authorized must be a boolean"
    if not isinstance(govern_output["outcome"], str) or not govern_output["outcome"]:
        return "govern_output.outcome must be a non-empty string"
    if not isinstance(govern_output["case"], dict):
        return "govern_output.case must be a mapping"
    if not isinstance(govern_output["rationale"], dict):
        return "govern_output.rationale must be a mapping"
    if not _is_action_list(govern_output["authorized_actions"]):
        return "govern_output.authorized_actions must be a list of non-empty strings"

    evaluation = govern_output["permission_evaluation"]
    if not isinstance(evaluation, dict):
        return "govern_output.permission_evaluation must be a mapping"
    missing = _missing(evaluation, REQUIRED_PERMISSION_EVALUATION_KEYS)
    if missing:
        return f"govern_output.permission_evaluation is missing required key(s): {missing}"
    if not isinstance(evaluation["candidates"], list) or not evaluation["candidates"]:
        return "govern_output.permission_evaluation.candidates must be a non-empty list"
    if not isinstance(evaluation["permitted_candidate_ids"], list):
        return "govern_output.permission_evaluation.permitted_candidate_ids must be a list"

    # A receipt that cannot be serialized cannot be audited, stored, or
    # fingerprinted -- refused here rather than discovered after the actions
    # have already been performed.
    try:
        json.dumps(govern_output, sort_keys=True, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        return f"govern_output must be JSON-serializable: {exc}"

    return None


def _candidate_problem(candidate):
    if not isinstance(candidate, dict):
        return "govern_output.selected_candidate is absent or not a mapping"
    missing = _missing(candidate, REQUIRED_SELECTED_CANDIDATE_KEYS)
    if missing:
        return f"govern_output.selected_candidate is missing required key(s): {missing}"
    if not isinstance(candidate["candidate_id"], str) or not candidate["candidate_id"]:
        return "govern_output.selected_candidate.candidate_id must be a non-empty string"
    if not _is_action_list(candidate["resulting_actions"]):
        return (
            "govern_output.selected_candidate.resulting_actions must be a list of "
            "non-empty strings"
        )
    return None


def _permission_record(evaluation, candidate_id):
    """
    The authorized candidate's own row in GOVERN's permission evaluation.

    Exactly one row must carry the id. Zero means the authorization names a
    candidate GOVERN never evaluated; more than one means the document is
    ambiguous about which row applies, and EXECUTOR does not choose.
    """

    matches = [
        record
        for record in evaluation["candidates"]
        if isinstance(record, dict) and record.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        return None, len(matches)
    return matches[0], 1


def _request_problem(request, candidate_id, authorized_actions):
    """
    Compare the caller's assertion of what it is executing against GOVERN's
    authorization. Returns `(rejection_code, reason)` or `(None, None)`.

    A request can only ever narrow the ladder, never widen it: it is compared,
    and any difference refuses. This is the rung that stops an orchestrator,
    an API handler, or a UI from naming a different candidate -- a
    better-scoring one included -- than the one GOVERN authorized.
    """

    if not isinstance(request, dict) or not request:
        return REJECT_REQUEST_MALFORMED, "request must be a non-empty mapping when supplied"

    unknown = sorted(request.keys() - REQUEST_FIELDS)
    if unknown:
        return REJECT_REQUEST_MALFORMED, f"request carries unknown field(s): {unknown}"

    if "candidate_id" in request and request["candidate_id"] != candidate_id:
        return (
            REJECT_REQUESTED_CANDIDATE_MISMATCH,
            f"request names candidate {request['candidate_id']!r}; "
            f"GOVERN authorized {candidate_id!r}",
        )

    if "actions" in request:
        requested = request["actions"]
        if not _is_action_list(requested):
            return REJECT_REQUEST_MALFORMED, "request.actions must be a list of non-empty strings"
        if requested != authorized_actions:
            return (
                REJECT_REQUESTED_ACTION_MISMATCH,
                f"request names actions {requested}; GOVERN authorized {authorized_actions}",
            )

    return None, None


def verify(govern_output, request=None):
    """
    Run the ladder.

    Returns `(authorized, checks, rejection)`:

      * `authorized` -- on success, exactly what GOVERN authorized:
        `{"candidate_id", "strategy", "permission_basis", "actions"}`; None on
        any rejection.
      * `checks` -- the rungs that ran, in order, ending at the first failure.
      * `rejection` -- None on success, else `{"code", "reason", "detail"}`.

    No field of the returned authorization is EXECUTOR's own judgement; each
    one is copied out of GOVERN's document after being checked against it.
    """

    ladder = _Ladder()

    # 1. There is a document, and it is shaped like a GOVERN decision.
    if govern_output is None or govern_output == {}:
        return ladder.failed(
            CHECK_GOVERN_OUTPUT_WELL_FORMED,
            REJECT_AUTHORIZATION_MISSING,
            "no GOVERN authorization was supplied",
            "govern_output is empty; EXECUTOR has no authority of its own to fall back on",
        )

    problem = _shape_problem(govern_output)
    if problem is not None:
        return ladder.failed(
            CHECK_GOVERN_OUTPUT_WELL_FORMED,
            REJECT_GOVERN_OUTPUT_MALFORMED,
            "GOVERN output is malformed and was not repaired",
            problem,
        )
    ladder.passed(CHECK_GOVERN_OUTPUT_WELL_FORMED)

    # 2. GOVERN said yes -- as a literal True, not as anything merely truthy.
    if govern_output["execution_authorized"] is not True:
        return ladder.failed(
            CHECK_EXECUTION_AUTHORIZED_BY_GOVERN,
            REJECT_EXECUTION_NOT_AUTHORIZED,
            "GOVERN did not authorize execution",
            f"outcome {govern_output['outcome']!r} with execution_authorized "
            f"{govern_output['execution_authorized']!r}",
        )
    ladder.passed(CHECK_EXECUTION_AUTHORIZED_BY_GOVERN)

    # 3. ...and the rest of the document agrees that it said yes. GOVERN
    #    derives execution_authorized from the outcome in exactly one place,
    #    so a document where the two disagree did not come from GOVERN
    #    unmodified.
    if govern_output["outcome"] != AUTHORIZING_OUTCOME:
        return ladder.failed(
            CHECK_OUTCOME_CONSISTENT_WITH_AUTHORIZATION,
            REJECT_AUTHORIZATION_INCONSISTENT,
            "authorization evidence contradicts the outcome",
            f"execution_authorized is True but outcome is {govern_output['outcome']!r}, "
            f"not {AUTHORIZING_OUTCOME!r}",
        )
    ladder.passed(CHECK_OUTCOME_CONSISTENT_WITH_AUTHORIZATION)

    # 4. There is a named candidate to execute.
    candidate = govern_output["selected_candidate"]
    problem = _candidate_problem(candidate)
    if problem is not None:
        return ladder.failed(
            CHECK_AUTHORIZED_CANDIDATE_PRESENT,
            REJECT_AUTHORIZED_CANDIDATE_MISSING,
            "GOVERN authorized execution without naming an executable candidate",
            problem,
        )
    ladder.passed(CHECK_AUTHORIZED_CANDIDATE_PRESENT)

    candidate_id = candidate["candidate_id"]
    evaluation = govern_output["permission_evaluation"]

    # 5. GOVERN's own permission evaluation still clears that candidate. A
    #    candidate GOVERN blocked cannot execute even when the authorization
    #    fields above point straight at it.
    if candidate_id not in evaluation["permitted_candidate_ids"]:
        return ladder.failed(
            CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
            REJECT_CANDIDATE_NOT_PERMITTED,
            "the authorized candidate is not in GOVERN's permitted set",
            f"{candidate_id!r} is absent from permitted_candidate_ids",
        )

    record, match_count = _permission_record(evaluation, candidate_id)
    if record is None:
        return ladder.failed(
            CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
            REJECT_CANDIDATE_NOT_PERMITTED,
            "the authorized candidate has no single permission record",
            f"{candidate_id!r} matched {match_count} record(s) in permission_evaluation",
        )

    missing = _missing(record, REQUIRED_PERMISSION_RECORD_KEYS)
    if missing:
        return ladder.failed(
            CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
            REJECT_CANDIDATE_NOT_PERMITTED,
            "the authorized candidate's permission record is incomplete",
            f"{candidate_id!r} record is missing required key(s): {missing}",
        )

    if record["permitted"] is not True or record["blocking_reasons"]:
        return ladder.failed(
            CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
            REJECT_CANDIDATE_NOT_PERMITTED,
            "the authorized candidate is blocked by GOVERN",
            f"{candidate_id!r} has permitted={record['permitted']!r} and "
            f"blocking_reasons={record['blocking_reasons']!r}",
        )
    ladder.passed(CHECK_AUTHORIZED_CANDIDATE_PERMITTED)

    # 6. The authorized actions are that candidate's actions -- as GOVERN
    #    recorded them in BOTH places. This is what makes it impossible to
    #    attach one candidate's identity to another candidate's actions.
    authorized_actions = govern_output["authorized_actions"]
    if (
        authorized_actions != candidate["resulting_actions"]
        or authorized_actions != record["resulting_actions"]
    ):
        return ladder.failed(
            CHECK_AUTHORIZED_ACTIONS_MATCH_CANDIDATE,
            REJECT_AUTHORIZATION_INCONSISTENT,
            "the authorized actions do not match the authorized candidate",
            f"authorized_actions={authorized_actions}, "
            f"selected_candidate.resulting_actions={candidate['resulting_actions']}, "
            f"permission record resulting_actions={record['resulting_actions']}",
        )
    ladder.passed(CHECK_AUTHORIZED_ACTIONS_MATCH_CANDIDATE)

    # 7. There is actually something to do. An authorization naming no action
    #    authorizes nothing, and EXECUTOR does not invent one.
    if not authorized_actions:
        return ladder.failed(
            CHECK_AUTHORIZED_ACTION_PRESENT,
            REJECT_AUTHORIZED_ACTION_MISSING,
            "GOVERN authorized no action to execute",
            f"{candidate_id!r} authorizes an empty action list",
        )
    ladder.passed(CHECK_AUTHORIZED_ACTION_PRESENT)

    # 8. The caller, if it asserted anything, asserted this exact thing.
    if request is not None:
        code, reason = _request_problem(request, candidate_id, authorized_actions)
        if code is not None:
            return ladder.failed(
                CHECK_REQUEST_MATCHES_AUTHORIZATION,
                code,
                "the execution request does not match GOVERN's authorization",
                reason,
            )
    ladder.passed(CHECK_REQUEST_MATCHES_AUTHORIZATION)

    # 9. EXECUTOR knows how to perform every one of them. An unknown action is
    #    a refusal of the whole authorization, never a partial execution of
    #    the actions it happened to recognise.
    unknown = unsupported(authorized_actions)
    if unknown:
        return ladder.failed(
            CHECK_ACTIONS_SUPPORTED,
            REJECT_UNSUPPORTED_ACTION,
            "GOVERN authorized an action EXECUTOR has no way to perform",
            f"unsupported action(s): {unknown}",
        )
    ladder.passed(CHECK_ACTIONS_SUPPORTED)

    authorized = {
        "candidate_id": candidate_id,
        "strategy": candidate["strategy"],
        "permission_basis": candidate["permission_basis"],
        "actions": list(authorized_actions),
    }
    return authorized, ladder.checks, None
