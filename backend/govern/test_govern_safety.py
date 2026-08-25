"""
Structural safety (design §L.1, §O, §P, §Q, §T).

These tests prove properties of the code itself rather than of one case:
GOVERN is structurally incapable of calling a model, reading a clock, or
loading policy from disk; it fails safely on broken input; it emits every
audit field policy asks of it; and no final decision leaks backwards into
the layers above it.
"""

import ast
import copy
from pathlib import Path

import pytest

from govern import decide
from govern.conftest import (
    build_case,
    no_conflict_release_case,
    payout_vs_dispute_case,
    real_policy,
    rto_vs_retention_case,
)
from govern.errors import GovernInputError, GovernPolicyError
from govern.govern import _validate_policy
from govern.schema import AUDIT_FIELD_PATHS, ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS
from weigh.schema import FORBIDDEN_OUTPUT_KEYS

GOVERN_PACKAGE_DIR = Path(__file__).resolve().parent

# Checked via the import graph (ast), not substring search on file text -- a
# substring check would false-positive on this package's docstrings, which
# legitimately explain the Claude/network/DB/clock boundary in prose.
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
    "database",
}


def _non_test_source_files():
    # conftest.py is test infrastructure, not GOVERN source: it deliberately
    # loads policy from disk to build fixtures.
    return [
        path
        for path in GOVERN_PACKAGE_DIR.glob("*.py")
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


def _imported_names_from(path: Path, module: str) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.name for alias in node.names)
    return names


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


# --- the package cannot do the things it promises not to do ---------------


def test_no_forbidden_imports_in_govern_source():
    # No Anthropic SDK, no HTTP client, no database, no clock, no randomness
    # -- verified against the actual import graph, so GOVERN is structurally
    # incapable of any of them rather than merely documented as avoiding them.
    assert _non_test_source_files(), "no GOVERN source files found"
    for path in _non_test_source_files():
        hit = _imported_module_roots(path) & FORBIDDEN_IMPORT_MODULES
        assert not hit, f"{path.name} imports forbidden module(s): {hit}"


def test_govern_never_loads_policy_itself():
    # GOVERN consumes an already-loaded, already-validated policy dict.
    # compute_policy_hash is fine -- a pure hash over the dict already passed
    # in -- but load_policy reads the YAML from disk and must never appear.
    for path in _non_test_source_files():
        names = _imported_names_from(path, "policy.loader")
        assert "load_policy" not in names, path.name

    assert "compute_policy_hash" in _imported_names_from(
        GOVERN_PACKAGE_DIR / "govern.py", "policy.loader"
    )


def test_no_dynamic_execution_in_govern_source():
    # No eval/exec, and no getattr dispatch that could turn a policy or
    # advisory string into a code path.
    for path in _non_test_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not called & {"eval", "exec", "compile", "getattr", "__import__"}, path.name


def test_no_timestamp_in_output():
    # GOVERN emits no clock reading; the orchestrator stamps the receipt.
    output = decide(*payout_vs_dispute_case())
    forbidden = {"timestamp", "created_at", "decided_at", "updated_at", "now"}
    assert set(_walk_keys(output)) & forbidden == set()


def test_govern_reads_no_continuous_risk_magnitude():
    # The Open Track boundary: GOVERN's inputs are booleans, list membership,
    # a copied score, and policy thresholds. Varying an agent's internal risk
    # magnitude with its declared verdict held fixed must change nothing.
    outputs = []
    for rto_score, churn_risk in [(0.76, 0.76), (0.90, 0.60), (0.99, 0.99)]:
        rto = {
            "agent": "rto",
            "proposed_action": "HOLD_ORDER",
            "confidence": 0.95,
            "rto_score": rto_score,
        }
        retention = {
            "agent": "retention",
            "proposed_action": "WIN_BACK_OFFER",
            "confidence": 0.95,
            "churn_risk": churn_risk,
        }
        weigh_output, agent_actions, case_context, policy = build_case(
            rto, retention, "customer", {"case_id": "case-R"}
        )
        output = decide(weigh_output, agent_actions, case_context, policy)
        outputs.append((output["outcome"], output["execution_authorized"], output["decision_id"]))

    assert len(set(outputs)) == 1, outputs


def test_govern_output_carries_no_entity_risk_field():
    output = decide(*rto_vs_retention_case())
    forbidden = {
        "risk_score",
        "fraud_score",
        "rto_score",
        "rto_risk",
        "churn_risk",
        "chargeback_risk",
        "severity",
        "exposure_amount",
        "disputed_amount",
        "days_overdue",
    }
    assert set(_walk_keys(output)) & forbidden == set()


# --- no final decision leaks backwards ------------------------------------


def test_no_final_decision_leakage_into_earlier_layers():
    # WEIGH must never name a winner. Running GOVERN over its output must not
    # change that, in either direction.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    before = copy.deepcopy(weigh_output)

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert weigh_output == before
    assert set(_walk_keys(weigh_output)) & FORBIDDEN_OUTPUT_KEYS == set()
    govern_only = {
        "execution_authorized",
        "authorized_actions",
        "outcome_basis",
        "decision_id",
        "permission_evaluation",
        "candidate_under_review",
    }
    assert set(_walk_keys(weigh_output)) & govern_only == set()
    # ...and GOVERN's own output does name one, which is the whole point.
    assert output["selected_candidate"] is not None


def test_weigh_output_forbidden_key_is_rejected():
    # A weigh_output carrying a key WEIGH is forbidden to emit did not come
    # from WEIGH unmodified, so GOVERN refuses to enforce against it.
    for key in ("selected", "outcome", "decision", "winner"):
        weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
        tampered = copy.deepcopy(weigh_output)
        tampered["candidates"][0][key] = "tampered"
        with pytest.raises(GovernInputError, match="forbidden"):
            decide(tampered, agent_actions, case_context, policy)


def test_profile_selected_reads_profile_name_not_selected():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["profile_selected"] == weigh_output["profile"]["profile_name"] == "standard"
    assert "selected" not in weigh_output["profile"]


def test_govern_refuses_a_weigh_output_that_claims_enforcement_authority():
    for field, value in [("authority", "enforcing"), ("rechecked_by", "WEIGH")]:
        weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
        tampered = copy.deepcopy(weigh_output)
        tampered["constraint_evaluation"][field] = value
        with pytest.raises(GovernInputError, match=field):
            decide(tampered, agent_actions, case_context, policy)


# --- policy identity -------------------------------------------------------


def test_policy_hash_mismatch_raises():
    # It must be impossible to enforce policy B against numbers produced
    # under policy A.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    tampered["policy_hash"] = "0" * 64

    with pytest.raises(GovernInputError, match="policy identity mismatch"):
        decide(tampered, agent_actions, case_context, policy)


def test_silently_edited_policy_is_caught_by_the_hash():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    edited = copy.deepcopy(policy)
    edited["authority"]["agents"]["payouts"]["max_autonomous_amount"] = 999999999

    with pytest.raises(GovernInputError, match="policy identity mismatch"):
        decide(weigh_output, agent_actions, case_context, edited)


# --- invalid and missing inputs fail safely -------------------------------


@pytest.mark.parametrize("missing", sorted({"case", "profile", "evidence", "candidates", "ranking", "ambiguity", "constraint_evaluation", "policy_hash"}))
def test_missing_weigh_key_raises_input_error(missing):
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    del tampered[missing]

    with pytest.raises(GovernInputError, match="missing required key"):
        decide(tampered, agent_actions, case_context, policy)


@pytest.mark.parametrize("bad", ["not a mapping", 42, None, []])
def test_non_mapping_inputs_raise_input_error(bad):
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()

    with pytest.raises(GovernInputError):
        decide(bad, agent_actions, case_context, policy)
    with pytest.raises(GovernInputError):
        decide(weigh_output, bad, case_context, policy)
    with pytest.raises(GovernInputError):
        decide(weigh_output, agent_actions, bad, policy)


def test_empty_candidate_list_raises_input_error():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    tampered["candidates"] = []

    with pytest.raises(GovernInputError, match="non-empty list"):
        decide(tampered, agent_actions, case_context, policy)


def test_missing_agent_payload_raises_input_error():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    stripped = {k: v for k, v in agent_actions.items() if k != "dispute"}

    with pytest.raises(GovernInputError, match="agent_b"):
        decide(weigh_output, stripped, case_context, policy)


def test_ranking_that_does_not_cover_the_candidates_raises():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    tampered["ranking"] = tampered["ranking"][:1]

    with pytest.raises(GovernInputError, match="ranking"):
        decide(tampered, agent_actions, case_context, policy)


@pytest.mark.parametrize(
    "section", ["escalation", "authority", "hard_constraints", "claude", "fallback", "audit"]
)
def test_missing_policy_section_raises_policy_error(section):
    broken = copy.deepcopy(real_policy())
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    del policy[section]

    with pytest.raises(GovernPolicyError, match=section):
        decide(weigh_output, agent_actions, case_context, policy)


def test_missing_outcome_vocabulary_raises_policy_error():
    broken = copy.deepcopy(real_policy())
    broken["escalation"]["outcomes"] = ["PROCEED", "HOLD"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError, match="AMBIGUOUS"):
        decide(weigh_output, agent_actions, case_context, policy)


