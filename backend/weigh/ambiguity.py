"""
Deterministic ambiguity detection (design §J). WEIGH detects and reports;
GOVERN decides what an ambiguous case means. Nothing here selects an
outcome or a winning candidate.
"""


def _near_tie(eligible_ranked: list, threshold: float):
    if len(eligible_ranked) < 2:
        return False, None, []

    top_score = eligible_ranked[0]["total_score"]
    group = [c["candidate_id"] for c in eligible_ranked if top_score - c["total_score"] <= threshold]
    top_gap = round(top_score - eligible_ranked[1]["total_score"], 4)
    return len(group) >= 2, top_gap, group


def _conflicting_objectives(eligible_ranked: list, near_tie_threshold: float):
    if len(eligible_ranked) < 2:
        return None

    c1, c2 = eligible_ranked[0], eligible_ranked[1]
    gap = c1["total_score"] - c2["total_score"]
    if gap > near_tie_threshold:
        return None

    favoring_top = sorted(
        o for o in c1["objective_impacts"]
        if c1["objective_impacts"][o]["contribution"] > c2["objective_impacts"][o]["contribution"]
    )
    favoring_next = sorted(
        o for o in c1["objective_impacts"]
        if c2["objective_impacts"][o]["contribution"] > c1["objective_impacts"][o]["contribution"]
    )

    if favoring_top and favoring_next:
        return {
            "favoring_top": favoring_top,
            "favoring_next": favoring_next,
            "pair": [c1["candidate_id"], c2["candidate_id"]],
        }
    return None


def evaluate_ambiguity(
    evaluated_candidates: list,
    ambiguity_policy: dict,
    case_confidence: float,
    supporting_signals: int,
    any_evidence_incomplete: bool,
) -> tuple[dict, set]:
    """
    Returns (ambiguity_block, near_tie_group_ids). near_tie_group_ids lets
    the caller annotate each ranking entry's tie_group.
    """

    eligible = [c for c in evaluated_candidates if c["eligible"]]
    eligible_ranked = sorted(eligible, key=lambda c: (-c["total_score"], c["candidate_id"]))

    threshold = ambiguity_policy["near_tie_threshold"]
    near_tie_detected, top_gap, near_tie_group = _near_tie(eligible_ranked, threshold)

    signals = []

    if near_tie_detected:
        signals.append(
            {
                "code": "NEAR_TIE",
                "detail": {"top_gap": top_gap, "threshold": threshold, "members": sorted(near_tie_group)},
            }
        )

    low_confidence_threshold = ambiguity_policy["low_confidence_threshold"]
    if case_confidence < low_confidence_threshold:
        signals.append(
            {
                "code": "LOW_CONFIDENCE",
                "detail": {"case_confidence": case_confidence, "threshold": low_confidence_threshold},
            }
        )

    min_supporting_signals = ambiguity_policy["insufficient_evidence"]["min_supporting_signals"]
    if supporting_signals < min_supporting_signals or any_evidence_incomplete:
        signals.append(
            {
                "code": "INSUFFICIENT_EVIDENCE",
                "detail": {
                    "supporting_signals": supporting_signals,
                    "min_supporting_signals": min_supporting_signals,
                    "evidence_complete": not any_evidence_incomplete,
                },
            }
        )

    conflict_detail = _conflicting_objectives(eligible_ranked, threshold)
    if conflict_detail is not None:
        signals.append({"code": "CONFLICTING_OBJECTIVES", "detail": conflict_detail})

    if len(evaluated_candidates) > 0 and len(eligible) == 0:
        signals.append({"code": "ALL_CANDIDATES_CONSTRAINED", "detail": {}})

    if len(evaluated_candidates) == 1:
        # Informational only -- does not set `detected`. With one candidate
        # there is no comparison to be ambiguous about.
        signals.append({"code": "SINGLE_CANDIDATE", "detail": {}})

    detected = any(s["code"] != "SINGLE_CANDIDATE" for s in signals)
    signals_sorted = sorted(signals, key=lambda s: s["code"])

    ambiguity_block = {
        "detected": detected,
        "signals": signals_sorted,
        "near_tie_group": sorted(near_tie_group) if near_tie_detected else [],
        "top_gap": top_gap,
        "near_tie_threshold": threshold,
    }

    return ambiguity_block, (set(near_tie_group) if near_tie_detected else set())
