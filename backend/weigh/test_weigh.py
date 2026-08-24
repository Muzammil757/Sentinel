import copy
import json

import pytest

from conflict_matrix.integration import evaluate_agent_actions
from mock_agents.disputes import generate_dispute_action
from mock_agents.payouts import generate_payout_action
from mock_agents.retention import generate_retention_action
from mock_agents.rto import generate_rto_action
from policy.loader import compute_policy_hash, load_policy
from resolve.resolver import generate_resolution_candidates
from weigh import WeighInputError, WeighPolicyError, evaluate_candidates
from weigh.schema import FORBIDDEN_OUTPUT_KEYS


def _policy():
    return load_policy()


def _two_candidate_conflict():
    resolve_output = {
        "entity_type": "order_vendor",
        "agent_a": "payouts",
        "agent_b": "dispute",
        "conflict": True,
        "unresolved": False,
        "candidates": [
            {
                "candidate_id": "defer_to_agent-1",
                "strategy": "DEFER_TO_AGENT",
                "preferred_agent": "dispute",
                "resulting_actions": ["HOLD_RELATED_ACTIONS"],
                "rationale": "Static agent priority order favors dispute.",
                "source_rule": "release_payment_vs_hold_related_actions",
            },
            {
                "candidate_id": "hold_both_pending_review-2",
                "strategy": "HOLD_BOTH_PENDING_REVIEW",
                "preferred_agent": None,
                "resulting_actions": [],
                "rationale": "Conservative fallback.",
                "source_rule": "release_payment_vs_hold_related_actions",
            },
        ],
    }
    agent_actions = {
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.95, "amount": 42000},
        "dispute": {
            "agent": "dispute",
            "proposed_action": "HOLD_RELATED_ACTIONS",
            "confidence": 0.95,
            "dispute_status": "OPEN",
        },
    }
    case_context = {"case_id": "case-weigh-1"}
    return resolve_output, agent_actions, case_context


def _no_conflict_single_candidate():
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
                "rationale": "No conflict was detected between the two actions.",
                "source_rule": "no_conflict_passthrough",
            }
        ],
    }
    agent_actions = {
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.85, "amount": 10000},
        "dispute": {"agent": "dispute", "proposed_action": "CLOSE_CASE", "confidence": 0.90},
    }
    return resolve_output, agent_actions, {}


def _unresolved_single_candidate():
    resolve_output = {
        "entity_type": "order_vendor",
        "agent_a": "payouts",
        "agent_b": "rto",
        "conflict": True,
        "unresolved": True,
        "candidates": [
            {
                "candidate_id": "hold_both_pending_review-1",
                "strategy": "HOLD_BOTH_PENDING_REVIEW",
                "preferred_agent": None,
                "resulting_actions": [],
                "rationale": "No matching resolution rule.",
                "source_rule": "no_matching_resolution_rule",
            }
        ],
    }
    agent_actions = {
        "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.85},
        "rto": {"agent": "rto", "proposed_action": "REVIEW_ORDER", "confidence": 0.80},
    }
    return resolve_output, agent_actions, {}


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_keys(item)


# ---------------------------------------------------------------------------
# Determinism and contract invariants
# ---------------------------------------------------------------------------


def test_deterministic_repeated_calls():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result_1 = evaluate_candidates(resolve_output, agent_actions, case_context, policy)
    result_2 = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert result_1 == result_2
    assert json.dumps(result_1, sort_keys=True) == json.dumps(result_2, sort_keys=True)


def test_inputs_are_not_mutated():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    resolve_before = copy.deepcopy(resolve_output)
    agent_before = copy.deepcopy(agent_actions)
    context_before = copy.deepcopy(case_context)
    policy_before = copy.deepcopy(policy)

    evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert resolve_output == resolve_before
    assert agent_actions == agent_before
    assert case_context == context_before
    assert policy == policy_before


