from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_reliability_with_no_runs_yet(api_client):
    body = api_client.get("/api/system/reliability").json()
    assert body["total_runs"] == 0
    assert body["executed_count"] == 0
    assert body["rejected_count"] == 0
    assert body["runs_missing_audit_trail"] == 0
    assert "generated_at" in body


def test_reliability_reflects_real_runs(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/scenarios/authority_cap_escalation/run")

    body = api_client.get("/api/system/reliability").json()
    assert body["total_runs"] == 2
    assert body["executed_count"] == 1
    assert body["rejected_count"] == 1
    assert body["runs_by_status"]["PROCEED"] == 1
    assert body["runs_by_status"]["ESCALATE"] == 1
    assert body["runs_missing_audit_trail"] == 0
    assert len(body["recent_runs"]) == 2


def test_reliability_never_hard_codes_a_test_count(api_client):
    body = api_client.get("/api/system/reliability").json()
    assert "total_tests" not in body
    assert "562" not in str(body)
