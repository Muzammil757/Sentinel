"""
Shared EXECUTOR test fixtures.

Every GOVERN document under test is produced by running the REAL pipeline
(agents -> conflict matrix -> RESOLVE -> WEIGH -> GOVERN) through
govern.conftest, so what EXECUTOR is tested against is what GOVERN actually
emits rather than a hand-written document that can drift from it. Tests then
tamper with a deepcopy of that document to reach the fail-closed paths --
most of which GOVERN itself cannot produce, which is precisely the point:
EXECUTOR must refuse a document that did not come from GOVERN unmodified.

Test infrastructure may import GOVERN. EXECUTOR's own source may not, and
test_executor_safety.py asserts that.
"""

import copy

from govern import decide
from govern.conftest import (
    no_conflict_release_case,
    payout_vs_dispute_case,
    rto_vs_retention_case,
    unresolved_case,
)


# --- real GOVERN decisions, one per outcome EXECUTOR has to handle --------


def authorized_hold_decision():
    """GOVERN design S.1 -- PROCEED, one authorized action: HOLD_RELATED_ACTIONS."""

    return decide(*payout_vs_dispute_case())


def authorized_release_decision(amount=50000):
    """
    GOVERN design S.3 -- PROCEED, two authorized actions in order:
    RELEASE_PAYMENT then CLOSE_CASE. The only money-moving path in the system,
    and so the one that most needs a mock executor rather than a real one.
    """

    return decide(*no_conflict_release_case(amount))


def escalated_decision():
    """S.3 at 50 001 -- ESCALATE. Same evidence, one rupee over the cap."""

    return decide(*no_conflict_release_case(50001))


def ambiguous_decision():
    """S.2 -- AMBIGUOUS, a near tie between two permitted candidates."""

    return decide(*rto_vs_retention_case())


def unresolved_decision():
    """RESOLVE's unresolved path: hold-both as the sole candidate."""

    return decide(*unresolved_case())


def unauthorized_decisions():
    """Every real GOVERN decision that did not authorize execution."""

    return [escalated_decision(), ambiguous_decision(), unresolved_decision()]


# --- tampering -------------------------------------------------------------


def tampered(decision, mutate):
    """Deepcopy `decision`, apply `mutate` to the copy, and return the copy."""

    copied = copy.deepcopy(decision)
    mutate(copied)
    return copied


def permission_record(decision, candidate_id):
    """The permission-evaluation row for one candidate."""

    for record in decision["permission_evaluation"]["candidates"]:
        if record["candidate_id"] == candidate_id:
            return record
    raise AssertionError(f"no permission record for {candidate_id!r}")


def rival_candidate_id(decision):
    """A permission-evaluated candidate that is NOT the authorized one."""

    authorized = decision["selected_candidate"]["candidate_id"]
    for record in decision["permission_evaluation"]["candidates"]:
        if record["candidate_id"] != authorized:
            return record["candidate_id"]
    raise AssertionError("decision has only one candidate")
