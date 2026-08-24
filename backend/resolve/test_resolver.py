from resolve.resolver import generate_resolution_candidates


def test_no_conflict_passthrough():
    conflict_result = {
        "agent_a": "payouts",
        "agent_b": "dispute",
        "action_a": "RELEASE_PAYMENT",
        "action_b": "CLOSE_CASE",
        "entity_type": "order_vendor",
        "conflict": False,
        "reason": "Closed dispute case creates no active payment conflict.",
    }
    action_a_detail = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT"}
    action_b_detail = {"agent": "dispute", "proposed_action": "CLOSE_CASE"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    assert result["unresolved"] is False
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["strategy"] == "NO_CONFLICT_PROCEED"
    assert set(candidate["resulting_actions"]) == {"RELEASE_PAYMENT", "CLOSE_CASE"}


def test_known_conflict_release_payment_vs_hold():
    conflict_result = {
        "agent_a": "payouts",
        "agent_b": "dispute",
        "action_a": "RELEASE_PAYMENT",
        "action_b": "HOLD_RELATED_ACTIONS",
        "entity_type": "order_vendor",
        "conflict": True,
        "reason": "Payment release overlaps with a dispute-related hold.",
    }
    action_a_detail = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT"}
    action_b_detail = {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    assert result["unresolved"] is False
    assert len(result["candidates"]) > 0
    defer_candidates = [c for c in result["candidates"] if c["strategy"] == "DEFER_TO_AGENT"]
    assert len(defer_candidates) == 1
    assert defer_candidates[0]["preferred_agent"] == "dispute"


def test_known_conflict_hold_order_vs_winback():
    conflict_result = {
        "agent_a": "rto",
        "agent_b": "retention",
        "action_a": "HOLD_ORDER",
        "action_b": "WIN_BACK_OFFER",
        "entity_type": "customer",
        "conflict": True,
        "reason": "Order hold may conflict with a retention win-back action.",
    }
    action_a_detail = {"agent": "rto", "proposed_action": "HOLD_ORDER"}
    action_b_detail = {"agent": "retention", "proposed_action": "WIN_BACK_OFFER"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    defer_candidates = [c for c in result["candidates"] if c["strategy"] == "DEFER_TO_AGENT"]
    assert len(defer_candidates) == 1
    assert defer_candidates[0]["preferred_agent"] == "rto"


def test_unmatched_conflict_falls_back_to_hold_for_review():
    conflict_result = {
        "agent_a": "payouts",
        "agent_b": "rto",
        "action_a": "RELEASE_PAYMENT",
        "action_b": "REVIEW_ORDER",
        "entity_type": "order_vendor",
        "conflict": True,
        "reason": "No known conflict rule matched.",
    }
    action_a_detail = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT"}
    action_b_detail = {"agent": "rto", "proposed_action": "REVIEW_ORDER"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    assert result["unresolved"] is True
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["strategy"] == "HOLD_BOTH_PENDING_REVIEW"


def test_output_never_contains_a_final_decision():
    conflict_result = {
        "agent_a": "payouts",
        "agent_b": "dispute",
        "action_a": "RELEASE_PAYMENT",
        "action_b": "HOLD_RELATED_ACTIONS",
        "entity_type": "order_vendor",
        "conflict": True,
        "reason": "Payment release overlaps with a dispute-related hold.",
    }
    action_a_detail = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT"}
    action_b_detail = {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    forbidden_keys = {"final_action", "decision", "selected_candidate"}
    assert forbidden_keys.isdisjoint(result.keys())
    for candidate in result["candidates"]:
        assert forbidden_keys.isdisjoint(candidate.keys())


def test_candidate_ids_unique_within_output():
    conflict_result = {
        "agent_a": "payouts",
        "agent_b": "dispute",
        "action_a": "RELEASE_PAYMENT",
        "action_b": "HOLD_RELATED_ACTIONS",
        "entity_type": "order_vendor",
        "conflict": True,
        "reason": "Payment release overlaps with a dispute-related hold.",
    }
    action_a_detail = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT"}
    action_b_detail = {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS"}

    result = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    candidate_ids = [c["candidate_id"] for c in result["candidates"]]
    assert len(candidate_ids) == len(set(candidate_ids))


def test_deterministic_repeated_calls():
    conflict_result = {
        "agent_a": "rto",
        "agent_b": "retention",
        "action_a": "HOLD_ORDER",
        "action_b": "WIN_BACK_OFFER",
        "entity_type": "customer",
        "conflict": True,
        "reason": "Order hold may conflict with a retention win-back action.",
    }
    action_a_detail = {"agent": "rto", "proposed_action": "HOLD_ORDER"}
    action_b_detail = {"agent": "retention", "proposed_action": "WIN_BACK_OFFER"}

    result_1 = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)
    result_2 = generate_resolution_candidates(conflict_result, action_a_detail, action_b_detail)

    assert result_1 == result_2
