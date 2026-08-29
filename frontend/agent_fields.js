// Field definitions mirror backend/mock_agents/*.py exactly -- this UI
// invents no agent, field, or action the backend does not already accept
// through backend/api/schemas.py::RunRequest. proposed_action options are
// the exact values each mock agent generator can produce (backend/mock_agents/
// payouts.py, disputes.py, rto.py, retention.py); confidence stays a free
// 0..1 input because RunRequest validates it as any numeric in that range,
// not one fixed value per action.
const AGENT_TYPES = {
  payouts: {
    label: "Payouts",
    actions: ["RELEASE_PAYMENT"],
    defaultConfidence: 0.95,
    fields: [
      { name: "vendor_id", label: "Vendor ID", type: "text", placeholder: "vendor_123" },
      { name: "amount", label: "Amount", type: "number", step: "1", placeholder: "42000" },
      { name: "invoice_id", label: "Invoice ID", type: "text", placeholder: "inv_001" },
      { name: "days_overdue", label: "Days overdue", type: "number", step: "1", placeholder: "9" },
    ],
  },
  dispute: {
    label: "Dispute",
    actions: ["HOLD_RELATED_ACTIONS", "CLOSE_CASE"],
    defaultConfidence: 0.95,
    fields: [
      { name: "dispute_id", label: "Dispute ID", type: "text", placeholder: "dp_001" },
      { name: "order_id", label: "Order ID", type: "text", placeholder: "order_001" },
      {
        name: "dispute_status",
        label: "Dispute status",
        type: "select",
        options: ["OPEN", "UNDER_REVIEW", "CLOSED"],
      },
      { name: "disputed_amount", label: "Disputed amount", type: "number", step: "1", placeholder: "42000" },
    ],
  },
  rto: {
    label: "RTO / Fraud",
    actions: ["HOLD_ORDER", "REVIEW_ORDER", "ALLOW_ORDER"],
    defaultConfidence: 0.9,
    fields: [
      { name: "order_id", label: "Order ID", type: "text", placeholder: "order_002" },
      { name: "customer_id", label: "Customer ID", type: "text", placeholder: "cust_002" },
      { name: "rto_score", label: "RTO score (0-1)", type: "number", step: "0.01", placeholder: "0.82" },
      {
        name: "shipment_status",
        label: "Shipment status",
        type: "select",
        options: ["IN_TRANSIT", "DELIVERED", "PENDING"],
      },
    ],
  },
  retention: {
    label: "Retention",
    actions: ["WIN_BACK_OFFER", "RETENTION_MESSAGE", "NO_RETENTION_ACTION"],
    defaultConfidence: 0.9,
    fields: [
      { name: "customer_id", label: "Customer ID", type: "text", placeholder: "cust_002" },
      { name: "order_id", label: "Order ID", type: "text", placeholder: "order_002" },
      {
        name: "customer_value_score",
        label: "Customer value score (0-1)",
        type: "number",
        step: "0.01",
        placeholder: "0.9",
      },
      { name: "churn_risk", label: "Churn risk (0-1)", type: "number", step: "0.01", placeholder: "0.8" },
    ],
  },
};
