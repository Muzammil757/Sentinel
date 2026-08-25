"""
execute() end to end: the receipt it produces, on the authorizing path and on
every refusing one.

The cases here are real GOVERN decisions produced by the real pipeline, so
what these tests pin is the actual contract between the two layers rather
than a hand-written approximation of it.
"""

import copy
import json

import pytest

from executor import execute
from executor.conftest import (
    ambiguous_decision,
    authorized_hold_decision,
    authorized_release_decision,
    escalated_decision,
    permission_record,
    unauthorized_decisions,
    unresolved_decision,
    tampered,
)
from executor.schema import (
    AUTHORIZATION_SOURCE,
    CHECK_ORDER,
    CHECK_PASS,
    EXECUTION_METHOD,
    EXECUTION_MODE,
    EXECUTOR_VERSION,
    RECEIPT_ID_PREFIX,
    REJECT_EXECUTION_NOT_AUTHORIZED,
    REJECT_REQUESTED_CANDIDATE_MISMATCH,
    REJECTION_CODES,
    STATUS_EXECUTED,
    STATUS_REJECTED,
)

def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


RECEIPT_KEYS = {
    "executor_version",
    "execution_method",
    "execution_mode",
    "status",
    "case",
    "authorization",
    "authorization_checks",
    "executed_actions",
    "rejection",
    "receipt_id",
}


# --- the authorized action executes ---------------------------------------


def test_authorized_action_executes():
    decision = authorized_hold_decision()
    receipt = execute(decision)

    assert receipt["status"] == STATUS_EXECUTED
    assert receipt["rejection"] is None
    assert [entry["action"] for entry in receipt["executed_actions"]] == ["HOLD_RELATED_ACTIONS"]
    assert receipt["executed_actions"][0]["effect"] == "RELATED_ACTIONS_HELD"


def test_multiple_authorized_actions_execute_in_the_authorized_order():
    receipt = execute(authorized_release_decision())

    assert receipt["status"] == STATUS_EXECUTED
    assert [entry["action"] for entry in receipt["executed_actions"]] == [
        "RELEASE_PAYMENT",
        "CLOSE_CASE",
    ]
    assert [entry["effect"] for entry in receipt["executed_actions"]] == [
        "PAYOUT_RELEASE_SIMULATED",
        "CASE_CLOSED",
    ]


def test_executed_actions_are_exactly_the_authorized_actions():
    for decision in [authorized_hold_decision(), authorized_release_decision()]:
        receipt = execute(decision)
        performed = [entry["action"] for entry in receipt["executed_actions"]]
        assert performed == decision["authorized_actions"]


def test_matching_request_executes():
    receipt = execute(
        authorized_release_decision(),
        {"candidate_id": "no_conflict_proceed-1", "actions": ["RELEASE_PAYMENT", "CLOSE_CASE"]},
    )
    assert receipt["status"] == STATUS_EXECUTED


# --- the unauthorized action does not -------------------------------------


@pytest.mark.parametrize("decision", unauthorized_decisions(), ids=lambda d: d["outcome"])
def test_unauthorized_outcomes_are_rejected(decision):
    receipt = execute(decision)

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []
    assert receipt["rejection"]["code"] == REJECT_EXECUTION_NOT_AUTHORIZED


def test_execution_authorized_false_is_rejected():
    decision = escalated_decision()
    assert decision["execution_authorized"] is False

    receipt = execute(decision)
    assert receipt["status"] == STATUS_REJECTED
    assert receipt["authorization"]["execution_authorized"] is False


@pytest.mark.parametrize("empty", [None, {}])
def test_missing_authorization_is_rejected(empty):
    receipt = execute(empty)

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []
    assert receipt["case"] is None
    assert receipt["authorization"]["decision_id"] is None


@pytest.mark.parametrize("bad", ["PROCEED", 42, [], {"execution_authorized": True}])
def test_malformed_govern_output_is_rejected(bad):
    receipt = execute(bad)

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []
    assert set(receipt) == RECEIPT_KEYS


