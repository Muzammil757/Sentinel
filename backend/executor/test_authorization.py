"""
The authorization ladder, rung by rung.

Each test drives the ladder to exactly one rung and asserts the rejection code
it produces, so a future change that reorders or weakens a rung fails here
rather than silently somewhere downstream.

The ladder is the whole of EXECUTOR's decision-making, and every branch of it
is a refusal. There is no test below that turns a "no" into a "yes", because
there is no code path that could make one pass.
"""

import pytest

from executor.authorization import verify
from executor.conftest import (
    ambiguous_decision,
    authorized_hold_decision,
    authorized_release_decision,
    escalated_decision,
    permission_record,
    rival_candidate_id,
    tampered,
)
from executor.schema import (
    CHECK_FAIL,
    CHECK_ORDER,
    CHECK_PASS,
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
    REJECTION_CODES,
    REQUIRED_GOVERN_KEYS,
)


def _rejects(decision, code, request=None):
    authorized, checks, rejection = verify(decision, request)
    assert authorized is None
    assert rejection is not None, "expected a rejection"
    assert rejection["code"] == code, rejection
    assert rejection["reason"]
    assert checks[-1]["result"] == CHECK_FAIL
    assert all(check["result"] == CHECK_PASS for check in checks[:-1])
    return rejection


# --- the authorizing path -------------------------------------------------


def test_authorized_decision_passes_every_rung():
    authorized, checks, rejection = verify(authorized_hold_decision())

    assert rejection is None
    assert [check["check"] for check in checks] == list(CHECK_ORDER)
    assert all(check["result"] == CHECK_PASS for check in checks)
    assert authorized == {
        "candidate_id": "defer_to_agent-1",
        "strategy": "DEFER_TO_AGENT",
        "permission_basis": "all_checks_passed",
        "actions": ["HOLD_RELATED_ACTIONS"],
    }


def test_authorization_is_copied_from_govern_not_derived():
    decision = authorized_release_decision()
    authorized, _, _ = verify(decision)

    assert authorized["candidate_id"] == decision["selected_candidate"]["candidate_id"]
    assert authorized["strategy"] == decision["selected_candidate"]["strategy"]
    assert authorized["actions"] == decision["authorized_actions"]
    # ...and it is a copy, so editing the result cannot edit the decision.
    authorized["actions"].append("RELEASE_PAYMENT")
    assert decision["authorized_actions"] == ["RELEASE_PAYMENT", "CLOSE_CASE"]


# --- rung 1: the document exists and is shaped like a GOVERN decision -----


@pytest.mark.parametrize("empty", [None, {}])
def test_missing_authorization_is_rejected(empty):
    _rejects(empty, REJECT_AUTHORIZATION_MISSING)


@pytest.mark.parametrize("bad", ["PROCEED", 42, [], True, {"execution_authorized": True}])
def test_malformed_govern_output_is_rejected(bad):
    _rejects(bad, REJECT_GOVERN_OUTPUT_MALFORMED)


@pytest.mark.parametrize("key", sorted(REQUIRED_GOVERN_KEYS))
def test_every_required_govern_key_is_required(key):
    decision = tampered(authorized_hold_decision(), lambda d: d.pop(key))
    rejection = _rejects(decision, REJECT_GOVERN_OUTPUT_MALFORMED)
    assert key in rejection["detail"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(execution_authorized="true"),
        lambda d: d.update(execution_authorized=1),
        lambda d: d.update(outcome=""),
        lambda d: d.update(case="case-Q"),
        lambda d: d.update(rationale="all good"),
        lambda d: d.update(authorized_actions="HOLD_RELATED_ACTIONS"),
        lambda d: d.update(authorized_actions=[""]),
        lambda d: d.update(authorized_actions=[None]),
        lambda d: d.update(permission_evaluation=[]),
        lambda d: d["permission_evaluation"].pop("permitted_candidate_ids"),
        lambda d: d["permission_evaluation"].update(candidates=[]),
        lambda d: d["permission_evaluation"].update(permitted_candidate_ids="defer_to_agent-1"),
    ],
    ids=[
        "authorized_as_string",
        "authorized_as_int",
        "empty_outcome",
        "case_not_mapping",
        "rationale_not_mapping",
        "actions_not_list",
        "empty_action_name",
        "null_action_name",
        "permission_evaluation_not_mapping",
        "permitted_ids_missing",
        "no_candidates",
        "permitted_ids_not_list",
    ],
)
def test_structurally_broken_documents_are_rejected_not_repaired(mutate):
    decision = tampered(authorized_hold_decision(), mutate)
    _rejects(decision, REJECT_GOVERN_OUTPUT_MALFORMED)


