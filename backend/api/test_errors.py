"""
Error-mapping tests, including the real-world case a live-Supabase smoke
test surfaced: a postgrest.exceptions.APIError (e.g. a table missing from
the schema cache) must map to a distinguishable "persistence_failure", not
an opaque 500 with no code a client could branch on.
"""

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from main import app

from .deps import get_reader


class _RaisingReader:
    def get_case(self, case_id):
        raise APIError(
            {
                "message": "Could not find the table 'public.human_reviews' in the schema cache",
                "code": "PGRST205",
                "hint": None,
                "details": None,
            }
        )


def test_postgrest_api_error_maps_to_persistence_failure_502():
    app.dependency_overrides[get_reader] = lambda: _RaisingReader()
    try:
        client = TestClient(app)
        response = client.get("/api/cases/anything")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "persistence_failure"
    # Never echoes the raw postgrest message (which could name a table/schema).
    assert "human_reviews" not in str(body)
    assert "schema cache" not in str(body)
