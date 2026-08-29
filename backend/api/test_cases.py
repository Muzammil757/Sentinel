from .conftest import PAYOUT_VS_DISPUTE_RUN_BODY


def test_list_cases_empty_initially(api_client):
    response = api_client.get("/api/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_get_nonexistent_case_returns_404_with_typed_error(api_client):
    response = api_client.get("/api/cases/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "case_not_found"


def test_get_case_with_syntactically_invalid_id_returns_404_not_502(api_client):
    # Regression test: against a real Postgres-backed project, a case_id that
    # isn't valid UUID syntax used to reach the `cases.id` (uuid) column
    # lookup and raise there, surfacing as 502 persistence_failure instead of
    # 404 case_not_found. CaseReader.get_case now guards against this before
    # any query is issued (see persistence/test_reader.py for the unit-level
    # proof); this test pins the HTTP-level contract.
    response = api_client.get("/api/cases/not-a-valid-uuid-at-all")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_get_case_with_well_formed_but_nonexistent_uuid_returns_404(api_client):
    response = api_client.get("/api/cases/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_run_then_list_and_get_case(api_client):
    run_response = api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["failed"] is False
    assert run_body["status"] == "PROCEED"

    cases = api_client.get("/api/cases").json()
    assert len(cases) == 1
    summary = cases[0]
    assert summary["external_case_id"] == "case-Q"
    assert summary["outcome"] == "PROCEED"
    assert summary["execution_authorized"] is True
    assert summary["executed"] is True
    assert summary["human_review_required"] is False

    detail = api_client.get(f"/api/cases/{summary['case_id']}").json()
    assert detail["case"]["external_case_id"] == "case-Q"
    assert len(detail["agents"]) == 2
    assert detail["conflict"]["conflict"] is True
    assert len(detail["candidates"]) >= 1
    assert all(c["score"] is not None for c in detail["candidates"])
    assert detail["govern_result"]["outcome"] == "PROCEED"
    assert detail["execution_receipt"]["status"] == "EXECUTED"
    assert len(detail["timeline"]) == 7  # RUN_STARTED..EXECUTOR_COMPLETED


def test_get_case_by_internal_id_when_case_has_no_runs(api_client, fake_client):
    from persistence.store import PersistenceStore

    store = PersistenceStore(fake_client)
    case = store.get_or_create_case("case-empty")

    detail = api_client.get(f"/api/cases/{case['id']}").json()
    assert detail["case"]["id"] == case["id"]
    assert detail["run"] is None
    assert detail["candidates"] == []
    assert detail["govern_result"] is None


def test_rerun_creates_a_second_run_and_case_list_shows_run_count(api_client):
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)
    api_client.post("/api/cases/case-Q/run", json=PAYOUT_VS_DISPUTE_RUN_BODY)

    cases = api_client.get("/api/cases").json()
    assert len(cases) == 1
    assert cases[0]["run_count"] == 2
