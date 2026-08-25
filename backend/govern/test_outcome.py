"""
Phase 4: the decision table, the score bands, and the ambiguity gate
(design §F.1, §I, §J).

Mostly unit-level, because the decision table is the thing a judge will be
shown and it should be demonstrable without a whole pipeline behind it.
"""

import copy

import pytest

from govern import decide
from govern.conftest import (
    build_case,
    payout_vs_dispute_case,
    real_policy,
    rto_vs_retention_case,
    variant_policy,
)
from govern.errors import GovernPolicyError
from govern.outcome import (
    ambiguity_applies,
    applying_ambiguity_codes,
    classify_band,
    decide_outcome,
)


def _permitted(candidate_id, score, requires_escalation=False):
    return {
        "candidate_id": candidate_id,
        "total_score": score,
        "authority": {
            "requires_escalation": requires_escalation,
            "escalation_matches": (
                ["strategy:HOLD_BOTH_PENDING_REVIEW"] if requires_escalation else []
            ),
            "escalation_match": (
                "strategy:HOLD_BOTH_PENDING_REVIEW" if requires_escalation else None
            ),
        },
    }


def _ambiguity(detected=False, codes=()):
    return {
        "detected": detected,
        "signals": [{"code": code, "detail": {}} for code in codes],
        "near_tie_group": [],
        "top_gap": None,
    }


THRESHOLDS = {"proceed_min_score": 0.75, "hold_max_score": 0.40, "mid_band_outcome": "HOLD"}


# --- band classification ---------------------------------------------------


@pytest.mark.parametrize(
    "score,expected",
    [
        (1.00, "PROCEED_BAND"),
        (0.7501, "PROCEED_BAND"),
        (0.7500, "PROCEED_BAND"),  # inclusive at the top
        (0.7499, "MID_BAND"),
        (0.4001, "MID_BAND"),
        (0.4000, "HOLD_BAND"),  # inclusive at the bottom
        (0.0000, "HOLD_BAND"),
    ],
)
def test_band_boundaries_are_inclusive_at_both_ends(score, expected):
    assert classify_band(score, THRESHOLDS) == expected


# --- the decision table, row by row ---------------------------------------


def test_d1_empty_permitted_set_escalates():
    outcome, basis, band = decide_outcome([], True, _ambiguity(), True, THRESHOLDS)
    assert (outcome, basis) == ("ESCALATE", "NO_PERMITTED_CANDIDATE")
    assert band["evaluated"] is False
    assert band["reason_not_evaluated"] == "no_permitted_candidate"


def test_d2_disagreement_escalates_before_anything_else_is_read():
    # A high-scoring, unflagged, unambiguous candidate still escalates.
    permitted = [_permitted("c1", 0.99)]
    outcome, basis, band = decide_outcome(permitted, False, _ambiguity(), True, THRESHOLDS)
    assert (outcome, basis) == ("ESCALATE", "GOVERN_WEIGH_DISAGREEMENT")
    assert band["band"] is None


def test_d3_flagged_top_candidate_escalates_before_the_band():
    permitted = [_permitted("c1", 0.99, requires_escalation=True)]
    outcome, basis, _band = decide_outcome(permitted, True, _ambiguity(), True, THRESHOLDS)
    assert (outcome, basis) == ("ESCALATE", "ACTION_REQUIRES_ESCALATION")


def test_d4_ambiguity_outranks_a_proceed_band_score():
    # Deliberate and accepted: a near-tie at 0.80 vs 0.78 is AMBIGUOUS, not
    # PROCEED. Reading a band off an untrustworthy comparison is exactly the
    # failure the ambiguity machinery exists to prevent.
    permitted = [_permitted("c1", 0.80), _permitted("c2", 0.78)]
    outcome, basis, band = decide_outcome(
        permitted, True, _ambiguity(True, ["NEAR_TIE"]), True, THRESHOLDS
    )
    assert (outcome, basis) == ("AMBIGUOUS", "AMBIGUITY_DETECTED")
    assert band["evaluated"] is False


def test_d5_no_conflict_skips_the_band_only():
    permitted = [_permitted("c1", 0.31)]
    outcome, basis, band = decide_outcome(permitted, True, _ambiguity(), False, THRESHOLDS)
    assert (outcome, basis) == ("PROCEED", "NO_CONFLICT_ALL_CHECKS_PASSED")
    assert band["reason_not_evaluated"] == "no_conflict_single_candidate"
    assert band["band"] is None


