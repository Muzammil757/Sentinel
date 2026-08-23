from datetime import datetime


def generate_rto_action(
    order_id: str,
    customer_id: str,
    rto_score: float,
    shipment_status: str,
) -> dict:
    """
    Mock RTO/Fraud Agent.

    This agent only knows RTO/fraud-related information.
    It does not access payout, dispute, retention, or
    other agents' information.
    """

    if rto_score >= 0.75:
        proposed_action = "HOLD_ORDER"
        confidence = 0.95
    elif rto_score >= 0.50:
        proposed_action = "REVIEW_ORDER"
        confidence = 0.80
    else:
        proposed_action = "ALLOW_ORDER"
        confidence = 0.90

    return {
        "agent": "rto",
        "order_id": order_id,
        "customer_id": customer_id,
        "rto_score": rto_score,
        "shipment_status": shipment_status.upper(),
        "proposed_action": proposed_action,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }