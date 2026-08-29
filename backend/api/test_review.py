from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_approve_review_is_recorded_and_auditable(api_client, fake_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    response = api_client.post(
        "/api/cases/case-Q/review", json={"action": "approve", "reviewer": "alice", "reason": "looks correct"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "approve"
    assert body["reviewer"] == "alice"
    assert "does not" in body["note"].lower()

    rows = fake_client.rows("human_reviews")
    assert len(rows) == 1
    assert rows[0]["action"] == "approve"
    assert rows[0]["case_run_status_at_review"] == "PROCEED"


def test_reject_and_request_more_evidence_are_supported(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    for action in ("reject", "request_more_evidence"):
        response = api_client.post("/api/cases/case-Q/review", json={"action": action})
        assert response.status_code == 200
        assert response.json()["action"] == action


def test_review_for_nonexistent_case_is_404(api_client):
    response = api_client.post("/api/cases/does-not-exist/review", json={"action": "approve"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_review_for_case_with_no_runs_is_run_not_found(api_client, fake_client):
    from persistence.store import PersistenceStore

    PersistenceStore(fake_client).get_or_create_case("case-empty")
    response = api_client.post("/api/cases/case-empty/review", json={"action": "approve"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_review_rejects_unknown_action(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    response = api_client.post("/api/cases/case-Q/review", json={"action": "delete_everything"})
    assert response.status_code == 422
