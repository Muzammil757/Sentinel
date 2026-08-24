import pytest

from policy.loader import load_policy
from weigh.errors import WeighPolicyError
from weigh.scoring import build_ranking, score_candidate, select_impact_vector

SCORING = load_policy()["scoring"]
STANDARD_WEIGHTS = load_policy()["weights"]["profiles"]["standard"]


def test_single_action_candidate_uses_action_vector_directly():
    candidate = {
        "candidate_id": "c1",
        "strategy": "DEFER_TO_AGENT",
        "resulting_actions": ["HOLD_RELATED_ACTIONS"],
    }

    raw, source = select_impact_vector(candidate, SCORING)

    assert raw == SCORING["action_effects"]["HOLD_RELATED_ACTIONS"]
    assert all(v == "action:HOLD_RELATED_ACTIONS" for v in source.values())


def test_no_action_candidate_uses_strategy_vector():
    candidate = {
        "candidate_id": "c2",
        "strategy": "HOLD_BOTH_PENDING_REVIEW",
        "resulting_actions": [],
    }

    raw, source = select_impact_vector(candidate, SCORING)

    assert raw == SCORING["strategy_effects"]["HOLD_BOTH_PENDING_REVIEW"]
    assert all(v == "strategy:HOLD_BOTH_PENDING_REVIEW" for v in source.values())


def test_multi_action_candidate_takes_elementwise_minimum():
    # RELEASE_PAYMENT and CLOSE_CASE, per-objective minimum should be
    # taken independently -- design §Q.4.
    candidate = {
        "candidate_id": "c3",
        "strategy": "NO_CONFLICT_PROCEED",
        "resulting_actions": ["RELEASE_PAYMENT", "CLOSE_CASE"],
    }

    raw, source = select_impact_vector(candidate, SCORING)

    release = SCORING["action_effects"]["RELEASE_PAYMENT"]
    close = SCORING["action_effects"]["CLOSE_CASE"]
    for objective in raw:
        assert raw[objective] == min(release[objective], close[objective])

    # Different actions can win different objectives.
    assert source["financial_exposure_prevention"] == "action:RELEASE_PAYMENT"
    assert source["merchant_trust"] == "action:CLOSE_CASE"


def test_multi_action_minimum_is_not_diluted_by_a_benign_action():
    # A risky action bundled with a benign one must not have its risk
    # diluted -- the conservative (lower) value always wins per objective.
    candidate = {
        "candidate_id": "c4",
        "strategy": "NO_CONFLICT_PROCEED",
        "resulting_actions": ["RELEASE_PAYMENT", "HOLD_RELATED_ACTIONS"],
    }

    raw, _source = select_impact_vector(candidate, SCORING)

    assert raw["financial_exposure_prevention"] == SCORING["action_effects"]["RELEASE_PAYMENT"][
        "financial_exposure_prevention"
    ]


def test_unmapped_action_raises_policy_error():
    candidate = {"candidate_id": "c5", "strategy": "DEFER_TO_AGENT", "resulting_actions": ["NOT_A_REAL_ACTION"]}

    with pytest.raises(WeighPolicyError):
        select_impact_vector(candidate, SCORING)


def test_unmapped_strategy_raises_policy_error():
    candidate = {"candidate_id": "c6", "strategy": "NOT_A_REAL_STRATEGY", "resulting_actions": []}

    with pytest.raises(WeighPolicyError):
        select_impact_vector(candidate, SCORING)


def test_normalization_maps_impact_scale_to_unit_interval():
    candidate = {"candidate_id": "c7", "strategy": "DEFER_TO_AGENT", "resulting_actions": ["HOLD_ORDER"]}

    objective_impacts, total_score = score_candidate(candidate, SCORING, STANDARD_WEIGHTS)

    for detail in objective_impacts.values():
        assert 0.0 <= detail["normalized"] <= 1.0
        assert detail["normalized"] == round((detail["raw"] + 1.0) / 2.0, 4)
    assert 0.0 <= total_score <= 1.0


def test_contributions_sum_exactly_to_total_score():
    candidate = {"candidate_id": "c8", "strategy": "DEFER_TO_AGENT", "resulting_actions": ["WIN_BACK_OFFER"]}

    objective_impacts, total_score = score_candidate(candidate, SCORING, STANDARD_WEIGHTS)

    assert round(sum(v["contribution"] for v in objective_impacts.values()), 4) == total_score


def test_higher_is_always_better_including_operational_cost():
    # operational_cost is "minimize overhead" -- a costly action (e.g. the
    # HOLD_BOTH_PENDING_REVIEW strategy) must score LOW on operational_cost,
    # not high, even though the raw label says "cost".
    candidate = {"candidate_id": "c9", "strategy": "HOLD_BOTH_PENDING_REVIEW", "resulting_actions": []}

    objective_impacts, _total = score_candidate(candidate, SCORING, STANDARD_WEIGHTS)

    assert objective_impacts["operational_cost"]["raw"] < 0
    assert objective_impacts["operational_cost"]["normalized"] < 0.5


def test_objective_keys_are_sorted_alphabetically():
    candidate = {"candidate_id": "c10", "strategy": "DEFER_TO_AGENT", "resulting_actions": ["HOLD_ORDER"]}

    objective_impacts, _total = score_candidate(candidate, SCORING, STANDARD_WEIGHTS)

    assert list(objective_impacts.keys()) == sorted(objective_impacts.keys())


def test_weight_sum_of_one_bounds_total_score_to_unit_interval():
    for action in SCORING["action_effects"]:
        candidate = {"candidate_id": "x", "strategy": "DEFER_TO_AGENT", "resulting_actions": [action]}
        _impacts, total = score_candidate(candidate, SCORING, STANDARD_WEIGHTS)
        assert 0.0 <= total <= 1.0


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _evaluated(candidate_id, total_score, eligible):
    return {"candidate_id": candidate_id, "total_score": total_score, "eligible": eligible}


def test_ranking_orders_by_score_descending_when_all_eligible():
    candidates = [
        _evaluated("low", 0.30, True),
        _evaluated("high", 0.90, True),
        _evaluated("mid", 0.60, True),
    ]

    ranking = build_ranking(candidates)

    assert [r["candidate_id"] for r in ranking] == ["high", "mid", "low"]
    assert [r["score_rank"] for r in ranking] == [1, 2, 3]


def test_ranking_never_places_a_constrained_candidate_first():
    candidates = [
        _evaluated("blocked_best_score", 0.95, False),
        _evaluated("eligible_lower_score", 0.50, True),
    ]

    ranking = build_ranking(candidates)

    assert ranking[0]["candidate_id"] == "eligible_lower_score"
    assert ranking[0]["eligible"] is True


def test_ranking_preserves_score_rank_for_constrained_candidate():
    candidates = [
        _evaluated("blocked_best_score", 0.95, False),
        _evaluated("eligible_lower_score", 0.50, True),
    ]

    ranking = build_ranking(candidates)
    blocked = next(r for r in ranking if r["candidate_id"] == "blocked_best_score")

    assert blocked["score_rank"] == 1
    assert blocked["eligible"] is False
    assert blocked["rank"] == 2  # last, despite highest score_rank


def test_ranking_tiebreak_is_candidate_id():
    candidates = [
        _evaluated("zzz", 0.50, True),
        _evaluated("aaa", 0.50, True),
    ]

    ranking = build_ranking(candidates)

    assert [r["candidate_id"] for r in ranking] == ["aaa", "zzz"]
