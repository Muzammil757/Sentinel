from datetime import datetime


def generate_retention_action(
    customer_id: str,
    order_id: str,
    customer_value_score: float,
    churn_risk: float,
) -> dict:
    """
    Mock Retention Agent.

    This agent only knows customer-retention information.
    It does not access payout, dispute, RTO, or other
    agents' information.
    """

    if churn_risk >= 0.75:
        proposed_action = "WIN_BACK_OFFER"
        confidence = 0.95
    elif churn_risk >= 0.50:
        proposed_action = "RETENTION_MESSAGE"
        confidence = 0.80
    else:
        proposed_action = "NO_RETENTION_ACTION"
        confidence = 0.90

    return {
        "agent": "retention",
        "customer_id": customer_id,
        "order_id": order_id,
        "customer_value_score": customer_value_score,
        "churn_risk": churn_risk,
        "proposed_action": proposed_action,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }