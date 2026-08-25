"""
End-to-end GOVERN behaviour: the three worked examples from design §S, the
structural invariants of §U.1, determinism, and policy sensitivity.
"""

import copy
import json

import pytest

from govern.conftest import (
    build_case,
    no_conflict_release_case,
    payout_vs_dispute_case,
    real_policy,
    rto_vs_retention_case,
    variant_policy,
)
from govern import decide
from govern.schema import GOVERN_CONSTRAINT_AUTHORITY, ORDERING_SOURCE, SCORE_SOURCE


def _numbers(node):
    """Every number in a structure, excluding booleans (bool is an int)."""

    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        yield float(node)
    elif isinstance(node, dict):
        for value in node.values():
            yield from _numbers(value)
    elif isinstance(node, list):
        for item in node:
            yield from _numbers(item)


def _assert_structural_invariants(output, weigh_output, policy):
    """Design §U.1 -- these must hold for every input, on every path."""

    assert output["outcome"] in policy["escalation"]["outcomes"]
    assert output["execution_authorized"] is (output["outcome"] == "PROCEED")

    permitted_ids = output["permission_evaluation"]["permitted_candidate_ids"]
    if output["execution_authorized"]:
        assert output["selected_candidate"] is not None
        assert output["selected_candidate"]["candidate_id"] in permitted_ids
        assert output["authorized_actions"]
    else:
        assert output["selected_candidate"] is None
        assert output["authorized_actions"] == []

    # The candidate set is closed: no additions, no removals.
    assert {c["candidate_id"] for c in output["permission_evaluation"]["candidates"]} == {
        c["candidate_id"] for c in weigh_output["candidates"]
    }

    # No candidate carrying a VIOLATED or INDETERMINATE re-check is ever permitted.
    for record in output["permission_evaluation"]["candidates"]:
        blocking = [
            entry
            for entry in record["constraint_recheck"]
            if entry["status"] in ("VIOLATED", "INDETERMINATE")
        ]
        if blocking:
            assert record["candidate_id"] not in permitted_ids

    # An advisor is never reached on a path that authorizes execution.
    if output["execution_authorized"]:
        assert output["claude"]["invoked"] is False

    # A gated action can only be authorized with a determinate gate on record.
    gated = set(policy["authority"].get("actions_requiring_governance") or [])
    if output["execution_authorized"] and gated & set(output["authorized_actions"]):
        selected_id = output["selected_candidate"]["candidate_id"]
        record = next(
            r
            for r in output["permission_evaluation"]["candidates"]
            if r["candidate_id"] == selected_id
        )
        assert record["governance_gate"] is not None
        assert record["governance_gate"]["all_determinate"] is True


# --- §S.1 ------------------------------------------------------------------


def test_proceed_at_exact_threshold():
    # 0.7500 against proceed_min_score 0.75 -- the boundary is inclusive.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    assert weigh_output["candidates"][0]["total_score"] == 0.75

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "PROCEED"
    assert output["outcome_basis"] == "SCORE_AT_OR_ABOVE_PROCEED_MIN"
    assert output["execution_authorized"] is True
    assert output["authorized_actions"] == ["HOLD_RELATED_ACTIONS"]
    assert output["selected_candidate"]["candidate_id"] == "defer_to_agent-1"
    assert output["score_band"]["evaluated"] is True
    assert output["score_band"]["band"] == "PROCEED_BAND"
    assert output["score_band"]["evaluated_score"] == 0.75
    assert output["score_band"]["score_source"] == SCORE_SOURCE
    _assert_structural_invariants(output, weigh_output, policy)


def test_govern_declares_itself_the_enforcing_layer():
    # WEIGH says "advisory_only, rechecked_by GOVERN"; this is the counterpart.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert weigh_output["constraint_evaluation"]["authority"] == "advisory_only"
    assert output["permission_evaluation"]["authority"] == GOVERN_CONSTRAINT_AUTHORITY


# --- §S.2 ------------------------------------------------------------------


def test_near_tie_is_ambiguous():
    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case()
    assert [c["total_score"] for c in weigh_output["candidates"]] == [0.63, 0.62]

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "AMBIGUOUS"
    assert output["outcome_basis"] == "AMBIGUITY_DETECTED"
    assert output["execution_authorized"] is False
    assert output["selected_candidate"] is None
    # The option a human is being asked about -- deliberately a different
    # field from selected_candidate, which means "authorized to execute".
    assert output["candidate_under_review"] == "defer_to_agent-1"
    assert output["score_band"]["evaluated"] is False
    _assert_structural_invariants(output, weigh_output, policy)


def test_ambiguity_outranks_the_score_band():
    # 0.6300 is mid-band, which would otherwise HOLD. AMBIGUOUS wins because
    # an ambiguity signal says the comparison itself is not trustworthy.
    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "AMBIGUOUS"
    assert output["score_band"]["reason_not_evaluated"] == "ambiguity_detected"
    assert output["score_band"]["band"] is None


