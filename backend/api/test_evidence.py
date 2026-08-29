from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_evidence_exposes_agent_positions_and_scores(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    body = api_client.get("/api/cases/case-Q/evidence").json()

    agent_names = {a["agent_name"] for a in body["agents"]}
    assert agent_names == {"payouts", "dispute"}
    assert body["conflict"]["conflict"] is True
    assert len(body["candidates"]) >= 1
    for candidate in body["candidates"]:
        assert candidate["score"]["total_score"] is not None
    assert body["weigh_result"]["profile_name"] == "standard"
