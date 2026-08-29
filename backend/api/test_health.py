def test_health_reports_ok_application_status(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["application"]["status"] == "ok"


def test_health_distinguishes_application_from_database(api_client):
    body = api_client.get("/api/health").json()
    assert "application" in body and "database" in body
    assert body["application"] != body["database"]


def test_health_does_not_leak_credentials(api_client):
    body = api_client.get("/api/health").json()
    text = str(body)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in text
    assert "supabase.co" not in text