def test_unregistered_hard_constraint_raises_policy_error():
    # Defence in depth: WEIGH refuses such a policy first, so this preflight
    # check is asserted directly rather than through a pipeline that can
    # never reach it.
    broken = copy.deepcopy(real_policy())
    broken["hard_constraints"].append(
        {"id": "HC_INVENTED", "description": "d", "enforcement": "block"}
    )

    with pytest.raises(GovernPolicyError, match="HC_INVENTED"):
        _validate_policy(broken)


def test_inverted_thresholds_raise_policy_error():
    broken = copy.deepcopy(real_policy())
    broken["escalation"]["thresholds"]["hold_max_score"] = 0.90

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError, match="hold_max_score"):
        decide(weigh_output, agent_actions, case_context, policy)


def test_a_raised_error_never_leaves_a_partial_output():
    # Every preflight check runs before any candidate work, so a failure is a
    # clean exception rather than a half-built receipt.
    broken = copy.deepcopy(real_policy())
    del broken["escalation"]["thresholds"]["mid_band_outcome"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError):
        decide(weigh_output, agent_actions, case_context, policy)


# --- audit completeness ----------------------------------------------------


def _resolve(output, path):
    node = output
    for step in path:
        assert isinstance(node, dict) and step in node, path
        node = node[step]
    return node


def test_audit_required_fields_are_all_supplied():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    required = policy["audit"]["required_fields"]
    assert len(required) == 15
    for field in required:
        if field in ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS:
            continue
        _resolve(output, AUDIT_FIELD_PATHS[field])

    # The one field GOVERN deliberately does not supply.
    assert ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS == {"timestamp"}
    assert set(required) - ORCHESTRATOR_SUPPLIED_AUDIT_FIELDS == set(AUDIT_FIELD_PATHS)


def test_audit_field_govern_cannot_supply_raises():
    # A future policy edit that adds a required field fails loudly instead of
    # producing a quietly incomplete receipt.
    extended = copy.deepcopy(real_policy())
    extended["audit"]["required_fields"].append("executor_signature")

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=extended)
    with pytest.raises(GovernPolicyError, match="executor_signature"):
        decide(weigh_output, agent_actions, case_context, policy)


def test_audit_fields_are_populated_on_every_outcome():
    cases = [
        payout_vs_dispute_case(),  # PROCEED
        rto_vs_retention_case(),  # AMBIGUOUS
        no_conflict_release_case(60000),  # ESCALATE
    ]
    for inputs in cases:
        output = decide(*inputs)
        assert output["decision_id"].startswith("dec_")
        assert output["policy_hash"]
        assert output["objectives_considered"]
        assert output["weights_used"]
        assert output["permission_evaluation"]["constraints_checked"]
        assert output["permission_evaluation"]["candidates"]
        assert output["rationale"]["outcome_sentence"]
        assert output["claude"]["invoked"] is False
        assert output["claude"]["output_used"] is False


def test_non_serializable_case_context_fails_safely():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    poisoned = dict(case_context, opaque=object())

    with pytest.raises(GovernInputError, match="JSON-serializable"):
        decide(weigh_output, agent_actions, poisoned, policy)


def test_decision_id_is_a_content_fingerprint():
    # Re-running the same case yields the same id -- the desirable property
    # for a receipt, and the reason decision_id is a hash rather than a uuid.
    first = decide(*no_conflict_release_case(10000))
    again = decide(*no_conflict_release_case(10000))

    assert first["decision_id"] == again["decision_id"]
    assert first["decision_id"].startswith("dec_")
    assert len(first["decision_id"]) == len("dec_") + 64


def test_case_context_separates_releases_that_weigh_cannot_tell_apart():
    # A 10 000 and a 50 000 release produce byte-identical weigh_output (the
    # score is 0.3100 at every amount), so case_context is what keeps their
    # receipts distinct.
    low_weigh = no_conflict_release_case(10000)[0]
    high_weigh = no_conflict_release_case(50000)[0]
    assert low_weigh["candidates"][0]["total_score"] == high_weigh["candidates"][0]["total_score"]

    low = decide(*no_conflict_release_case(10000))
    high = decide(*no_conflict_release_case(50000))
    assert low["decision_id"] != high["decision_id"]


def test_decision_id_is_a_fingerprint_not_a_unique_event_id():
    # Stated plainly because it is a property, not an accident: two runs whose
    # case_context and weigh_output are identical share an id even when an
    # input GOVERN does not hash differed. The orchestrator pairs decision_id
    # with `timestamp` when per-run uniqueness is needed.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    other_actions = copy.deepcopy(agent_actions)
    other_actions["payouts"]["days_overdue"] = 999  # read by nothing in GOVERN

    assert (
        decide(weigh_output, agent_actions, case_context, policy)["decision_id"]
        == decide(weigh_output, other_actions, case_context, policy)["decision_id"]
    )
