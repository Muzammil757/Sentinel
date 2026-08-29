from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_run_endpoint_invokes_the_real_pipeline_and_persists(api_client):
    response = api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    assert response.status_code == 200
    body = response.json()

    assert body["failed"] is False
    assert body["status"] == "PROCEED"
    assert body["govern_result"]["execution_authorized"] is True
    assert body["execution_receipt"]["status"] == "EXECUTED"
    assert body["govern_result"]["decision_id"].startswith("dec_")


def test_run_request_rejects_missing_required_agent_fields(api_client):
    bad_body = {
        "entity_type": "order_vendor",
        "agent_a": {"agent": "payouts", "confidence": 0.95},  # no proposed_action
        "agent_b": PAYOUT_VS_DISPUTE_RUN_BODY["agent_b"],
    }
    response = api_client.post("/api/cases/case-Q/run", json=bad_body)
    assert response.status_code == 422


def test_run_request_rejects_out_of_range_confidence(api_client):
    bad_body = {
        "entity_type": "order_vendor",
        "agent_a": {**PAYOUT_VS_DISPUTE_RUN_BODY["agent_a"], "confidence": 1.5},
        "agent_b": PAYOUT_VS_DISPUTE_RUN_BODY["agent_b"],
    }
    response = api_client.post("/api/cases/case-Q/run", json=bad_body)
    assert response.status_code == 422


def test_rerun_creates_a_new_run_never_overwrites_the_first(api_client, fake_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    assert len(fake_client.rows("cases")) == 1
    assert len(fake_client.rows("case_runs")) == 2
    assert len(fake_client.rows("govern_results")) == 2


def test_run_endpoint_reports_a_failed_run_without_raising_500(api_client):
    # Extra_agents lets a malformed evidence payload through validation with
    # a normal conflict pair, but a policy-incompatible amount type still
    # cannot slip past Pydantic's numeric confidence check -- so the HTTP
    # surface itself cannot reach WEIGH/GOVERN with unscoreable evidence
    # (see test_orchestrator.py for that failure path exercised directly).
    # This test instead confirms the run endpoint for a scenario that DOES
    # legitimately fail end to end: the Scenario Lab's pipeline_failure
    # fixture, reached through POST /api/scenarios/{id}/run.
    response = api_client.post("/api/scenarios/pipeline_failure/run")
    assert response.status_code == 200
    body = response.json()
    assert body["failed"] is True
    assert body["status"] == "FAILED"
    assert body["failed_stage"] == "CONFLICT_OR_RESOLVE"
