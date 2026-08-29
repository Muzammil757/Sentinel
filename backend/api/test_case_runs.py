from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_list_case_runs_for_nonexistent_case_is_404(api_client):
    response = api_client.get("/api/cases/does-not-exist/runs")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_list_case_runs_empty_for_case_with_no_runs(api_client, fake_client):
    from persistence.store import PersistenceStore

    store = PersistenceStore(fake_client)
    store.get_or_create_case("case-empty")

    response = api_client.get("/api/cases/case-empty/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_list_case_runs_returns_newest_first_with_outcome_and_executed(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    runs = api_client.get("/api/cases/case-Q/runs").json()

    assert len(runs) == 2
    assert runs[0]["created_at"] >= runs[1]["created_at"]
    for run in runs:
        assert run["status"] == "PROCEED"
        assert run["outcome"] == "PROCEED"
        assert run["executed"] is True
        assert run["entity_type"] == "order_vendor"
        assert "case_run_id" in run


def test_list_case_runs_accepts_internal_or_external_case_id(api_client):
    run_response = api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    case_id = run_response.json()["case_id"]

    by_internal = api_client.get(f"/api/cases/{case_id}/runs").json()
    by_external = api_client.get("/api/cases/case-Q/runs").json()

    assert by_internal == by_external
