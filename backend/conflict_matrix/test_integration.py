from conflict_matrix.integration import evaluate_agent_actions


def test_evaluate_agent_actions_payouts_vs_dispute_conflict():
    payouts_action = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
    }

    dispute_action = {
        "agent": "dispute",
        "proposed_action": "HOLD_RELATED_ACTIONS",
    }

    result = evaluate_agent_actions(
        payouts_action,
        dispute_action,
        "order_vendor",
    )

    assert result["conflict"] is True
    assert result["agent_a"] == "payouts"
    assert result["agent_b"] == "dispute"


def test_evaluate_agent_actions_rto_vs_retention_conflict():
    rto_action = {
        "agent": "rto",
        "proposed_action": "HOLD_ORDER",
    }

    retention_action = {
        "agent": "retention",
        "proposed_action": "WIN_BACK_OFFER",
    }

    result = evaluate_agent_actions(
        rto_action,
        retention_action,
        "customer",
    )

    assert result["conflict"] is True
    assert result["agent_a"] == "rto"
    assert result["agent_b"] == "retention"
