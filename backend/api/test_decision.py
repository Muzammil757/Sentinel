from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_decision_reflects_persisted_govern_output(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    response = api_client.get("/api/cases/case-Q/decision")
    assert response.status_code == 200
    body = response.json()

    assert body["outcome"] == "PROCEED"
    assert body["execution_authorized"] is True
    assert body["decision_id"].startswith("dec_")
    assert body["selected_candidate"] is not None
    assert body["authorized_actions"] == ["HOLD_RELATED_ACTIONS"]
    assert body["policy_hash"]
    assert body["raw_output"]["outcome"] == "PROCEED"
    # No fabricated fields.
    assert "confidence" not in body
    assert "reasoning" not in body


def test_decision_for_nonexistent_case_is_404(api_client):
    response = api_client.get("/api/cases/does-not-exist/decision")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_decision_for_case_with_no_runs_is_run_not_found(api_client, fake_client):
    from persistence.store import PersistenceStore

    store = PersistenceStore(fake_client)
    store.get_or_create_case("case-empty")

    response = api_client.get("/api/cases/case-empty/decision")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_decision_by_explicit_run_id_must_belong_to_case(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-R/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    case_q = next(c for c in api_client.get("/api/cases").json() if c["external_case_id"] == "case-Q")

    other_case_run_id = next(
        c["latest_run_id"] for c in api_client.get("/api/cases").json() if c["external_case_id"] == "case-R"
    )

    response = api_client.get(f"/api/cases/{case_q['case_id']}/decision?run_id={other_case_run_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"
