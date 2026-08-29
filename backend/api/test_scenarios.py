def test_list_scenarios_returns_the_curated_set(api_client):
    response = api_client.get("/api/scenarios")
    assert response.status_code == 200
    ids = {s["id"] for s in response.json()}
    assert ids == {
        "normal_payout_proceed",
        "agent_disagreement_hold",
        "authority_cap_escalation",
        "ambiguous_case",
        "executor_rejection",
        "pipeline_failure",
    }


def test_unknown_scenario_is_404(api_client):
    response = api_client.post("/api/scenarios/does-not-exist/run")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "scenario_not_found"


def test_normal_payout_scenario_proceeds_and_executes(api_client):
    body = api_client.post("/api/scenarios/normal_payout_proceed/run").json()
    assert body["status"] == "PROCEED"
    assert body["govern_result"]["execution_authorized"] is True
    assert body["execution_receipt"]["status"] == "EXECUTED"


def test_agent_disagreement_scenario_holds_for_review(api_client):
    body = api_client.post("/api/scenarios/agent_disagreement_hold/run").json()
    assert body["status"] == "HOLD"
    assert body["govern_result"]["execution_authorized"] is False
    assert body["execution_receipt"]["status"] == "REJECTED"


def test_authority_cap_scenario_escalates(api_client):
    body = api_client.post("/api/scenarios/authority_cap_escalation/run").json()
    assert body["status"] == "ESCALATE"
    assert body["govern_result"]["execution_authorized"] is False


def test_ambiguous_scenario_is_ambiguous(api_client):
    body = api_client.post("/api/scenarios/ambiguous_case/run").json()
    assert body["status"] == "AMBIGUOUS"
    assert body["govern_result"]["selected_candidate"] is None


def test_executor_rejection_scenario_authorizes_but_rejects_execution(api_client):
    body = api_client.post("/api/scenarios/executor_rejection/run").json()
    assert body["govern_result"]["outcome"] == "PROCEED"
    assert body["govern_result"]["execution_authorized"] is True
    assert body["execution_receipt"]["status"] == "REJECTED"
    assert body["execution_receipt"]["rejection"]["code"] == "REQUESTED_CANDIDATE_MISMATCH"


def test_pipeline_failure_scenario_fails_without_becoming_a_success(api_client):
    body = api_client.post("/api/scenarios/pipeline_failure/run").json()
    assert body["failed"] is True
    assert body["status"] == "FAILED"


def test_scenario_run_persists_through_the_real_store(api_client, fake_client):
    api_client.post("/api/scenarios/normal_payout_proceed/run")
    assert len(fake_client.rows("govern_results")) == 1
    assert len(fake_client.rows("execution_receipts")) == 1
    assert len(fake_client.rows("audit_events")) == 7
