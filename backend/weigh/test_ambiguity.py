from weigh.ambiguity import evaluate_ambiguity

AMBIGUITY_POLICY = {
    "near_tie_threshold": 0.05,
    "insufficient_evidence": {"min_supporting_signals": 1},
    "low_confidence_threshold": 0.55,
    "conflicting_objectives": {},
}


def _candidate(candidate_id, total_score, eligible=True, objective_impacts=None):
    return {
        "candidate_id": candidate_id,
        "total_score": total_score,
        "eligible": eligible,
        "objective_impacts": objective_impacts or {},
    }


def _codes(ambiguity_block):
    return {s["code"] for s in ambiguity_block["signals"]}


def test_clear_winner_no_ambiguity():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.30)]
    block, tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert block["detected"] is False
    assert block["signals"] == []
    assert block["top_gap"] == 0.50
    assert tie_ids == set()


def test_near_tie_detected_within_threshold():
    candidates = [_candidate("a", 0.812), _candidate("b", 0.809)]
    block, tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "NEAR_TIE" in _codes(block)
    assert block["detected"] is True
    assert tie_ids == {"a", "b"}
    assert block["near_tie_group"] == ["a", "b"]


def test_near_tie_boundary_is_inclusive():
    candidates = [_candidate("a", 0.60), _candidate("b", 0.55)]  # gap exactly 0.05
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "NEAR_TIE" in _codes(block)


def test_near_tie_gap_just_outside_threshold_is_not_a_tie():
    candidates = [_candidate("a", 0.601), _candidate("b", 0.55)]  # gap 0.051
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "NEAR_TIE" not in _codes(block)


def test_near_tie_group_includes_three_way_cluster():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.78), _candidate("c", 0.76)]
    block, tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert tie_ids == {"a", "b", "c"}


def test_low_confidence_signal():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.30)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.5375, supporting_signals=2, any_evidence_incomplete=False)

    assert "LOW_CONFIDENCE" in _codes(block)
    assert block["detected"] is True


def test_confidence_at_threshold_is_not_low():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.30)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.55, supporting_signals=2, any_evidence_incomplete=False)

    assert "LOW_CONFIDENCE" not in _codes(block)


def test_insufficient_evidence_from_low_supporting_signals():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.30)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=0, any_evidence_incomplete=False)

    assert "INSUFFICIENT_EVIDENCE" in _codes(block)


def test_insufficient_evidence_from_incomplete_evidence_flag():
    candidates = [_candidate("a", 0.80), _candidate("b", 0.30)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=True)

    assert "INSUFFICIENT_EVIDENCE" in _codes(block)


def test_all_candidates_constrained_signal():
    candidates = [_candidate("a", 0.80, eligible=False), _candidate("b", 0.30, eligible=False)]
    block, tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "ALL_CANDIDATES_CONSTRAINED" in _codes(block)
    assert block["detected"] is True
    assert block["top_gap"] is None
    assert tie_ids == set()


def test_single_candidate_is_informational_only():
    candidates = [_candidate("only", 0.42)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=1, any_evidence_incomplete=False)

    assert "SINGLE_CANDIDATE" in _codes(block)
    assert block["detected"] is False  # single-candidate alone must not set detected
    assert block["top_gap"] is None


def test_exactly_one_eligible_candidate_has_no_near_tie():
    candidates = [_candidate("eligible_one", 0.80, eligible=True), _candidate("blocked", 0.90, eligible=False)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "NEAR_TIE" not in _codes(block)
    assert block["top_gap"] is None


def test_conflicting_objectives_requires_near_tie_and_opposing_favorites():
    impacts_a = {
        "financial_exposure_prevention": {"contribution": 0.30},
        "merchant_trust": {"contribution": 0.02},
    }
    impacts_b = {
        "financial_exposure_prevention": {"contribution": 0.10},
        "merchant_trust": {"contribution": 0.20},
    }
    candidates = [
        _candidate("a", 0.60, objective_impacts=impacts_a),
        _candidate("b", 0.58, objective_impacts=impacts_b),
    ]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "CONFLICTING_OBJECTIVES" in _codes(block)
    signal = next(s for s in block["signals"] if s["code"] == "CONFLICTING_OBJECTIVES")
    assert signal["detail"]["favoring_top"] == ["financial_exposure_prevention"]
    assert signal["detail"]["favoring_next"] == ["merchant_trust"]


def test_conflicting_objectives_absent_when_one_candidate_dominates_every_objective():
    impacts_a = {
        "financial_exposure_prevention": {"contribution": 0.30},
        "merchant_trust": {"contribution": 0.20},
    }
    impacts_b = {
        "financial_exposure_prevention": {"contribution": 0.10},
        "merchant_trust": {"contribution": 0.05},
    }
    candidates = [
        _candidate("a", 0.60, objective_impacts=impacts_a),
        _candidate("b", 0.58, objective_impacts=impacts_b),
    ]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.90, supporting_signals=2, any_evidence_incomplete=False)

    assert "CONFLICTING_OBJECTIVES" not in _codes(block)


def test_signals_are_sorted_by_code():
    candidates = [_candidate("a", 0.80, eligible=False), _candidate("b", 0.30, eligible=False)]
    block, _tie_ids = evaluate_ambiguity(candidates, AMBIGUITY_POLICY, case_confidence=0.10, supporting_signals=0, any_evidence_incomplete=False)

    codes = [s["code"] for s in block["signals"]]
    assert codes == sorted(codes)
