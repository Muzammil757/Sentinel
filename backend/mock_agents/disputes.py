from datetime import datetime


def generate_dispute_action(
    dispute_id: str,
    order_id: str,
    dispute_status: str,
    disputed_amount: float,
) -> dict:
    """
    Mock Dispute Agent.

    This agent only knows dispute-related information.
    It does not access payout, retention, RTO, or other
    agents' information.
    """

    if dispute_status.upper() in {"OPEN", "UNDER_REVIEW"}:
        proposed_action = "HOLD_RELATED_ACTIONS"
        confidence = 0.95
    else:
        proposed_action = "CLOSE_CASE"
        confidence = 0.90

    return {
        "agent": "dispute",
        "dispute_id": dispute_id,
        "order_id": order_id,
        "dispute_status": dispute_status.upper(),
        "disputed_amount": disputed_amount,
        "proposed_action": proposed_action,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }
    