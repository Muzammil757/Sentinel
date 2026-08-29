"""
Shared API test fixtures: a FastAPI TestClient wired to
persistence.conftest.FakeSupabaseClient via dependency overrides, so every
API test exercises the real pipeline and the real PersistenceStore/
CaseReader against a deterministic in-memory database -- never a live
Supabase project, and never a mocked pipeline response.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

from persistence.conftest import FakeSupabaseClient
from persistence.reader import CaseReader
from persistence.store import PersistenceStore

from .deps import get_database_health, get_reader, get_store


@pytest.fixture
def fake_client():
    return FakeSupabaseClient()


def _fake_database_health(fake_client):
    def _check() -> dict:
        fake_client.table("cases").select("id").execute()
        return {"status": "ok"}

    return _check


@pytest.fixture
def api_client(fake_client):
    # Database health is overridden too, to a check against the same fake
    # client -- deterministic and network-free, while still exercising the
    # real "does a read succeed" logic rather than a hard-coded True.
    app.dependency_overrides[get_store] = lambda: PersistenceStore(fake_client)
    app.dependency_overrides[get_reader] = lambda: CaseReader(fake_client)
    app.dependency_overrides[get_database_health] = _fake_database_health(fake_client)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


PAYOUT_VS_DISPUTE_RUN_BODY = {
    "entity_type": "order_vendor",
    "agent_a": {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.95,
        "amount": 42000,
        "days_overdue": 9,
    },
    "agent_b": {
        "agent": "dispute",
        "proposed_action": "HOLD_RELATED_ACTIONS",
        "confidence": 0.95,
        "dispute_status": "OPEN",
        "disputed_amount": 42000,
    },
    "case_context": {"case_id": "case-Q", "merchant_id": "mrch_001"},
}
