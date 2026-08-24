"""
Design §T: WEIGH evaluates governance OPTIONS, never the entity itself. It
must not become a fraud/RTO/chargeback classifier, must not read a
continuous agent-specific risk field into the score arithmetic, must never
call Claude, and must never execute anything.
"""

import ast
from pathlib import Path

from weigh import evaluate_candidates
from weigh.constraints import _eval_thirdwatch_high_risk_payout
from policy.loader import load_policy

WEIGH_PACKAGE_DIR = Path(__file__).resolve().parent

# Checked via the import graph (ast), not substring search on file text --
# a substring check would false-positive on this very file's docstrings,
# which legitimately explain the Claude/network/DB boundary in prose.
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
    "database",
}


def _non_test_source_files():
    return [p for p in WEIGH_PACKAGE_DIR.glob("*.py") if not p.name.startswith("test_")]


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


def test_no_forbidden_imports_in_weigh_source():
    # No Claude/Anthropic client, no network, no database, no clock, no
    # randomness -- verified against the actual import graph, so WEIGH is
    # structurally incapable of any of these, not just documented as such.
    for path in _non_test_source_files():
        roots = _imported_module_roots(path)
        forbidden_hit = roots & FORBIDDEN_IMPORT_MODULES
        assert not forbidden_hit, f"{path.name} imports forbidden module(s): {forbidden_hit}"

        # datetime is unimported anywhere in weigh/*.py, so datetime.now()/
        # utcnow() are structurally unreachable -- not just avoided by
        # convention.
        assert "datetime" not in roots, path.name


def test_weigh_never_loads_policy_itself():
    # WEIGH consumes an already-loaded, already-validated policy dict.
    # compute_policy_hash is fine -- it's a pure hash over the dict already
    # passed in, not a file read -- but load_policy (which reads
    # policy_bundle.yaml from disk) must never appear in weigh source.
    for path in _non_test_source_files():
        names = _imported_names_from(path, "policy.loader")
        assert "load_policy" not in names, path.name

    weigh_py_names = _imported_names_from(WEIGH_PACKAGE_DIR / "weigh.py", "policy.loader")
    assert "compute_policy_hash" in weigh_py_names


def _rto_vs_retention_case(rto_score, churn_risk):
    resolve_output = {
        "entity_type": "customer",
        "agent_a": "rto",
        "agent_b": "retention",
        "conflict": True,
        "unresolved": False,
        "candidates": [
            {
                "candidate_id": "defer_to_agent-1",
                "strategy": "DEFER_TO_AGENT",
                "preferred_agent": "rto",
                "resulting_actions": ["HOLD_ORDER"],
                "rationale": "r1",
                "source_rule": "hold_order_vs_win_back_offer",
            },
            {
                "candidate_id": "hold_both_pending_review-2",
                "strategy": "HOLD_BOTH_PENDING_REVIEW",
                "preferred_agent": None,
                "resulting_actions": [],
                "rationale": "r2",
                "source_rule": "hold_order_vs_win_back_offer",
            },
        ],
    }
    agent_actions = {
        "rto": {
            "agent": "rto",
            "proposed_action": "HOLD_ORDER",
            "confidence": 0.95,
            "rto_score": rto_score,  # varied below; must have zero effect
        },
        "retention": {
            "agent": "retention",
            "proposed_action": "WIN_BACK_OFFER",
            "confidence": 0.95,
            "churn_risk": churn_risk,  # varied below; must have zero effect
        },
    }
    return resolve_output, agent_actions


def test_continuous_agent_risk_fields_have_zero_effect_on_output():
    # rto_score and churn_risk are agent-internal risk signals. With
    # proposed_action and confidence held fixed, varying these continuous
    # fields must not move the score, the constraint findings, or the
    # ranking by even one unit -- proving WEIGH scores the declared option,
    # never re-derives a risk estimate from the raw evidence.
    policy = load_policy()
    outputs = []
    for rto_score, churn_risk in [(0.76, 0.76), (0.90, 0.60), (0.99, 0.99), (0.999, 0.51)]:
        resolve_output, agent_actions = _rto_vs_retention_case(rto_score, churn_risk)
        result = evaluate_candidates(resolve_output, agent_actions, {}, policy)
        scores = tuple(sorted((c["candidate_id"], c["total_score"]) for c in result["candidates"]))
        findings = tuple(
            sorted(
                (c["candidate_id"], f["constraint_id"], f["status"])
                for c in result["candidates"]
                for f in c["constraint_findings"]
            )
        )
        outputs.append((scores, findings))

    assert len(set(outputs)) == 1, "varying rto_score/churn_risk changed WEIGH's output"


def test_thirdwatch_constraint_reads_declared_verdict_not_raw_score():
    # The one place a continuous risk field COULD leak into a decision is
    # HC_THIRDWATCH_HIGH_RISK_PAYOUT. It must key off the RTO agent's own
    # proposed_action, never off rto_score directly.
    policy = load_policy()
    constraint = next(hc for hc in policy["hard_constraints"] if hc["id"] == "HC_THIRDWATCH_HIGH_RISK_PAYOUT")
    candidate = {"resulting_actions": ["RELEASE_PAYMENT"]}

    # rto_score of 0.99 would normally imply HOLD_ORDER, but the agent's
    # declared verdict here is ALLOW_ORDER -- the constraint must follow
    # the declared verdict, not the raw score.
    agent_actions = {"rto": {"proposed_action": "ALLOW_ORDER", "rto_score": 0.99}}
    finding = _eval_thirdwatch_high_risk_payout(candidate, agent_actions, {}, constraint, policy, 0.90)
    assert finding["status"] == "SATISFIED"
    assert finding["observed"] == {"rto.proposed_action": "ALLOW_ORDER"}
    assert "rto_score" not in str(finding)


def test_weigh_output_never_contains_a_risk_score_field():
    resolve_output, agent_actions = _rto_vs_retention_case(0.80, 0.80)
    policy = load_policy()
    result = evaluate_candidates(resolve_output, agent_actions, {}, policy)

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                yield key
                yield from walk(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from walk(item)

    forbidden_entity_risk_keys = {
        "risk_score",
        "fraud_score",
        "rto_risk",
        "chargeback_risk",
        "severity",
        "exposure_amount",
    }
    keys_found = set(walk(result))
    assert keys_found & forbidden_entity_risk_keys == set()


def test_weigh_evaluates_governance_options_not_the_entity():
    # Structural proof: WEIGH's public signature takes RESOLVE's candidate
    # set as its subject. With a single-agent (no-conflict) case there is
    # only one candidate and nothing to weigh between -- the layer has
    # nothing to say about "is this order risky" in isolation.
    resolve_output = {
        "entity_type": "order_vendor",
        "agent_a": "payouts",
        "agent_b": "dispute",
        "conflict": False,
        "unresolved": False,
        "candidates": [
            {
                "candidate_id": "no_conflict_proceed-1",
                "strategy": "NO_CONFLICT_PROCEED",
                "preferred_agent": None,
                "resulting_actions": ["RELEASE_PAYMENT", "CLOSE_CASE"],
                "rationale": "no conflict",
                "source_rule": "no_conflict_passthrough",
            }
        ],
    }
    agent_actions = {
        # amount + dispute_status + an rto verdict supplied so all three
        # RELEASE_PAYMENT-gated constraints (HC_UNAUTHORIZED_ACTION,
        # HC_PAYOUT_DURING_CHARGEBACK, HC_THIRDWATCH_HIGH_RISK_PAYOUT)
        # resolve to SATISFIED rather than INDETERMINATE -- this test is
        # about candidate count, not constraint findings. agent_actions may
        # legitimately carry agents beyond agent_a/agent_b (design §D.3):
        # a constraint gated on RELEASE_PAYMENT is entitled to consult
        # rto's verdict even when rto isn't one of the two conflicting
        # agents in this particular case.
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.85, "amount": 5000},
        "dispute": {"agent": "dispute", "proposed_action": "CLOSE_CASE", "confidence": 0.90, "dispute_status": "CLOSED"},
        "rto": {"agent": "rto", "proposed_action": "ALLOW_ORDER", "confidence": 0.90},
    }
    result = evaluate_candidates(resolve_output, agent_actions, {}, load_policy())

    # There is exactly one option -- WEIGH ranks it against nothing.
    assert len(result["ranking"]) == 1
    assert {s["code"] for s in result["ambiguity"]["signals"]} == {"SINGLE_CANDIDATE"}