def test_no_candidate_invention_or_mutation():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    input_ids = {c["candidate_id"] for c in resolve_output["candidates"]}
    output_ids = {c["candidate_id"] for c in result["candidates"]}
    assert input_ids == output_ids

    by_id_in = {c["candidate_id"]: c for c in resolve_output["candidates"]}
    for out_candidate in result["candidates"]:
        in_candidate = by_id_in[out_candidate["candidate_id"]]
        assert out_candidate["strategy"] == in_candidate["strategy"]
        assert out_candidate["preferred_agent"] == in_candidate["preferred_agent"]
        assert out_candidate["resulting_actions"] == in_candidate["resulting_actions"]
        assert out_candidate["rationale"] == in_candidate["rationale"]
        assert out_candidate["source_rule"] == in_candidate["source_rule"]


def test_no_final_decision_field():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    keys_found = set(_walk_keys(result))
    forbidden_hit = keys_found & FORBIDDEN_OUTPUT_KEYS
    assert forbidden_hit == set()


def test_agent_order_does_not_change_result():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    result_1 = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    swapped = copy.deepcopy(resolve_output)
    swapped["agent_a"], swapped["agent_b"] = swapped["agent_b"], swapped["agent_a"]
    result_2 = evaluate_candidates(swapped, agent_actions, case_context, policy)

    scores_1 = {c["candidate_id"]: c["total_score"] for c in result_1["candidates"]}
    scores_2 = {c["candidate_id"]: c["total_score"] for c in result_2["candidates"]}
    assert scores_1 == scores_2
    assert result_1["evidence"]["contributing_agents"] == result_2["evidence"]["contributing_agents"]


# ---------------------------------------------------------------------------
# Case shape coverage
# ---------------------------------------------------------------------------


def test_no_conflict_single_candidate():
    resolve_output, agent_actions, case_context = _no_conflict_single_candidate()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert result["case"]["conflict"] is False
    assert len(result["candidates"]) == 1
    signal_codes = {s["code"] for s in result["ambiguity"]["signals"]}
    assert "SINGLE_CANDIDATE" in signal_codes
    assert result["ambiguity"]["top_gap"] is None


def test_unresolved_single_candidate_is_eligible():
    resolve_output, agent_actions, case_context = _unresolved_single_candidate()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert result["case"]["unresolved"] is True
    candidate = result["candidates"][0]
    assert candidate["eligible"] is True
    assert all(f["status"] == "NOT_APPLICABLE" for f in candidate["constraint_findings"])


def test_multiple_candidates_all_scored():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert len(result["candidates"]) == 2
    objective_names = set(policy["objectives"].keys())
    for candidate in result["candidates"]:
        assert set(candidate["objective_impacts"].keys()) == objective_names
        assert 0.0 <= candidate["total_score"] <= 1.0


def test_worked_example_scores_match_design_doc_exactly():
    # Reproduces docs/weigh_layer_design.md §Q exactly.
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)
    by_id = {c["candidate_id"]: c["total_score"] for c in result["candidates"]}

    assert by_id["defer_to_agent-1"] == 0.75
    assert by_id["hold_both_pending_review-2"] == 0.62
    assert result["ambiguity"]["detected"] is False


def test_policy_identity_propagates():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()

    result = evaluate_candidates(resolve_output, agent_actions, case_context, policy)

    assert result["policy_id"] == policy["policy"]["policy_id"]
    assert result["policy_version"] == policy["policy"]["version"]
    assert result["policy_hash"] == compute_policy_hash(policy)


# ---------------------------------------------------------------------------
# Full pipeline integration (real mock agents + conflict matrix + RESOLVE)
# ---------------------------------------------------------------------------


def test_full_pipeline_payouts_vs_dispute_conflict():
    payout = generate_payout_action(vendor_id="v1", amount=42000, invoice_id="inv1", days_overdue=9)
    dispute = generate_dispute_action(dispute_id="d1", order_id="o1", dispute_status="OPEN", disputed_amount=42000)

    conflict_result = evaluate_agent_actions(payout, dispute, entity_type="order_vendor")
    resolve_output = generate_resolution_candidates(conflict_result, payout, dispute)
    agent_actions = {"payouts": payout, "dispute": dispute}

    result = evaluate_candidates(resolve_output, agent_actions, {}, _policy())

    assert result["case"]["conflict"] is True
    assert {c["candidate_id"] for c in result["candidates"]} == {
        c["candidate_id"] for c in resolve_output["candidates"]
    }
    defer_candidate = next(c for c in result["candidates"] if c["strategy"] == "DEFER_TO_AGENT")
    assert defer_candidate["preferred_agent"] == "dispute"


def test_full_pipeline_rto_vs_retention_conflict():
    rto = generate_rto_action(order_id="o1", customer_id="c1", rto_score=0.80, shipment_status="in_transit")
    retention = generate_retention_action(customer_id="c1", order_id="o1", customer_value_score=0.7, churn_risk=0.80)

    conflict_result = evaluate_agent_actions(rto, retention, entity_type="customer")
    resolve_output = generate_resolution_candidates(conflict_result, rto, retention)
    agent_actions = {"rto": rto, "retention": retention}

    result = evaluate_candidates(resolve_output, agent_actions, {}, _policy())

    assert result["case"]["conflict"] is True
    assert {c["candidate_id"] for c in result["candidates"]} == {
        c["candidate_id"] for c in resolve_output["candidates"]
    }
    defer_candidate = next(c for c in result["candidates"] if c["strategy"] == "DEFER_TO_AGENT")
    assert defer_candidate["preferred_agent"] == "rto"


def test_full_pipeline_no_conflict_release_vs_close_case():
    payout = generate_payout_action(vendor_id="v1", amount=5000, invoice_id="inv2", days_overdue=2)
    dispute = generate_dispute_action(dispute_id="d2", order_id="o2", dispute_status="CLOSED", disputed_amount=5000)

    conflict_result = evaluate_agent_actions(payout, dispute, entity_type="order_vendor")
    resolve_output = generate_resolution_candidates(conflict_result, payout, dispute)
    agent_actions = {"payouts": payout, "dispute": dispute}

    result = evaluate_candidates(resolve_output, agent_actions, {}, _policy())

    assert result["case"]["conflict"] is False
    assert len(result["candidates"]) == 1


# ---------------------------------------------------------------------------
# Fail-safe behavior
# ---------------------------------------------------------------------------


def test_missing_agent_payload_raises_input_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    del agent_actions["dispute"]

    with pytest.raises(WeighInputError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)


def test_duplicate_candidate_ids_raise_input_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    resolve_output["candidates"][1]["candidate_id"] = resolve_output["candidates"][0]["candidate_id"]

    with pytest.raises(WeighInputError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)


def test_empty_candidates_raises_input_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    resolve_output["candidates"] = []

    with pytest.raises(WeighInputError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)


def test_case_context_must_be_a_mapping():
    resolve_output, agent_actions, _case_context = _two_candidate_conflict()
    policy = _policy()

    with pytest.raises(WeighInputError):
        evaluate_candidates(resolve_output, agent_actions, ["not", "a", "dict"], policy)


def test_unmapped_action_raises_policy_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    del policy["scoring"]["action_effects"]["HOLD_RELATED_ACTIONS"]

    with pytest.raises(WeighPolicyError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)


def test_unregistered_constraint_raises_policy_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    policy["hard_constraints"] = list(policy["hard_constraints"]) + [
        {"id": "HC_UNKNOWN", "description": "test", "enforcement": "block"}
    ]

    with pytest.raises(WeighPolicyError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)


def test_missing_scoring_section_raises_policy_error():
    resolve_output, agent_actions, case_context = _two_candidate_conflict()
    policy = _policy()
    del policy["scoring"]

    with pytest.raises(WeighPolicyError):
        evaluate_candidates(resolve_output, agent_actions, case_context, policy)
