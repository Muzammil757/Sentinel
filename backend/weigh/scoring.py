from weigh.errors import WeighPolicyError


def select_impact_vector(candidate: dict, scoring_policy: dict) -> tuple[dict, dict]:
    """
    Design §F step 1: the candidate's raw objective vector is the
    element-wise minimum over its resulting_actions' vectors (the most
    conservative signal governs); the strategy vector is used only when
    resulting_actions is empty.

    Returns (raw_by_objective, source_by_objective), where source records
    which action (or the strategy) contributed each objective's value.
    """

    resulting_actions = candidate["resulting_actions"]
    action_effects = scoring_policy["action_effects"]
    strategy_effects = scoring_policy["strategy_effects"]

    if resulting_actions:
        vectors = []
        for action in resulting_actions:
            vector = action_effects.get(action)
            if vector is None:
                raise WeighPolicyError(
                    f"No scoring.action_effects entry for action {action!r} "
                    f"referenced by candidate {candidate['candidate_id']!r}"
                )
            vectors.append((action, vector))

        objective_names = vectors[0][1].keys()
        raw = {}
        source = {}
        for objective in objective_names:
            winning_action, winning_value = min(
                ((action, vector[objective]) for action, vector in vectors),
                key=lambda pair: pair[1],
            )
            raw[objective] = winning_value
            source[objective] = f"action:{winning_action}"
        return raw, source

    strategy = candidate["strategy"]
    vector = strategy_effects.get(strategy)
    if vector is None:
        raise WeighPolicyError(
            f"No scoring.strategy_effects entry for strategy {strategy!r} "
            f"referenced by candidate {candidate['candidate_id']!r}"
        )
    raw = dict(vector)
    source = {objective: f"strategy:{strategy}" for objective in vector}
    return raw, source


def score_candidate(candidate: dict, scoring_policy: dict, weights: dict) -> tuple[dict, float]:
    """
    Design §F steps 2-4: normalize each raw value to [0,1], weight it by the
    selected profile, sum. Contributions are rounded to 4dp first, and the
    total is the rounded sum of those rounded contributions -- so a receipt
    reader's arithmetic (sum the displayed contributions) always matches
    the displayed total exactly.
    """

    raw, source = select_impact_vector(candidate, scoring_policy)

    objective_impacts = {}
    for objective in sorted(raw.keys()):
        raw_value = raw[objective]
        normalized = round((raw_value + 1.0) / 2.0, 4)
        weight = weights[objective]
        contribution = round(weight * normalized, 4)
        objective_impacts[objective] = {
            "raw": raw_value,
            "normalized": normalized,
            "weight": weight,
            "contribution": contribution,
            "source": source[objective],
        }

    total_score = round(sum(v["contribution"] for v in objective_impacts.values()), 4)
    return objective_impacts, total_score


def build_ranking(evaluated_candidates: list) -> list:
    """
    Design §E.4: sort eligible candidates before ineligible ones, then by
    total_score descending, then by candidate_id for a stable tiebreak.
    score_rank is computed independently (pure score order) so a blocked
    top-scorer still shows its true score rank in the receipt.
    """

    score_sorted = sorted(
        evaluated_candidates, key=lambda c: (-c["total_score"], c["candidate_id"])
    )
    score_rank = {c["candidate_id"]: i + 1 for i, c in enumerate(score_sorted)}

    eligible_sorted = sorted(
        evaluated_candidates,
        key=lambda c: (not c["eligible"], -c["total_score"], c["candidate_id"]),
    )

    ranking = []
    for i, c in enumerate(eligible_sorted):
        ranking.append(
            {
                "candidate_id": c["candidate_id"],
                "rank": i + 1,
                "score_rank": score_rank[c["candidate_id"]],
                "total_score": c["total_score"],
                "eligible": c["eligible"],
                "tie_group": None,
            }
        )
    return ranking
