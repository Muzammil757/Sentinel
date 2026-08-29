"""
Unit tests for backend.api.deps's health-check logic in isolation --
mirrors persistence/test_connection.py's own stance: no live Supabase
project is exercised, only the fail-safe paths and a stubbed client.
"""

import pytest

from persistence.connection import SUPABASE_KEY_ENV_VAR, SUPABASE_URL_ENV_VAR

from . import deps


@pytest.fixture(autouse=True)
def _clear_client_cache():
    deps._cached_client.cache_clear()
    yield
    deps._cached_client.cache_clear()


def test_database_health_not_configured_without_credentials(monkeypatch):
    monkeypatch.delenv(SUPABASE_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(SUPABASE_KEY_ENV_VAR, raising=False)

    result = deps.get_database_health()

    assert result["status"] == "not_configured"
    assert SUPABASE_URL_ENV_VAR not in str(result)


def test_database_health_ok_when_read_succeeds(monkeypatch):
    class _StubClient:
        def table(self, name):
            class _T:
                def select(self, *_a):
                    return self

                def execute(self):
                    return None

            return _T()

    monkeypatch.setattr(deps, "get_client", lambda: _StubClient())
    monkeypatch.setenv(SUPABASE_URL_ENV_VAR, "https://example.supabase.co")
    monkeypatch.setenv(SUPABASE_KEY_ENV_VAR, "fake-key")

    assert deps.get_database_health() == {"status": "ok"}


def test_database_health_error_when_read_fails(monkeypatch):
    class _StubClient:
        def table(self, name):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(deps, "get_client", lambda: _StubClient())
    monkeypatch.setenv(SUPABASE_URL_ENV_VAR, "https://example.supabase.co")
    monkeypatch.setenv(SUPABASE_KEY_ENV_VAR, "fake-key")

    result = deps.get_database_health()
    assert result["status"] == "error"
    assert "connection refused" not in str(result)


def test_application_health_is_always_ok():
    result = deps.get_application_health()
    assert result["status"] == "ok"
    assert isinstance(result["uptime_seconds"], float)