def test_d5_is_reached_only_after_every_gate_above_it():
    # The same no-conflict case fails each earlier row in turn.
    ambiguous = _ambiguity(True, ["LOW_CONFIDENCE"])
    assert decide_outcome([], True, _ambiguity(), False, THRESHOLDS)[0] == "ESCALATE"
    assert (
        decide_outcome([_permitted("c1", 0.31)], False, _ambiguity(), False, THRESHOLDS)[0]
        == "ESCALATE"
    )
    assert (
        decide_outcome(
            [_permitted("c1", 0.31, requires_escalation=True)], True, _ambiguity(), False, THRESHOLDS
        )[0]
        == "ESCALATE"
    )
    assert (
        decide_outcome([_permitted("c1", 0.31)], True, ambiguous, False, THRESHOLDS)[0]
        == "AMBIGUOUS"
    )


@pytest.mark.parametrize(
    "score,expected_outcome,expected_basis",
    [
        (0.7500, "PROCEED", "SCORE_AT_OR_ABOVE_PROCEED_MIN"),
        (0.7499, "HOLD", "SCORE_IN_MID_BAND"),
        (0.4001, "HOLD", "SCORE_IN_MID_BAND"),
        (0.4000, "HOLD", "SCORE_AT_OR_BELOW_HOLD_MAX"),
    ],
)
def test_d6_reads_the_band_off_the_top_permitted_candidate(
    score, expected_outcome, expected_basis
):
    permitted = [_permitted("c1", score)]
    outcome, basis, band = decide_outcome(permitted, True, _ambiguity(), True, THRESHOLDS)
    assert (outcome, basis) == (expected_outcome, expected_basis)
    assert band["evaluated"] is True
    assert band["evaluated_candidate_id"] == "c1"
    assert band["evaluated_score"] == score


def test_band_is_read_off_the_top_permitted_not_the_top_scorer():
    # A blocked candidate's score never reaches the band comparison: only
    # the permitted set is passed in, so the 0.99 top scorer is invisible
    # here and the band is read off the 0.30 candidate GOVERN would authorize.
    permitted = [_permitted("survivor", 0.30)]
    outcome, basis, band = decide_outcome(permitted, True, _ambiguity(), True, THRESHOLDS)

    assert band["evaluated_candidate_id"] == "survivor"
    assert band["evaluated_score"] == 0.30
    assert (outcome, basis) == ("HOLD", "SCORE_AT_OR_BELOW_HOLD_MAX")


# --- the mid band comes from policy ---------------------------------------


def test_mid_band_uses_the_policy_outcome():
    permitted = [_permitted("c1", 0.60)]

    holding = decide_outcome(permitted, True, _ambiguity(), True, THRESHOLDS)
    assert holding[0] == "HOLD"

    escalating_thresholds = dict(THRESHOLDS, mid_band_outcome="ESCALATE")
    escalating = decide_outcome(permitted, True, _ambiguity(), True, escalating_thresholds)
    assert escalating[0] == "ESCALATE"
    assert escalating[1] == "SCORE_IN_MID_BAND"


def test_mid_band_policy_flip_changes_the_outcome_end_to_end():
    # 0.7500 lands in the mid band once proceed_min_score is 0.7501.
    holding = variant_policy(proceed_min_score=0.7501)
    output = decide(*payout_vs_dispute_case(policy=holding))
    assert output["score_band"]["band"] == "MID_BAND"
    assert output["outcome"] == "HOLD"

    escalating = variant_policy(proceed_min_score=0.7501, mid_band_outcome="ESCALATE")
    output = decide(*payout_vs_dispute_case(policy=escalating))
    assert output["score_band"]["band"] == "MID_BAND"
    assert output["outcome"] == "ESCALATE"
    assert output["execution_authorized"] is False


def test_hold_band_boundary_end_to_end():
    # Move hold_max_score up to 0.75 so the real 0.7500 score sits exactly on
    # the inclusive lower boundary.
    policy = variant_policy(proceed_min_score=0.90, hold_max_score=0.75)
    output = decide(*payout_vs_dispute_case(policy=policy))

    assert output["score_band"]["band"] == "HOLD_BAND"
    assert output["outcome"] == "HOLD"
    assert output["outcome_basis"] == "SCORE_AT_OR_BELOW_HOLD_MAX"
    assert output["execution_authorized"] is False


