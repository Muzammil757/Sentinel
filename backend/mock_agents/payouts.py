from datetime import datetime


def generate_payout_action(
    vendor_id: str,
    amount: float,
    invoice_id: str,
    days_overdue: int,
) -> dict:
    """
    Mock Payouts Agent.

    This agent only knows about payout-related information.
    It does not access disputes, customers, subscriptions,
    or any other agent's data.
    """

    proposed_action = "RELEASE_PAYMENT"

    confidence = 0.95 if days_overdue >= 7 else 0.85

    return {
        "agent": "payouts",
        "vendor_id": vendor_id,
        "amount": amount,
        "invoice_id": invoice_id,
        "days_overdue": days_overdue,
        "proposed_action": proposed_action,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }