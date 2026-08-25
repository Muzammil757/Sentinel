"""
Structural safety.

These tests prove properties of the EXECUTOR package itself rather than of one
case: it is structurally incapable of calling a model, opening a socket,
touching a database, reading a clock, or loading policy; it cannot reach back
into any deciding layer; it cannot grant itself authority; and the candidate
GOVERN authorized is the candidate it executes, whatever else the document
says is better.

The candidate-integrity section is the safety invariant this layer exists for:

    If GOVERN authorizes candidate A, EXECUTOR executes candidate A.
"""

import ast
import copy
from pathlib import Path

import pytest

from executor import execute
from executor.authorization import verify
from executor.conftest import (
    ambiguous_decision,
    authorized_hold_decision,
    authorized_release_decision,
    escalated_decision,
    permission_record,
    rival_candidate_id,
    tampered,
    unauthorized_decisions,
)
from executor.schema import (
    AUTHORIZING_OUTCOME,
    REJECT_AUTHORIZATION_INCONSISTENT,
    REJECT_CANDIDATE_NOT_PERMITTED,
    REJECT_EXECUTION_NOT_AUTHORIZED,
    REJECT_REQUESTED_CANDIDATE_MISMATCH,
    STATUS_EXECUTED,
    STATUS_REJECTED,
)
from govern.schema import OUTCOME_PROCEED

EXECUTOR_PACKAGE_DIR = Path(__file__).resolve().parent

# Checked via the import graph (ast), not substring search on file text -- a
# substring check would false-positive on this package's docstrings, which
# legitimately explain the model/network/DB/clock boundary in prose.
FORBIDDEN_IMPORT_MODULES = {
    "anthropic",
    "requests",
    "urllib",
    "httpx",
    "sqlite3",
    "sqlalchemy",
    "socket",
    "subprocess",
    "random",
    "time",
    "uuid",
    "datetime",
    "os",
    "pathlib",
    "shutil",
    "fastapi",
    "database",
}

# EXECUTOR consumes a GOVERN *document*, not a GOVERN *module*. Importing any
# deciding layer would give it a way to produce an authorization instead of
# merely checking one, so the whole upstream half of the pipeline is off
# limits -- policy included, since re-reading policy is how a downstream layer
# starts quietly re-deciding.
FORBIDDEN_LAYER_MODULES = {
    "govern",
    "weigh",
    "resolve",
    "policy",
    "conflict_matrix",
    "mock_agents",
}

# Numbers EXECUTOR must never touch. WEIGH owns comparison, GOVERN owns
# thresholds; EXECUTOR reads neither, so none of these names may appear in its
# source outside a docstring.
FORBIDDEN_SCORE_TOKENS = {
    "total_score",
    "score_rank",
    "objective_impacts",
    "objective_contributions",
    "weights_used",
    "score_band",
    "proceed_min_score",
    "hold_max_score",
    "near_tie_threshold",
    "ranking",
}


def _source_files():
    # conftest.py is test infrastructure, not EXECUTOR source: it deliberately
    # imports GOVERN to build fixtures.
    return [
        path
        for path in EXECUTOR_PACKAGE_DIR.glob("*.py")
        if not path.name.startswith("test_") and path.name != "conftest.py"
    ]


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_module_roots(path):
    roots = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _docstring_node_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _code_tokens(path):
    """Every identifier and non-docstring string literal in one source file."""

    tree = _tree(path)
    docstrings = _docstring_node_ids(tree)
    tokens = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                tokens.add(node.value)
    return tokens


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


# --- the package cannot do the things it promises not to do ---------------


def test_no_forbidden_imports_in_executor_source():
    # No model SDK, no HTTP client, no database, no filesystem, no clock, no
    # randomness -- verified against the actual import graph, so EXECUTOR is
    # structurally incapable of any of them rather than merely documented as
    # avoiding them.
    assert _source_files(), "no EXECUTOR source files found"
    for path in _source_files():
        hit = _imported_module_roots(path) & FORBIDDEN_IMPORT_MODULES
        assert not hit, f"{path.name} imports forbidden module(s): {hit}"


def test_executor_imports_no_deciding_layer():
    for path in _source_files():
        hit = _imported_module_roots(path) & FORBIDDEN_LAYER_MODULES
        assert not hit, f"{path.name} imports deciding layer(s): {hit}"


def test_executor_never_loads_policy():
    # EXECUTOR has no policy of its own and reads nobody else's. Everything
    # policy decided arrived already decided, inside GOVERN's document.
    for path in _source_files():
        assert "policy" not in _imported_module_roots(path), path.name
        assert "load_policy" not in _code_tokens(path), path.name


def test_executor_does_not_invoke_claude():
    # No SDK import above, and no advisory vocabulary anywhere in the source.
    for path in _source_files():
        tokens = _code_tokens(path)
        assert not tokens & {"advisor", "Advisor", "advisory", "consult", "explain"}, path.name


def test_executor_calculates_no_weigh_score():
    for path in _source_files():
        hit = _code_tokens(path) & FORBIDDEN_SCORE_TOKENS
        assert not hit, f"{path.name} references scoring machinery: {hit}"


def test_no_file_or_dynamic_execution_in_executor_source():
    # No open(), and no eval/exec/getattr dispatch that could turn a string
    # from a document into a code path.
    for path in _source_files():
        called = {
            node.func.id
            for node in ast.walk(_tree(path))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not called & {"open", "eval", "exec", "compile", "getattr", "__import__"}, path.name


def test_receipt_carries_no_scoring_or_ranking_fields():
    receipt = execute(authorized_hold_decision())
    assert set(_walk_keys(receipt)) & FORBIDDEN_SCORE_TOKENS == set()
    assert "claude" not in set(_walk_keys(receipt))


def test_executor_reads_no_entity_risk_magnitude():
    receipt = execute(authorized_release_decision())
    forbidden = {
        "risk_score",
        "fraud_score",
        "rto_score",
        "churn_risk",
        "disputed_amount",
        "days_overdue",
        "amount",
    }
    assert set(_walk_keys(receipt)) & forbidden == set()


def test_authorizing_outcome_matches_governs_own_vocabulary():
    # EXECUTOR duplicates the token rather than importing GOVERN. This is the
    # test that keeps the duplicate honest.
    assert AUTHORIZING_OUTCOME == OUTCOME_PROCEED


# --- EXECUTOR cannot grant authority --------------------------------------


@pytest.mark.parametrize("decision", unauthorized_decisions(), ids=lambda d: d["outcome"])
def test_executor_cannot_authorize_what_govern_did_not(decision):
    receipt = execute(decision)

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []
    assert receipt["authorization"]["execution_authorized"] is False


def test_a_permitted_candidate_is_not_an_authorized_one():
    # An AMBIGUOUS case leaves two candidates permitted and one under review,
    # and authorizes neither. Permission is not authority, and EXECUTOR does
    # not treat it as any.
    decision = ambiguous_decision()
    assert len(decision["permission_evaluation"]["permitted_candidate_ids"]) > 1
    assert decision["candidate_under_review"] is not None
    assert decision["selected_candidate"] is None

    receipt = execute(decision)
    assert receipt["status"] == STATUS_REJECTED
    assert receipt["executed_actions"] == []


def test_executor_cannot_promote_the_candidate_under_review():
    # candidate_under_review is "the option a human is being asked about", not
    # a decision. EXECUTOR must not mistake it for one.
    decision = ambiguous_decision()
    assert decision["candidate_under_review"] is not None
    assert decision["selected_candidate"] is None

    receipt = execute(decision, {"candidate_id": decision["candidate_under_review"]})
    assert receipt["status"] == STATUS_REJECTED
    assert receipt["rejection"]["code"] == REJECT_EXECUTION_NOT_AUTHORIZED


def test_a_request_cannot_manufacture_authorization():
    # The request is an assertion to be checked, never a grant. No shape of it
    # makes an unauthorized decision executable.
    decision = escalated_decision()
    for request in [
        None,
        {"candidate_id": "no_conflict_proceed-1"},
        {"actions": ["RELEASE_PAYMENT", "CLOSE_CASE"]},
        {"candidate_id": "no_conflict_proceed-1", "actions": ["RELEASE_PAYMENT"]},
    ]:
        receipt = execute(decision, request)
        assert receipt["status"] == STATUS_REJECTED
        assert receipt["executed_actions"] == []


def test_receipt_authorization_mirrors_govern_and_never_overstates_it():
    for decision in [authorized_hold_decision(), *unauthorized_decisions()]:
        receipt = execute(decision)
        assert (
            receipt["authorization"]["execution_authorized"]
            is decision["execution_authorized"]
        )
        assert (receipt["status"] == STATUS_EXECUTED) is decision["execution_authorized"]


def test_executor_cannot_bypass_govern():
    # There is exactly one way into execution, and it is verify(). Rejections
    # from it are exhaustive over execute()'s behaviour: whenever verify()
    # refuses, execute() performs nothing.
    for decision in [None, "garbage", escalated_decision(), ambiguous_decision()]:
        _, _, rejection = verify(decision)
        assert rejection is not None
        assert execute(decision)["executed_actions"] == []


# --- candidate integrity: A is authorized, so A is executed ---------------


def test_a_higher_scoring_rival_cannot_replace_the_authorized_candidate():
    # The regression test for the safety invariant. A rival candidate is added
    # with a better score, a more attractive action, a different agent and a
    # clean permission record, and placed first in the evaluated list.
    # EXECUTOR must not so much as look at it.
    def plant_rival(decision):
        records = decision["permission_evaluation"]["candidates"]
        rival = copy.deepcopy(records[0])
        rival.update(
            candidate_id="rival-999",
            strategy="DEFER_TO_AGENT",
            resulting_actions=["RELEASE_PAYMENT"],
            total_score=0.99,
            score_rank=0,
            permitted=True,
            blocking_reasons=[],
            permission_basis="all_checks_passed",
        )
        records.insert(0, rival)
        decision["permission_evaluation"]["permitted_candidate_ids"].insert(0, "rival-999")

    decision = tampered(authorized_hold_decision(), plant_rival)
    receipt = execute(decision)

    assert receipt["status"] == STATUS_EXECUTED
    assert receipt["authorization"]["authorized_candidate_id"] == "defer_to_agent-1"
    assert [entry["action"] for entry in receipt["executed_actions"]] == ["HOLD_RELATED_ACTIONS"]
    assert "RELEASE_PAYMENT" not in {
        entry["action"] for entry in receipt["executed_actions"]
    }


def test_a_request_naming_the_higher_scoring_rival_is_refused_not_obeyed():
    def plant_rival(decision):
        records = decision["permission_evaluation"]["candidates"]
        rival = copy.deepcopy(records[0])
        rival.update(
            candidate_id="rival-999",
            resulting_actions=["RELEASE_PAYMENT"],
            total_score=0.99,
            permitted=True,
            blocking_reasons=[],
        )
        records.insert(0, rival)
        decision["permission_evaluation"]["permitted_candidate_ids"].insert(0, "rival-999")

    decision = tampered(authorized_hold_decision(), plant_rival)
    receipt = execute(decision, {"candidate_id": "rival-999"})

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["rejection"]["code"] == REJECT_REQUESTED_CANDIDATE_MISMATCH
    assert receipt["executed_actions"] == []


def test_reordering_the_evaluated_candidates_changes_nothing():
    # EXECUTOR reads the authorization, not the order of the list. Reversing
    # the evaluated candidates leaves the executed actions untouched.
    baseline = execute(authorized_hold_decision())
    reordered = execute(
        tampered(
            authorized_hold_decision(),
            lambda d: d["permission_evaluation"]["candidates"].reverse(),
        )
    )
    assert reordered["executed_actions"] == baseline["executed_actions"]
    assert (
        reordered["authorization"]["authorized_candidate_id"]
        == baseline["authorization"]["authorized_candidate_id"]
    )


def test_raising_a_rivals_score_changes_nothing():
    def outscore(decision):
        rival = permission_record(decision, rival_candidate_id(decision))
        rival["total_score"] = 0.99
        rival["score_rank"] = 1

    baseline = execute(authorized_hold_decision())
    outscored = execute(tampered(authorized_hold_decision(), outscore))

    assert outscored["executed_actions"] == baseline["executed_actions"]
    assert (
        outscored["authorization"]["authorized_candidate_id"]
        == baseline["authorization"]["authorized_candidate_id"]
    )


def test_candidate_action_mismatch_is_rejected():
    # A document that names candidate A but carries candidate B's actions is
    # refused rather than resolved in either direction.
    def swap_actions(decision):
        rival = permission_record(decision, rival_candidate_id(decision))
        rival["resulting_actions"] = ["RELEASE_PAYMENT"]
        decision["authorized_actions"] = ["RELEASE_PAYMENT"]

    receipt = execute(tampered(authorized_hold_decision(), swap_actions))
    assert receipt["status"] == STATUS_REJECTED
    assert receipt["rejection"]["code"] == REJECT_AUTHORIZATION_INCONSISTENT
    assert receipt["executed_actions"] == []


def test_swapping_the_authorized_candidate_id_alone_is_rejected():
    # Renaming the winner without moving its evidence does not make the rival
    # executable; it makes the document inconsistent, and EXECUTOR refuses.
    decision = authorized_hold_decision()
    rival = rival_candidate_id(decision)
    receipt = execute(
        tampered(decision, lambda d: d["selected_candidate"].update(candidate_id=rival))
    )

    assert receipt["status"] == STATUS_REJECTED
    assert receipt["rejection"]["code"] in {
        REJECT_CANDIDATE_NOT_PERMITTED,
        REJECT_AUTHORIZATION_INCONSISTENT,
    }
    assert receipt["executed_actions"] == []


# --- no side effects, upstream or outward ---------------------------------


def test_executor_modifies_no_upstream_data():
    # The decision EXECUTOR was handed -- and the RESOLVE/WEIGH facts GOVERN
    # copied into it -- come back untouched.
    decision = authorized_release_decision()
    before = copy.deepcopy(decision)

    receipt = execute(decision)
    receipt["authorization"]["authorized_actions"].append("HOLD_ORDER")
    receipt["executed_actions"].clear()

    assert decision == before


def test_executor_writes_no_file_and_leaves_no_artifact():
    # There is no filesystem import and no open() call (asserted above); this
    # confirms the observable half: running the layer creates nothing on disk.
    before = sorted(path.name for path in EXECUTOR_PACKAGE_DIR.iterdir())
    execute(authorized_hold_decision())
    execute(escalated_decision())
    assert sorted(path.name for path in EXECUTOR_PACKAGE_DIR.iterdir()) == before


def test_executor_holds_no_state_between_calls():
    # No module-level accumulator, no memo, no counter: the tenth execution is
    # identical to the first, and an intervening rejection changes nothing.
    first = execute(authorized_hold_decision())
    for _ in range(9):
        execute(escalated_decision())
        execute(None)
        assert execute(authorized_hold_decision()) == first