def test_rejection_never_executes_anything():
    # Whatever the reason, a refused authorization performs nothing at all --
    # not even the part of it that was fine.
    refusals = [
        (None, None),
        ("garbage", None),
        (escalated_decision(), None),
        (ambiguous_decision(), None),
        (authorized_hold_decision(), {"candidate_id": "hold_both_pending_review-2"}),
        (authorized_release_decision(), {"actions": ["RELEASE_PAYMENT"]}),
    ]
    for decision, request in refusals:
        receipt = execute(decision, request)
        assert receipt["status"] == STATUS_REJECTED
        assert receipt["executed_actions"] == []


# --- the receipt -----------------------------------------------------------


def test_successful_receipt_is_structurally_complete():
    receipt = execute(authorized_hold_decision())

    assert set(receipt) == RECEIPT_KEYS
    assert receipt["executor_version"] == EXECUTOR_VERSION
    assert receipt["execution_method"] == EXECUTION_METHOD
    assert receipt["execution_mode"] == EXECUTION_MODE
    assert receipt["receipt_id"].startswith(RECEIPT_ID_PREFIX)
    assert len(receipt["receipt_id"]) == len(RECEIPT_ID_PREFIX) + 64
    assert [check["check"] for check in receipt["authorization_checks"]] == list(CHECK_ORDER)
    assert all(check["result"] == CHECK_PASS for check in receipt["authorization_checks"])


def test_rejected_receipt_carries_a_structured_failure_reason():
    receipt = execute(escalated_decision())

    assert set(receipt) == RECEIPT_KEYS
    rejection = receipt["rejection"]
    assert set(rejection) == {"code", "reason", "detail"}
    assert rejection["code"] in REJECTION_CODES
    assert isinstance(rejection["reason"], str) and rejection["reason"]
    assert isinstance(rejection["detail"], str) and rejection["detail"]


def test_receipt_links_the_execution_to_the_govern_authorization():
    # "Why did EXECUTOR perform this action?" is answerable from the receipt
    # alone, and every part of the answer points back at GOVERN.
    decision = authorized_hold_decision()
    authorization = execute(decision)["authorization"]

    assert authorization["source"] == AUTHORIZATION_SOURCE
    assert authorization["decision_id"] == decision["decision_id"]
    assert authorization["govern_version"] == decision["govern_version"]
    assert authorization["policy_id"] == decision["policy_id"]
    assert authorization["policy_version"] == decision["policy_version"]
    assert authorization["policy_hash"] == decision["policy_hash"]
    assert authorization["outcome"] == decision["outcome"]
    assert authorization["outcome_basis"] == decision["outcome_basis"]
    assert authorization["execution_authorized"] is True
    assert authorization["authorized_candidate_id"] == decision["selected_candidate"]["candidate_id"]
    assert authorization["authorized_strategy"] == decision["selected_candidate"]["strategy"]
    assert authorization["authorized_actions"] == decision["authorized_actions"]
    assert authorization["permission_basis"] == decision["selected_candidate"]["permission_basis"]


def test_receipt_quotes_governs_rationale_and_writes_none_of_its_own():
    # EXECUTOR has no policy and therefore no policy justification. The only
    # justification on the receipt is GOVERN's, copied verbatim.
    decision = authorized_hold_decision()
    receipt = execute(decision)

    assert (
        receipt["authorization"]["govern_rationale"]
        == decision["rationale"]["outcome_sentence"]
    )


def test_rejected_receipt_still_links_back_to_the_decision_it_refused():
    decision = escalated_decision()
    receipt = execute(decision)

    assert receipt["authorization"]["decision_id"] == decision["decision_id"]
    assert receipt["authorization"]["outcome"] == "ESCALATE"
    # ...but names nothing as authorized, because nothing was.
    assert receipt["authorization"]["authorized_candidate_id"] is None
    assert receipt["authorization"]["authorized_actions"] == []
    assert receipt["authorization"]["permission_basis"] is None


def test_receipt_echoes_the_case_without_aliasing_it():
    decision = authorized_hold_decision()
    receipt = execute(decision)

    assert receipt["case"] == decision["case"]
    receipt["case"]["case_id"] = "tampered"
    assert decision["case"]["case_id"] == "case-Q"


def test_receipt_is_json_serializable():
    for decision in [authorized_hold_decision(), escalated_decision(), unresolved_decision()]:
        json.dumps(execute(decision), sort_keys=True)


