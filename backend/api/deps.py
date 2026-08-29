"""
FastAPI dependency wiring: one lazily-created Supabase client shared by a
PersistenceStore and a CaseReader for the lifetime of the process, plus the
database-health check used by GET /api/health.

Route handlers depend on `get_store`/`get_reader`, never on
`persistence.connection.get_client` directly -- tests override these two
functions (`app.dependency_overrides[get_store] = ...`) to point at
`persistence.conftest.FakeSupabaseClient` instead of a live project, exactly
as the existing persistence test suite already does for its own tests.
"""

from __future__ import annotations

from functools import lru_cache
from time import monotonic

from persistence.connection import SupabaseConfigError, get_client
from persistence.reader import CaseReader
from persistence.store import PersistenceStore

_PROCESS_STARTED_AT = monotonic()


@lru_cache(maxsize=1)
def _cached_client():
    return get_client()


def get_store() -> PersistenceStore:
    return PersistenceStore(_cached_client())


def get_reader() -> CaseReader:
    return CaseReader(_cached_client())


def get_application_health() -> dict:
    """Application health only -- true whenever this process can answer at
    all. Never implies anything about the database."""

    return {"status": "ok", "uptime_seconds": round(monotonic() - _PROCESS_STARTED_AT, 3)}


def get_database_health() -> dict:
    """
    Persistence health, checked independently of application health.

    Three distinguishable states: "not_configured" (no Supabase credentials
    -- persistence.connection.get_client's own fail-safe path, per design),
    "error" (credentials present but the check itself failed), and "ok" (a
    real read succeeded). Never returns a URL, a key, or an exception's raw
    text -- persistence.connection's own SupabaseConfigError message already
    only names environment variable names, but this function still degrades
    the message defensively rather than trusting that stays true forever.
    """

    try:
        client = _cached_client()
    except SupabaseConfigError:
        return {"status": "not_configured", "detail": "Supabase credentials are not set."}

    try:
        client.table("cases").select("id").execute()
    except Exception:
        return {"status": "error", "detail": "The configured database could not be reached."}

    return {"status": "ok"}
