from mock_agents.payouts import generate_payout_action


def test_generate_payout_action():
    result = generate_payout_action(
        vendor_id="V-104",
        amount=400000,
        invoice_id="INV-3391",
        days_overdue=14,
    )

    assert result["agent"] == "payouts"
    assert result["proposed_action"] == "RELEASE_PAYMENT"
    assert result["vendor_id"] == "V-104"
    assert result["amount"] == 400000
    assert result["invoice_id"] == "INV-3391"
    assert result["days_overdue"] == 14
    assert result["confidence"] == 0.95
