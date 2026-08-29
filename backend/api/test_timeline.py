from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_timeline_events_are_in_chronological_order(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    body = api_client.get("/api/cases/case-Q/timeline").json()

    assert [e["stage"] for e in body["events"]] == [
        "RUN_STARTED",
        "AGENTS_RECORDED",
        "CONFLICT_EVALUATED",
        "RESOLVE_COMPLETED",
        "WEIGH_COMPLETED",
        "GOVERN_DECIDED",
        "EXECUTOR_COMPLETED",
    ]
    assert all(e["outcome"] == "SUCCEEDED" for e in body["events"])
    assert body["human_reviews"] == []


def test_timeline_for_nonexistent_case_is_404(api_client):
    response = api_client.get("/api/cases/does-not-exist/timeline")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_timeline_includes_recorded_human_reviews(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-Q/review", json={"action": "approve", "reviewer": "alice"})

    body = api_client.get("/api/cases/case-Q/timeline").json()
    assert len(body["human_reviews"]) == 1
    assert body["human_reviews"][0]["action"] == "approve"
