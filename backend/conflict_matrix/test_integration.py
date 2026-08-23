from integration import evaluate_agent_actions


def run_tests():
    # Scenario 1:
    # Payouts wants to release payment.
    # Dispute wants to hold related actions.
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

    # Scenario 2:
    # RTO wants to hold the order.
    # Retention wants to send a win-back offer.
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

    print("Conflict Matrix integration tests passed.")


if __name__ == "__main__":
    run_tests()