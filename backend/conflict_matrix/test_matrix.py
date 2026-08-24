from conflict_matrix.matrix import check_conflict


def test_known_conflict_release_payment_vs_hold_related_actions():
    result = check_conflict(
        "RELEASE_PAYMENT",
        "HOLD_RELATED_ACTIONS",
        "order_vendor",
    )
    assert result["conflict"] is True


def test_known_no_conflict_release_payment_vs_close_case():
    result = check_conflict(
        "RELEASE_PAYMENT",
        "CLOSE_CASE",
        "order_vendor",
    )
    assert result["conflict"] is False


def test_known_conflict_hold_order_vs_preserve_experience():
    result = check_conflict(
        "HOLD_ORDER",
        "PRESERVE_EXPERIENCE",
        "customer",
    )
    assert result["conflict"] is True


def test_known_conflict_hold_order_vs_win_back_offer():
    result = check_conflict(
        "HOLD_ORDER",
        "WIN_BACK_OFFER",
        "customer",
    )
    assert result["conflict"] is True


def test_unknown_pair_defaults_to_no_conflict():
    result = check_conflict(
        "RELEASE_PAYMENT",
        "APPROVE",
        "order_vendor",
    )
    assert result["conflict"] is False