# --- §S.3: the no-conflict path -------------------------------------------


@pytest.mark.parametrize("amount", [10000, 50000])
def test_no_conflict_release_within_cap_proceeds(amount):
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(amount)
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "PROCEED"
    assert output["outcome_basis"] == "NO_CONFLICT_ALL_CHECKS_PASSED"
    assert output["execution_authorized"] is True
    assert output["authorized_actions"] == ["RELEASE_PAYMENT", "CLOSE_CASE"]
    assert output["score_band"]["evaluated"] is False
    assert output["score_band"]["reason_not_evaluated"] == "no_conflict_single_candidate"
    _assert_structural_invariants(output, weigh_output, policy)


def test_no_conflict_skips_the_band_and_nothing_else():
    # The whole point of design §C.3. 0.3100 sits BELOW hold_max_score (0.40)
    # for a perfectly benign release, yet the case proceeds -- and every
    # permission check is still on the record, per candidate.
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(50000)
    assert weigh_output["candidates"][0]["total_score"] == 0.31
    assert 0.31 <= policy["escalation"]["thresholds"]["hold_max_score"]

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "PROCEED"
    assert output["score_band"]["band"] is None
    assert output["score_band"]["evaluated_score"] is None

    record = output["permission_evaluation"]["candidates"][0]
    # All five hard constraints re-checked, not skipped.
    assert [entry["constraint_id"] for entry in record["constraint_recheck"]] == [
        hc["id"] for hc in policy["hard_constraints"]
    ]
    # Authority evaluated per action, not skipped.
    assert record["authority"]["per_action"]["RELEASE_PAYMENT"]["result"] == "AUTHORIZED"
    assert record["authority"]["per_action"]["RELEASE_PAYMENT"]["agent"] == "payouts"
    # And the governance gate is on the record for the gated action.
    assert record["governance_gate"]["gated_actions"] == ["RELEASE_PAYMENT"]
    assert record["governance_gate"]["all_determinate"] is True
    assert any(note["code"] == "G_BAND_SKIPPED_NO_CONFLICT" for note in output["notes"])


def test_no_conflict_authority_boundary_is_one_rupee_not_one_score_point():
    # PROCEED at 50 000 and ESCALATE at 50 001 -- identical score (0.3100),
    # identical band handling. The decision came from authority.
    lo = decide(*no_conflict_release_case(50000))
    hi = decide(*no_conflict_release_case(50001))

    assert lo["score_band"]["evaluated"] is False
    assert hi["score_band"]["evaluated"] is False
    assert lo["outcome"] == "PROCEED" and lo["execution_authorized"] is True
    assert hi["outcome"] == "ESCALATE" and hi["execution_authorized"] is False


# --- no re-scoring, no re-ranking -----------------------------------------


def test_govern_does_not_rescore():
    # Every number GOVERN emits must already exist in weigh_output or in
    # policy. GOVERN performs comparisons, not arithmetic.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    allowed = set(_numbers(weigh_output)) | set(_numbers(policy))
    emitted = set(_numbers(output))
    assert emitted - allowed == set()


def test_ordering_uses_weigh_total_score():
    # Permuting the order WEIGH listed its candidates in must change nothing
    # about which candidates are permitted or how they are ordered.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    baseline = decide(weigh_output, agent_actions, case_context, policy)

    permuted = copy.deepcopy(weigh_output)
    permuted["candidates"].reverse()
    permuted["ranking"].reverse()
    shuffled = decide(permuted, agent_actions, case_context, policy)

    assert (
        shuffled["permission_evaluation"]["permitted_candidate_ids"]
        == baseline["permission_evaluation"]["permitted_candidate_ids"]
        == ["defer_to_agent-1", "hold_both_pending_review-2"]
    )
    assert shuffled["outcome"] == baseline["outcome"]
    assert shuffled["selected_candidate"] == baseline["selected_candidate"]
    assert baseline["permission_evaluation"]["ordering_source"] == ORDERING_SOURCE


def test_scores_and_ranks_are_copied_verbatim_from_weigh():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    weigh_scores = {c["candidate_id"]: c["total_score"] for c in weigh_output["candidates"]}
    weigh_ranks = {r["candidate_id"]: r["score_rank"] for r in weigh_output["ranking"]}
    for record in output["permission_evaluation"]["candidates"]:
        assert record["total_score"] == weigh_scores[record["candidate_id"]]
        assert record["score_rank"] == weigh_ranks[record["candidate_id"]]


# --- determinism and purity ------------------------------------------------


def test_deterministic_repeated_calls():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    first = decide(weigh_output, agent_actions, case_context, policy)
    second = decide(weigh_output, agent_actions, case_context, policy)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_deterministic_across_independently_built_inputs():
    first = decide(*payout_vs_dispute_case())
    second = decide(*payout_vs_dispute_case())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_inputs_are_not_mutated():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    before = copy.deepcopy((weigh_output, agent_actions, case_context, policy))

    output = decide(weigh_output, agent_actions, case_context, policy)
    # Mutating the output must not reach back into an input either.
    output["case"]["entity_type"] = "tampered"
    output["weights_used"]["merchant_trust"] = 99

    assert (weigh_output, agent_actions, case_context, policy) == before


# --- policy sensitivity ----------------------------------------------------


def test_policy_change_changes_outcome_without_code_change():
    # One number in policy, same evidence, same code: PROCEED becomes HOLD.
    before_inputs = payout_vs_dispute_case()
    before = decide(*before_inputs)
    assert before["outcome"] == "PROCEED"

    tightened = variant_policy(proceed_min_score=0.76)
    after_inputs = payout_vs_dispute_case(policy=tightened)
    after = decide(*after_inputs)

    assert after["outcome"] == "HOLD"
    assert after["outcome_basis"] == "SCORE_IN_MID_BAND"
    assert after["execution_authorized"] is False
    # Same score on both sides -- only the threshold moved.
    assert after["score_band"]["evaluated_score"] == before["score_band"]["evaluated_score"]
    assert after["policy_hash"] != before["policy_hash"]


def test_profile_change_moves_the_same_case_into_the_mid_band():
    # §S.1's third variant: a trusted merchant scores 0.6475 on identical
    # evidence, which lands in the band policy resolves via mid_band_outcome.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(
        case_context={"case_id": "case-Q", "merchant_trust_tier": "trusted"}
    )
    assert weigh_output["profile"]["profile_name"] == "trusted_merchant"
    assert weigh_output["candidates"][0]["total_score"] == 0.6475

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["score_band"]["band"] == "MID_BAND"
    assert output["outcome"] == policy["escalation"]["thresholds"]["mid_band_outcome"]
    assert output["outcome_basis"] == "SCORE_IN_MID_BAND"
    assert output["execution_authorized"] is False
    assert any(note["code"] == "G_MID_BAND_OUTCOME_APPLIED" for note in output["notes"])


# --- receipt shape ---------------------------------------------------------


def test_audit_receipt_structure_is_complete_and_machine_readable():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    for block in ("score_band", "permission_evaluation", "escalation", "claude", "rationale"):
        assert isinstance(output[block], dict), block

    assert output["rationale"]["reasons"] == [
        "CONSTRAINTS_RECHECKED_CLEAN",
        "AUTHORITY_SATISFIED",
        "SCORE_AT_OR_ABOVE_PROCEED_MIN",
    ]
    assert "0.75" in output["rationale"]["outcome_sentence"]
    assert output["rationale"]["claude_narrative"] is None
    assert output["escalation"]["required"] is False
    assert output["escalation"]["reasons"] == []
    # The whole receipt must survive a round trip as plain JSON.
    assert json.loads(json.dumps(output)) == output


def test_governance_gate_recorded_for_gated_actions():
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(50000)
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert "RELEASE_PAYMENT" in output["authorized_actions"]
    assert output["escalation"]["actions_requiring_governance_matched"] == ["RELEASE_PAYMENT"]
    gate = output["permission_evaluation"]["candidates"][0]["governance_gate"]
    assert gate["checks_run"] == {
        "constraint_recheck_performed": True,
        "originating_agent_resolved": True,
        "authority_entry_found": True,
        "amount_limit_evaluated": True,
    }
    assert gate["all_determinate"] is True


def test_case_and_profile_are_echoed_not_rederived():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["case"] == weigh_output["case"]
    assert output["profile_selected"] == weigh_output["profile"]["profile_name"]
    assert output["weights_used"] == weigh_output["profile"]["weights"]
    assert output["policy_id"] == weigh_output["policy_id"]
    assert output["policy_version"] == weigh_output["policy_version"]
    assert output["policy_hash"] == weigh_output["policy_hash"]


def test_unknown_entity_pair_without_conflict_still_runs_every_check():
    # A benign no-conflict pair whose actions appear in no agent's
    # autonomous_actions is blocked, not waved through (design §H.4).
    rto = {"agent": "rto", "proposed_action": "ALLOW_ORDER", "confidence": 0.9}
    retention = {
        "agent": "retention",
        "proposed_action": "WIN_BACK_OFFER",
        "confidence": 0.9,
        "amount": 1000,
    }
    weigh_output, agent_actions, case_context, policy = build_case(
        rto, retention, "customer", {"merchant_flags": []}
    )
    assert weigh_output["case"]["conflict"] is False

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "ESCALATE"
    assert output["execution_authorized"] is False
    assert "HC_UNAUTHORIZED_ACTION:VIOLATED" in output["escalation"]["reasons"]
    assert "AUTHORITY_EXCEEDED:rto:ALLOW_ORDER" in output["escalation"]["reasons"]
    _assert_structural_invariants(output, weigh_output, real_policy())
