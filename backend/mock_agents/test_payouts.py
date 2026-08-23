from payouts import generate_payout_action


def run_test():
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

    print("Payouts Agent test passed.")


if __name__ == "__main__":
    run_test()