def test_missing_mid_band_outcome_raises_at_preflight():
    # A missing band definition is not the kind of thing that should surface
    # for the first time on stage, in the one case that scores 0.6475.
    broken = copy.deepcopy(real_policy())
    del broken["escalation"]["thresholds"]["mid_band_outcome"]

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError, match="mid_band_outcome"):
        decide(weigh_output, agent_actions, case_context, policy)


@pytest.mark.parametrize("value", ["PROCEED", "AMBIGUOUS", "HOLD_FOR_REVIEW", "", None, 1])
def test_illegal_mid_band_outcome_raises(value):
    broken = copy.deepcopy(real_policy())
    broken["escalation"]["thresholds"]["mid_band_outcome"] = value

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError, match="mid_band_outcome"):
        decide(weigh_output, agent_actions, case_context, policy)


# --- ambiguity gating ------------------------------------------------------


def test_undetected_ambiguity_never_applies():
    assert ambiguity_applies(_ambiguity(False, ["NEAR_TIE"]), 2) is False


def test_comparative_signals_need_two_permitted_candidates():
    near_tie = _ambiguity(True, ["NEAR_TIE"])
    assert ambiguity_applies(near_tie, 2) is True
    # If GOVERN's authority gates permitted only one of the tied pair, the
    # tie is moot and reporting AMBIGUOUS over a field of one would mislead.
    assert ambiguity_applies(near_tie, 1) is False

    conflicting = _ambiguity(True, ["CONFLICTING_OBJECTIVES"])
    assert ambiguity_applies(conflicting, 2) is True
    assert ambiguity_applies(conflicting, 1) is False


def test_non_comparative_signals_apply_however_many_candidates_survive():
    # Weak or incomplete evidence is a statement about the case, not about
    # the comparison.
    for code in ("LOW_CONFIDENCE", "INSUFFICIENT_EVIDENCE"):
        assert ambiguity_applies(_ambiguity(True, [code]), 1) is True
        assert ambiguity_applies(_ambiguity(True, [code]), 2) is True


def test_single_candidate_signal_is_informational_only():
    # weigh.ambiguity never sets `detected` for SINGLE_CANDIDATE, and GOVERN
    # treats it as neither comparative nor non-comparative.
    assert ambiguity_applies(_ambiguity(False, ["SINGLE_CANDIDATE"]), 1) is False
    assert applying_ambiguity_codes(_ambiguity(True, ["SINGLE_CANDIDATE"]), 1) == []


def test_applying_codes_report_only_the_signals_that_drove_the_outcome():
    ambiguity = _ambiguity(True, ["NEAR_TIE", "LOW_CONFIDENCE"])
    assert applying_ambiguity_codes(ambiguity, 1) == ["LOW_CONFIDENCE"]
    assert applying_ambiguity_codes(ambiguity, 2) == ["LOW_CONFIDENCE", "NEAR_TIE"]


def test_low_confidence_case_is_ambiguous_end_to_end():
    # Both agents sit below ambiguity.low_confidence_threshold (0.55) but at
    # or above a relaxed HC_CONFIDENCE_FLOOR, so nothing is blocked and the
    # LOW_CONFIDENCE signal is the only thing driving the outcome.
    relaxed = copy.deepcopy(real_policy())
    floor = next(hc for hc in relaxed["hard_constraints"] if hc["id"] == "HC_CONFIDENCE_FLOOR")
    floor["parameters"]["min_confidence"] = 0.30

    payouts = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.40,
        "amount": 42000,
    }
    dispute = {
        "agent": "dispute",
        "proposed_action": "HOLD_RELATED_ACTIONS",
        "confidence": 0.40,
        "dispute_status": "OPEN",
    }
    weigh_output, agent_actions, case_context, policy = build_case(
        payouts, dispute, "order_vendor", {"case_id": "case-L"}, policy=relaxed
    )
    assert "LOW_CONFIDENCE" in {s["code"] for s in weigh_output["ambiguity"]["signals"]}

    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "AMBIGUOUS"
    assert output["execution_authorized"] is False
    assert "AMBIGUITY_SIGNAL:LOW_CONFIDENCE" in output["rationale"]["reasons"]


def test_ambiguous_never_authorizes_execution():
    output = decide(*rto_vs_retention_case())
    assert output["outcome"] == "AMBIGUOUS"
    assert output["execution_authorized"] is False
    assert output["selected_candidate"] is None
    assert output["authorized_actions"] == []
