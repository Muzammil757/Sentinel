"""
EXECUTOR: the layer that performs an action, and the only layer downstream of
GOVERN's authorization boundary (docs/govern_layer_design.md, pipeline
position "GOVERN -> Action Executor").

EXECUTOR is not a decision layer. It answers one question:

    Did GOVERN explicitly authorize this action -- and if so, exactly which?

It chooses nothing, ranks nothing, scores nothing, and grants nothing. Every
authorizing fact on the receipt is copied out of GOVERN's document; the only
thing EXECUTOR contributes is the deterministic mock effect of doing what it
was told, and a refusal when it was not told clearly enough.

execute() is a pure function: the same GOVERN document (and the same optional
request) produces a byte-identical receipt every time. It reads no clock, uses
no randomness, performs no I/O, opens no socket or database, loads no policy,
imports no deciding layer, and mutates none of its inputs.

Three phases, in order:

    Phase 1  VERIFY    the authorization ladder (authorization.py); the only
                       phase that can decide anything, and it can only refuse
    Phase 2  PERFORM   deterministic mock execution of the authorized actions,
                       in the order GOVERN authorized them (actions.py)
    Phase 3  RECEIPT   assembly; every authorizing field traced back to GOVERN

A rejection is a receipt with `status: "REJECTED"`, never a raised exception
and never a silent no-op: refusing to act is exactly the kind of event an
audit log exists to hold.
"""

import copy
import hashlib
import json

from executor.actions import perform_all
from executor.authorization import verify
from executor.schema import (
    AUTHORIZATION_SOURCE,
    EXECUTION_METHOD,
    EXECUTION_MODE,
    EXECUTOR_VERSION,
    RECEIPT_ID_PREFIX,
    STATUS_EXECUTED,
    STATUS_REJECTED,
)


def _read(govern_output, *path):
    """
    Best-effort read of one GOVERN field for the audit link.

    Used only to build the back-reference on a receipt, including the receipts
    for documents too malformed to act on -- a rejection should still say
    which decision it was refusing. Anything unreadable becomes None rather
    than a guess.
    """

    node = govern_output
    for step in path:
        if not isinstance(node, dict) or step not in node:
            return None
        node = node[step]
    return node if isinstance(node, (str, bool, int, float)) or node is None else None


def _read_case(govern_output):
    """
    The case GOVERN decided, deep-copied so the receipt and the decision can
    never alias -- editing one must not edit the other.

    A case that cannot be serialized is dropped rather than carried: the
    ladder already refuses such a document, and the receipt recording that
    refusal must itself remain a storable, fingerprintable object.
    """

    case = govern_output.get("case") if isinstance(govern_output, dict) else None
    if not isinstance(case, dict):
        return None
    try:
        json.dumps(case, sort_keys=True, ensure_ascii=True)
    except (TypeError, ValueError):
        return None
    return copy.deepcopy(case)


def _authorization_block(govern_output, authorized):
    """
    The answer to "why did EXECUTOR do this?" -- and the answer is always
    GOVERN, named field by field.

    `govern_rationale` is GOVERN's own outcome sentence, copied verbatim.
    EXECUTOR writes no policy justification of its own: it has no policy to
    justify anything with.
    """

    return {
        "source": AUTHORIZATION_SOURCE,
        "govern_version": _read(govern_output, "govern_version"),
        "decision_id": _read(govern_output, "decision_id"),
        "policy_id": _read(govern_output, "policy_id"),
        "policy_version": _read(govern_output, "policy_version"),
        "policy_hash": _read(govern_output, "policy_hash"),
        "outcome": _read(govern_output, "outcome"),
        "outcome_basis": _read(govern_output, "outcome_basis"),
        "execution_authorized": _read(govern_output, "execution_authorized"),
        "authorized_candidate_id": authorized["candidate_id"] if authorized else None,
        "authorized_strategy": authorized["strategy"] if authorized else None,
        "authorized_actions": list(authorized["actions"]) if authorized else [],
        "permission_basis": authorized["permission_basis"] if authorized else None,
        "govern_rationale": _read(govern_output, "rationale", "outcome_sentence"),
    }


def _receipt_id(receipt):
    """
    A content fingerprint of the receipt, mirroring GOVERN's `decision_id`:
    re-executing the same authorization yields the same id, which is the
    property a receipt wants. No clock and no uuid, so the whole layer stays
    deterministic; the orchestrator pairs this with `timestamp` when per-run
    uniqueness is needed.
    """

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return RECEIPT_ID_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def execute(govern_output, request=None):
    """
    Perform the action GOVERN authorized -- or refuse, on the record.

    `govern_output` is a GOVERN decision document (govern.decide's return
    value). `request` is an optional caller assertion of what it believes it
    is executing: `{"candidate_id": ..., "actions": [...]}`, either key
    optional. It can only ever be compared against GOVERN's authorization;
    any difference is a rejection. Omit it to execute exactly what GOVERN
    authorized.

    Returns an execution receipt. `status` is "EXECUTED" or "REJECTED";
    `rejection` carries the machine-readable code and reason on the latter.
    """

    # Phase 1 -- the only phase that decides anything, and it can only refuse.
    authorized, checks, rejection = verify(govern_output, request)

    # Phase 2 -- mock execution, reached only past a clean ladder.
    executed_actions = perform_all(authorized["actions"]) if rejection is None else []

    # Phase 3 -- assembly.
    case = _read_case(govern_output)
    receipt = {
        "executor_version": EXECUTOR_VERSION,
        "execution_method": EXECUTION_METHOD,
        "execution_mode": EXECUTION_MODE,
        "status": STATUS_REJECTED if rejection is not None else STATUS_EXECUTED,
        "case": case,
        "authorization": _authorization_block(govern_output, authorized),
        "authorization_checks": checks,
        "executed_actions": executed_actions,
        "rejection": rejection,
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt
