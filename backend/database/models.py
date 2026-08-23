from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from database.connection import Base


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    payment_terms_days = Column(Integer, nullable=False)


class Payment(Base):
    __tablename__ = "payments"

    payout_id = Column(String, primary_key=True)
    vendor_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    invoice_id = Column(String, nullable=False)
    days_overdue = Column(Integer, nullable=False)
    status = Column(String, nullable=False)


class Dispute(Base):
    __tablename__ = "disputes"

    case_id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    evidence_notes = Column(Text, nullable=True)
    opened_date = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    vendor_id = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    fulfillment_date = Column(String, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    subscription_tenure_months = Column(Integer, nullable=False)
    historical_avg_order_value = Column(Float, nullable=False)
    rto_history_count = Column(Integer, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"

    sub_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    active_campaign = Column(String, nullable=True)
    churn_risk_flag = Column(Boolean, nullable=False)


class RTOFlag(Base):
    __tablename__ = "rto_flags"

    flag_id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    pincode_risk_score = Column(Float, nullable=False)
    value_deviation_flag = Column(Boolean, nullable=False)


class SupportNote(Base):
    __tablename__ = "support_notes"

    note_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    order_id = Column(String, nullable=True)
    text = Column(Text, nullable=False)

class AgentAction(Base):
    __tablename__ = "agent_actions"

    action_id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    proposed_action = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_output_json = Column(Text, nullable=False)


class GovernanceDecision(Base):
    __tablename__ = "governance_decisions"

    decision_id = Column(String, primary_key=True)
    scenario = Column(String, nullable=False)
    action = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning_text = Column(Text, nullable=False)
    evidence_ids = Column(Text, nullable=False)
    human_approval_required = Column(Boolean, nullable=False)
    safety_override_applied = Column(Boolean, nullable=False)
    final_outcome = Column(String, nullable=False)

class EvalCase(Base):
    __tablename__ = "eval_cases"

    id = Column(Integer, primary_key=True, index=True)
    scenario = Column(String, nullable=False)
    ground_truth_action = Column(String, nullable=False)
    notes_on_why = Column(Text, nullable=True)