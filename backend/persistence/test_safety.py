"""
Structural safety: persistence is a passive sink. These tests prove
properties of the code itself, mirroring weigh/test_open_track_safety.py and
govern/test_govern_safety.py's own stance -- a substring search on source text
would false-positive on this file's own docstrings and on the mapper
docstrings that legitimately name GOVERN/WEIGH concepts in prose, so the
import graph (ast) is checked instead where that matters, plus a
byte-identity check that a govern_output surviving a full store round trip
comes back with its decision unchanged.
"""

import ast
import copy
from pathlib import Path

import pytest

from persistence.conftest import FakeSupabaseClient, full_run_ambiguous, full_run_payout_vs_dispute
from persistence.errors import PersistenceError
from persistence.store import PersistenceStore, candidate_row_id_map

PERSISTENCE_PACKAGE_DIR = Path(__file__).resolve().parent

# Persistence never decides anything, so it has no legitimate reason to
# import the layers that do. It also never talks to a decision layer's
# internals directly -- only to the plain dicts those layers already
# returned.
FORBIDDEN_IMPORT_MODULES = {
    "resolve",
    "weigh",
    "govern",
    "executor",
    "conflict_matrix",
    "anthropic",
    "requests",
    "httpx",
}


def _non_test_source_files():
    # conftest.py is test infrastructure: it deliberately imports the real
    # pipeline to build fixtures, exactly like govern/conftest.py and
    # executor/conftest.py do for their own packages.
    return [
        path
        for path in PERSISTENCE_PACKAGE_DIR.glob("*.py")
        if not path.name.startswith("test_") and path.name != "conftest.py"
    ]


def _imported_module_roots(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_persistence_source_never_imports_a_decision_layer():
    assert _non_test_source_files(), "no persistence source files found"
    for path in _non_test_source_files():
        hit = _imported_module_roots(path) & FORBIDDEN_IMPORT_MODULES
        assert not hit, f"{path.name} imports forbidden module(s): {hit}"


def test_persistence_source_defines_no_scoring_or_decision_functions():
    # A grep-shaped structural check: none of persistence's own source files
    # define a function that computes a score, a rank, or a decision --
    # every such value persistence handles was already computed upstream and
    # only needs to be shaped into a row (e.g. map_candidate_scores maps an
    # already-computed score, it does not compute one -- "scores" as a noun
    # naming the table is fine; "compute"/"calculate" acting on one is not).
    forbidden_name_fragments = (
        "compute_score",
        "calculate_score",
        "rank_candidates",
        "decide",
        "authorize_",
        "_authorize",
        "select_candidate",
        "choose_candidate",
        "resolve_conflict",
        "execute_action",
    )
    for path in _non_test_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lowered = node.name.lower()
                hit = [frag for frag in forbidden_name_fragments if frag in lowered]
                assert not hit, f"{path.name} defines {node.name}, which reads as a decision function"


def test_no_dynamic_execution_in_persistence_source():
    # No eval/exec/compile/__import__ anywhere. getattr is allowed only with a
    # literal string attribute name (store.py uses getattr(response, "data",
    # None) to read the Supabase response object defensively) -- a getattr
    # whose attribute name is itself data would be the dynamic-dispatch
    # pattern govern/test_govern_safety.py also forbids.
    for path in _non_test_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            name = node.func.id
            assert name not in {"eval", "exec", "compile", "__import__"}, f"{path.name}: {name}"
            if name == "getattr":
                attr_arg = node.args[1] if len(node.args) > 1 else None
                assert isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str), (
                    f"{path.name}: getattr with a non-literal attribute name"
                )


# --- behavioural proof: a decision survives a full store round trip --------


def test_persisted_govern_decision_is_never_altered_by_persistence():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_payout_vs_dispute()
    before = copy.deepcopy(run["govern_output"])

    candidate_rows = store.record_candidates("case-run-1", run["resolve_output"]["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    stored = store.record_govern_result("case-run-1", run["govern_output"], row_ids)

    # persistence never mutates the document it was handed...
    assert run["govern_output"] == before
    # ...and the stored row's decision fields are exactly what GOVERN decided.
    assert stored["outcome"] == run["govern_output"]["outcome"]
    assert stored["execution_authorized"] == run["govern_output"]["execution_authorized"]
    assert stored["decision_id"] == run["govern_output"]["decision_id"]
    assert stored["raw_output"] == before


def test_persisted_receipt_status_is_never_flipped():
    client = FakeSupabaseClient()
    store = PersistenceStore(client)
    run = full_run_ambiguous()  # AMBIGUOUS -> execution_authorized False -> REJECTED receipt
    assert run["receipt"]["status"] == "REJECTED"

    row = store.record_execution_receipt("case-run-1", "govern-row-1", run["receipt"])

    assert row["status"] == "REJECTED"
    assert row["executed_actions"] == []


def test_persistence_cannot_select_a_candidate_of_its_own():
    # There is no store method that takes a list of candidates and returns
    # one -- every candidate-linking method requires the caller (which
    # already ran GOVERN) to supply the winning id.
    store = PersistenceStore(FakeSupabaseClient())
    public_methods = [name for name in dir(store) if not name.startswith("_") and callable(getattr(store, name))]
    forbidden_fragments = ("choose", "pick", "select_candidate", "select_best")
    for name in public_methods:
        lowered = name.lower()
        assert not any(fragment in lowered for fragment in forbidden_fragments), name


def test_map_candidate_scores_refuses_to_invent_a_missing_link_rather_than_guess():
    # PersistenceError, not a silently-guessed row id: persistence fails
    # closed on a missing link rather than picking one.
    from persistence import mappers

    run = full_run_payout_vs_dispute()
    incomplete = {run["weigh_output"]["candidates"][0]["candidate_id"]: "only-one-row"}
    with pytest.raises(PersistenceError):
        mappers.map_candidate_scores(run["weigh_output"], incomplete)