def test_receipt_carries_no_timestamp():
    # Like GOVERN, EXECUTOR reads no clock; the orchestrator stamps the
    # receipt when it stores it.
    receipt = execute(authorized_hold_decision())
    forbidden = {"timestamp", "created_at", "executed_at", "updated_at", "now"}
    assert set(_walk_keys(receipt)) & forbidden == set()


# --- determinism -----------------------------------------------------------


def test_repeated_execution_is_byte_identical():
    decision = authorized_release_decision()
    first = execute(decision)
    second = execute(decision)

    assert first == second
    assert first["receipt_id"] == second["receipt_id"]


def test_execution_is_identical_across_independently_built_decisions():
    # Same case, decided twice, executed twice: one receipt id. GOVERN's
    # decision_id is a content fingerprint, and EXECUTOR's receipt_id is one
    # too, so the whole pipeline is reproducible end to end.
    assert execute(authorized_hold_decision()) == execute(authorized_hold_decision())


def test_rejection_is_deterministic_too():
    assert execute(escalated_decision()) == execute(escalated_decision())
    assert execute(None) == execute(None)


def test_different_authorizations_produce_different_receipt_ids():
    hold = execute(authorized_hold_decision())
    release = execute(authorized_release_decision())
    refused = execute(escalated_decision())

    ids = {hold["receipt_id"], release["receipt_id"], refused["receipt_id"]}
    assert len(ids) == 3


def test_receipt_id_covers_the_whole_receipt():
    # Two receipts that differ anywhere differ in their id, so the id is a
    # usable integrity check on the stored receipt.
    decision = authorized_release_decision(50000)
    other = authorized_release_decision(10000)
    assert decision["authorized_actions"] == other["authorized_actions"]
    assert execute(decision)["receipt_id"] != execute(other)["receipt_id"]


def test_request_does_not_change_the_executed_result():
    # Supplying a matching request asserts something; it does not alter
    # anything. The two receipts differ in nothing at all.
    decision = authorized_hold_decision()
    without = execute(decision)
    with_request = execute(decision, {"candidate_id": "defer_to_agent-1"})
    assert without == with_request


# --- the same candidate, whatever else is on the document -----------------


def test_executor_executes_the_candidate_govern_authorized():
    decision = authorized_hold_decision()
    receipt = execute(decision)

    assert receipt["authorization"]["authorized_candidate_id"] == "defer_to_agent-1"
    assert [entry["action"] for entry in receipt["executed_actions"]] == ["HOLD_RELATED_ACTIONS"]


def test_request_for_another_candidate_cannot_redirect_execution():
    receipt = execute(authorized_hold_decision(), {"candidate_id": "hold_both_pending_review-2"})

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["rejection"]["code"] == REJECT_REQUESTED_CANDIDATE_MISMATCH
    assert receipt["executed_actions"] == []


def test_execute_never_mutates_the_decision():
    decision = authorized_release_decision()
    before = copy.deepcopy(decision)

    execute(decision)
    execute(decision, {"candidate_id": "no_conflict_proceed-1"})
    execute(decision, {"candidate_id": "something-else"})

    assert decision == before


def test_a_permitted_but_unselected_candidate_is_never_executed():
    # GOVERN can permit several candidates and authorize one. The others are
    # permitted, not authorized, and EXECUTOR does not touch them.
    decision = authorized_hold_decision()
    permitted = decision["permission_evaluation"]["permitted_candidate_ids"]
    assert len(permitted) > 1

    receipt = execute(decision)
    executed = {entry["action"] for entry in receipt["executed_actions"]}
    for candidate_id in permitted:
        if candidate_id == decision["selected_candidate"]["candidate_id"]:
            continue
        others = set(permission_record(decision, candidate_id)["resulting_actions"])
        assert executed & (others - set(decision["authorized_actions"])) == set()


def test_blocked_candidate_cannot_execute():
    def block(decision):
        record = permission_record(decision, decision["selected_candidate"]["candidate_id"])
        record["permitted"] = False
        record["blocking_reasons"] = ["HC_THIRDWATCH_HIGH_RISK_PAYOUT"]

    receipt = execute(tampered(authorized_release_decision(), block))
    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []
