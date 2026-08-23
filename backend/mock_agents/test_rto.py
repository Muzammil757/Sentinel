from rto import generate_rto_action


def run_test():
    result = generate_rto_action(
        order_id="ORD-88213",
        customer_id="CUS-441",
        rto_score=0.91,
        shipment_status="in_transit",
    )

    assert result["agent"] == "rto"
    assert result["order_id"] == "ORD-88213"
    assert result["customer_id"] == "CUS-441"
    assert result["rto_score"] == 0.91
    assert result["shipment_status"] == "IN_TRANSIT"
    assert result["proposed_action"] == "HOLD_ORDER"
    assert result["confidence"] == 0.95

    print("RTO Agent test passed.")


if __name__ == "__main__":
    run_test()