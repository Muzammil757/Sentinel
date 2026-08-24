from mock_agents.retention import generate_retention_action


def test_generate_retention_action():
    result = generate_retention_action(
        customer_id="CUS-441",
        order_id="ORD-88213",
        customer_value_score=0.92,
        churn_risk=0.88,
    )

    assert result["agent"] == "retention"
    assert result["customer_id"] == "CUS-441"
    assert result["order_id"] == "ORD-88213"
    assert result["customer_value_score"] == 0.92
    assert result["churn_risk"] == 0.88
    assert result["proposed_action"] == "WIN_BACK_OFFER"
    assert result["confidence"] == 0.95
