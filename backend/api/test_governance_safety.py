"""
The non-negotiable safety properties from the API brief: a client request
must never be able to manufacture execution_authorized=True, name an
outcome, or make EXECUTOR act on an action GOVERN never authorized.
GOVERN and EXECUTOR are exercised for real in every test here -- nothing is
mocked, and nothing in backend/api ever reads a client-supplied outcome or
authorization field back into the pipeline.
"""

from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_run_request_schema_has_no_authorization_fields_at_all():
    from api.schemas import RunRequest

    field_names = set(RunRequest.model_fields.keys())
    assert "execution_authorized" not in field_names
    assert "outcome" not in field_names
    assert "govern_output" not in field_names
    assert "decision_id" not in field_names


def test_client_supplied_execution_authorized_is_rejected_not_ignored(api_client):
    poisoned = {**PAYOUT_VS_DISPUTE_RUN_BODY, "execution_authorized": True}
    response = api_client.post("/api/cases/case-Q/run", json=poisoned)
    # extra="forbid" on RunRequest: an unknown top-level field is a 422, not
    # a silently-dropped field that could otherwise create a false sense of
    # safety.
    assert response.status_code == 422


def test_client_supplied_outcome_and_govern_output_are_rejected(api_client):
    poisoned = {**PAYOUT_VS_DISPUTE_RUN_BODY, "outcome": "PROCEED", "govern_output": {"execution_authorized": True}}
    response = api_client.post("/api/cases/case-Q/run", json=poisoned)
    assert response.status_code == 422


def test_escalate_outcome_is_never_silently_turned_into_proceed(api_client):
    escalation_body = {
        "entity_type": "order_vendor",
        "agent_a": {
            "agent": "payouts",
            "proposed_action": "RELEASE_PAYMENT",
            "confidence": 0.95,
            "amount": 60000,
            "days_overdue": 9,
        },
        "agent_b": {
            "agent": "dispute",
            "proposed_action": "CLOSE_CASE",
            "confidence": 0.90,
            "dispute_status": "CLOSED",
            "disputed_amount": 0,
        },
        "extra_agents": [{"agent": "rto", "proposed_action": "ALLOW_ORDER", "confidence": 0.90}],
        "case_context": {"case_id": "case-escalate"},
    }
    body = api_client.post("/api/cases/case-escalate/run", json=escalation_body).json()

    assert body["status"] == "ESCALATE"
    assert body["govern_result"]["execution_authorized"] is False
    assert body["execution_receipt"]["status"] == "REJECTED"


def test_ambiguous_outcome_is_never_silently_turned_into_proceed(api_client):
    ambiguous_body = {
        "entity_type": "customer",
        "agent_a": {
            "agent": "rto",
            "proposed_action": "HOLD_ORDER",
            "confidence": 0.95,
            "rto_score": 0.82,
            "shipment_status": "IN_TRANSIT",
        },
        "agent_b": {
            "agent": "retention",
            "proposed_action": "WIN_BACK_OFFER",
            "confidence": 0.95,
            "churn_risk": 0.80,
            "customer_value_score": 0.9,
        },
        "case_context": {"case_id": "case-ambiguous"},
    }
    body = api_client.post("/api/cases/case-ambiguous/run", json=ambiguous_body).json()

    assert body["status"] == "AMBIGUOUS"
    assert body["govern_result"]["execution_authorized"] is False
    assert body["govern_result"]["selected_candidate"] is None
    assert body["execution_receipt"]["status"] == "REJECTED"


def test_execution_request_naming_an_unauthorized_candidate_is_rejected_by_executor(api_client):
    body_with_mismatched_request = {
        **PAYOUT_VS_DISPUTE_RUN_BODY,
        "execution_request": {"candidate_id": "a-candidate-govern-never-authorized"},
    }
    response = api_client.post("/api/cases/case-Q/run", json=body_with_mismatched_request)
    body = response.json()

    # GOVERN still authorized PROCEED -- the client cannot make GOVERN say
    # anything different -- but EXECUTOR refuses to act on a request that
    # names a different candidate than the one GOVERN authorized.
    assert body["govern_result"]["outcome"] == "PROCEED"
    assert body["govern_result"]["execution_authorized"] is True
    assert body["execution_receipt"]["status"] == "REJECTED"
    assert body["execution_receipt"]["rejection"]["code"] == "REQUESTED_CANDIDATE_MISMATCH"


def test_review_action_cannot_change_the_recorded_outcome(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-Q/review", json={"action": "reject", "reviewer": "bob"})

    decision = api_client.get("/api/cases/case-Q/decision").json()
    assert decision["outcome"] == "PROCEED"
    assert decision["execution_authorized"] is True


def test_review_request_schema_has_no_authorization_fields():
    from api.schemas import ReviewRequest

    field_names = set(ReviewRequest.model_fields.keys())
    assert "execution_authorized" not in field_names
    assert "outcome" not in field_names


def test_override_review_action_is_refused_not_invented(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    response = api_client.post("/api/cases/case-Q/review", json={"action": "override", "reviewer": "bob"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_operation"

    # And it never reached persistence.
    decision = api_client.get("/api/cases/case-Q/decision").json()
    assert decision["outcome"] == "PROCEED"