def test_non_serializable_document_is_rejected():
    decision = tampered(authorized_hold_decision(), lambda d: d.update(opaque=object()))
    rejection = _rejects(decision, REJECT_GOVERN_OUTPUT_MALFORMED)
    assert "JSON-serializable" in rejection["detail"]


# --- rung 2: GOVERN actually said yes -------------------------------------


def test_execution_authorized_false_is_rejected():
    _rejects(escalated_decision(), REJECT_EXECUTION_NOT_AUTHORIZED)
    _rejects(ambiguous_decision(), REJECT_EXECUTION_NOT_AUTHORIZED)


@pytest.mark.parametrize("value", [False, None, 0])
def test_flipping_authorization_off_stops_execution(value):
    decision = tampered(authorized_hold_decision(), lambda d: d.update(execution_authorized=value))
    # False is a plain refusal; the non-boolean impostors never even reach
    # rung 2, because a GOVERN document does not carry them.
    expected = (
        REJECT_EXECUTION_NOT_AUTHORIZED if value is False else REJECT_GOVERN_OUTPUT_MALFORMED
    )
    _rejects(decision, expected)


# --- rung 3: the document agrees with itself ------------------------------


@pytest.mark.parametrize("outcome", ["HOLD", "ESCALATE", "AMBIGUOUS", "APPROVED"])
def test_authorization_that_contradicts_the_outcome_is_rejected(outcome):
    # execution_authorized True beside a non-PROCEED outcome did not come from
    # GOVERN, which derives the one from the other in a single place.
    decision = tampered(authorized_hold_decision(), lambda d: d.update(outcome=outcome))
    _rejects(decision, REJECT_AUTHORIZATION_INCONSISTENT)


# --- rung 4: there is a candidate -----------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(selected_candidate=None),
        lambda d: d.update(selected_candidate="defer_to_agent-1"),
        lambda d: d["selected_candidate"].pop("candidate_id"),
        lambda d: d["selected_candidate"].pop("resulting_actions"),
        lambda d: d["selected_candidate"].pop("strategy"),
        lambda d: d["selected_candidate"].pop("permission_basis"),
        lambda d: d["selected_candidate"].update(candidate_id=""),
        lambda d: d["selected_candidate"].update(candidate_id=None),
        lambda d: d["selected_candidate"].update(resulting_actions="HOLD_RELATED_ACTIONS"),
    ],
    ids=[
        "null_candidate",
        "candidate_not_mapping",
        "no_candidate_id",
        "no_resulting_actions",
        "no_strategy",
        "no_permission_basis",
        "empty_candidate_id",
        "null_candidate_id",
        "actions_not_list",
    ],
)
def test_missing_authorized_candidate_is_rejected(mutate):
    _rejects(tampered(authorized_hold_decision(), mutate), REJECT_AUTHORIZED_CANDIDATE_MISSING)


# --- rung 5: GOVERN still permits that candidate --------------------------


def test_candidate_absent_from_the_permitted_set_is_rejected():
    decision = tampered(
        authorized_hold_decision(),
        lambda d: d["permission_evaluation"].update(permitted_candidate_ids=[]),
    )
    _rejects(decision, REJECT_CANDIDATE_NOT_PERMITTED)


def test_candidate_blocked_by_a_hard_constraint_is_rejected():
    # The safety case: every authorization field still says PROCEED, but the
    # candidate's own permission record says a hard constraint blocked it.
    # EXECUTOR believes the block.
    def block(decision):
        record = permission_record(decision, decision["selected_candidate"]["candidate_id"])
        record["permitted"] = False
        record["blocking_reasons"] = ["HC_PAYOUT_DURING_CHARGEBACK"]

    rejection = _rejects(tampered(authorized_hold_decision(), block), REJECT_CANDIDATE_NOT_PERMITTED)
    assert "HC_PAYOUT_DURING_CHARGEBACK" in rejection["detail"]


def test_candidate_with_blocking_reasons_is_rejected_even_when_marked_permitted():
    # permitted True beside a non-empty blocking list is a contradiction, and
    # EXECUTOR resolves contradictions by refusing.
    def contradict(decision):
        record = permission_record(decision, decision["selected_candidate"]["candidate_id"])
        record["blocking_reasons"] = ["HC_CONFIDENCE_FLOOR"]

    _rejects(tampered(authorized_hold_decision(), contradict), REJECT_CANDIDATE_NOT_PERMITTED)


def test_candidate_with_no_permission_record_is_rejected():
    def unrecord(decision):
        candidate_id = decision["selected_candidate"]["candidate_id"]
        decision["permission_evaluation"]["candidates"] = [
            record
            for record in decision["permission_evaluation"]["candidates"]
            if record["candidate_id"] != candidate_id
        ]

    _rejects(tampered(authorized_hold_decision(), unrecord), REJECT_CANDIDATE_NOT_PERMITTED)


def test_duplicate_permission_records_are_rejected():
    # Two rows for one id make the document ambiguous about which applies,
    # and EXECUTOR does not choose between them.
    def duplicate(decision):
        records = decision["permission_evaluation"]["candidates"]
        records.append(dict(records[0], permitted=False, blocking_reasons=["HC_CONFIDENCE_FLOOR"]))

    _rejects(tampered(authorized_hold_decision(), duplicate), REJECT_CANDIDATE_NOT_PERMITTED)


@pytest.mark.parametrize(
    "key", ["candidate_id", "resulting_actions", "permitted", "blocking_reasons"]
)
def test_incomplete_permission_record_is_rejected(key):
    def strip(decision):
        record = permission_record(decision, decision["selected_candidate"]["candidate_id"])
        record.pop(key)

    _rejects(tampered(authorized_hold_decision(), strip), REJECT_CANDIDATE_NOT_PERMITTED)


# --- rung 6: the actions belong to that candidate -------------------------


def test_candidate_action_mismatch_is_rejected():
    # One candidate's identity attached to another candidate's actions.
    decision = tampered(
        authorized_hold_decision(), lambda d: d.update(authorized_actions=["RELEASE_PAYMENT"])
    )
    rejection = _rejects(decision, REJECT_AUTHORIZATION_INCONSISTENT)
    assert "RELEASE_PAYMENT" in rejection["detail"]


def test_actions_must_match_the_permission_record_too():
    # Editing both authorization fields is not enough: the candidate's own
    # permission record is the third witness and must agree as well.
    def widen(decision):
        decision["authorized_actions"] = ["RELEASE_PAYMENT"]
        decision["selected_candidate"]["resulting_actions"] = ["RELEASE_PAYMENT"]

    _rejects(tampered(authorized_hold_decision(), widen), REJECT_AUTHORIZATION_INCONSISTENT)


def test_reordered_actions_are_rejected():
    # Order is part of the authorization: releasing a payment and then closing
    # the case is not the same instruction as the reverse.
    decision = tampered(
        authorized_release_decision(),
        lambda d: d.update(authorized_actions=["CLOSE_CASE", "RELEASE_PAYMENT"]),
    )
    _rejects(decision, REJECT_AUTHORIZATION_INCONSISTENT)


# --- rung 7: there is something to do -------------------------------------


def test_authorization_with_no_action_is_rejected():
    def empty(decision):
        candidate_id = decision["selected_candidate"]["candidate_id"]
        decision["authorized_actions"] = []
        decision["selected_candidate"]["resulting_actions"] = []
        permission_record(decision, candidate_id)["resulting_actions"] = []

    _rejects(tampered(authorized_hold_decision(), empty), REJECT_AUTHORIZED_ACTION_MISSING)


# --- rung 8: the request matches the authorization ------------------------


def test_matching_request_is_accepted():
    decision = authorized_release_decision()
    authorized, _, rejection = verify(
        decision,
        {"candidate_id": "no_conflict_proceed-1", "actions": ["RELEASE_PAYMENT", "CLOSE_CASE"]},
    )
    assert rejection is None
    assert authorized["candidate_id"] == "no_conflict_proceed-1"


def test_partial_request_is_accepted():
    authorized, _, rejection = verify(
        authorized_hold_decision(), {"candidate_id": "defer_to_agent-1"}
    )
    assert rejection is None and authorized is not None


def test_request_naming_a_different_candidate_is_rejected():
    decision = authorized_hold_decision()
    rival = rival_candidate_id(decision)
    rejection = _rejects(
        decision, REJECT_REQUESTED_CANDIDATE_MISMATCH, request={"candidate_id": rival}
    )
    assert rival in rejection["detail"]
    assert decision["selected_candidate"]["candidate_id"] in rejection["detail"]


def test_request_naming_different_actions_is_rejected():
    _rejects(
        authorized_hold_decision(),
        REJECT_REQUESTED_ACTION_MISMATCH,
        request={"actions": ["RELEASE_PAYMENT"]},
    )


def test_request_naming_a_superset_of_actions_is_rejected():
    _rejects(
        authorized_hold_decision(),
        REJECT_REQUESTED_ACTION_MISMATCH,
        request={"actions": ["HOLD_RELATED_ACTIONS", "RELEASE_PAYMENT"]},
    )


@pytest.mark.parametrize(
    "request_payload",
    [
        {},
        "defer_to_agent-1",
        ["defer_to_agent-1"],
        {"candidate_id": "defer_to_agent-1", "force": True},
        {"execution_authorized": True},
        {"actions": "HOLD_RELATED_ACTIONS"},
        {"actions": [""]},
    ],
    ids=[
        "empty",
        "not_a_mapping",
        "a_list",
        "unknown_field",
        "tries_to_authorize_itself",
        "actions_not_a_list",
        "empty_action_name",
    ],
)
def test_malformed_request_is_rejected(request_payload):
    _rejects(authorized_hold_decision(), REJECT_REQUEST_MALFORMED, request=request_payload)


# --- rung 9: the action is one EXECUTOR can perform -----------------------


def test_unknown_action_is_rejected():
    def rename(decision):
        candidate_id = decision["selected_candidate"]["candidate_id"]
        decision["authorized_actions"] = ["WIRE_MONEY_ANYWHERE"]
        decision["selected_candidate"]["resulting_actions"] = ["WIRE_MONEY_ANYWHERE"]
        permission_record(decision, candidate_id)["resulting_actions"] = ["WIRE_MONEY_ANYWHERE"]

    rejection = _rejects(tampered(authorized_hold_decision(), rename), REJECT_UNSUPPORTED_ACTION)
    assert "WIRE_MONEY_ANYWHERE" in rejection["detail"]


def test_one_unknown_action_refuses_the_whole_authorization():
    # No partial execution of the actions EXECUTOR happened to recognise.
    def append_unknown(decision):
        candidate_id = decision["selected_candidate"]["candidate_id"]
        actions = ["RELEASE_PAYMENT", "CLOSE_CASE", "WIRE_MONEY_ANYWHERE"]
        decision["authorized_actions"] = actions
        decision["selected_candidate"]["resulting_actions"] = list(actions)
        permission_record(decision, candidate_id)["resulting_actions"] = list(actions)

    _rejects(tampered(authorized_release_decision(), append_unknown), REJECT_UNSUPPORTED_ACTION)


# --- ladder shape ----------------------------------------------------------


def test_ladder_stops_at_the_first_failure():
    # Rung 2 fails, so rungs 3-9 never run: the receipt shows exactly how far
    # EXECUTOR got before it refused.
    _, checks, _ = verify(escalated_decision())
    assert [check["check"] for check in checks] == list(CHECK_ORDER[:2])


def test_every_rejection_code_is_in_the_declared_vocabulary():
    for decision, request in [
        (None, None),
        ("garbage", None),
        (escalated_decision(), None),
        (authorized_hold_decision(), {"candidate_id": "other"}),
    ]:
        _, _, rejection = verify(decision, request)
        assert rejection["code"] in REJECTION_CODES


def test_verify_never_mutates_the_decision():
    import copy

    decision = authorized_release_decision()
    before = copy.deepcopy(decision)
    verify(decision, {"candidate_id": "no_conflict_proceed-1"})
    verify(decision, {"candidate_id": "something-else"})
    assert decision == before
