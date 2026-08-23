from matrix import check_conflict


def run_tests():
    # Scenario 1: known conflict
    result = check_conflict(
        "RELEASE_PAYMENT",
        "HOLD_RELATED_ACTIONS",
        "order_vendor",
    )
    assert result["conflict"] is True

    # Scenario 1: known no-op
    result = check_conflict(
        "RELEASE_PAYMENT",
        "CLOSE_CASE",
        "order_vendor",
    )
    assert result["conflict"] is False

    # Scenario 2: known conflict
    result = check_conflict(
        "HOLD_ORDER",
        "PRESERVE_EXPERIENCE",
        "customer",
    )
    assert result["conflict"] is True

    # Variant conflict
    result = check_conflict(
        "HOLD_ORDER",
        "WIN_BACK_OFFER",
        "customer",
    )
    assert result["conflict"] is True

    # Unknown pair
    result = check_conflict(
        "RELEASE_PAYMENT",
        "APPROVE",
        "order_vendor",
    )
    assert result["conflict"] is False

    print("All Conflict Matrix tests passed.")


if __name__ == "__main__":
    run_tests()