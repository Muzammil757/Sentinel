from mock_agents.disputes import generate_dispute_action


def test_generate_dispute_action():
    result = generate_dispute_action(
        dispute_id="DSP-7742",
        order_id="ORD-88213",
        dispute_status="open",
        disputed_amount=400000,
    )

    assert result["agent"] == "dispute"
    assert result["dispute_id"] == "DSP-7742"
    assert result["order_id"] == "ORD-88213"
    assert result["dispute_status"] == "OPEN"
    assert result["disputed_amount"] == 400000
    assert result["proposed_action"] == "HOLD_RELATED_ACTIONS"
    assert result["confidence"] == 0.95
