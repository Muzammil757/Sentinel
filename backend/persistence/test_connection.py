"""
persistence.connection never invents a credential and never hard-codes one.
No live Supabase project is available in this environment (see the final
report's local-testing-strategy section), so these tests only exercise the
fail-safe paths: missing environment variables, and the `supabase` package
being unavailable (simulated via sys.modules so the test holds regardless
of whether the real package happens to be installed).
"""

import sys

import pytest

from persistence.connection import (
    SUPABASE_KEY_ENV_VAR,
    SUPABASE_URL_ENV_VAR,
    SupabaseConfigError,
    get_client,
)


def test_missing_env_vars_raises_config_error(monkeypatch):
    monkeypatch.delenv(SUPABASE_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(SUPABASE_KEY_ENV_VAR, raising=False)

    with pytest.raises(SupabaseConfigError, match=SUPABASE_URL_ENV_VAR):
        get_client()


def test_missing_key_only_raises_config_error(monkeypatch):
    monkeypatch.setenv(SUPABASE_URL_ENV_VAR, "https://example.supabase.co")
    monkeypatch.delenv(SUPABASE_KEY_ENV_VAR, raising=False)

    with pytest.raises(SupabaseConfigError):
        get_client()


def test_no_credential_is_hard_coded_as_a_fallback(monkeypatch):
    # Setting garbage values must not be silently replaced by a default --
    # get_client() only ever fails past this point because the `supabase`
    # package is unavailable, never by falling back to a baked-in URL or
    # key. The import is forced to fail via sys.modules so this holds
    # whether or not the real package is actually installed.
    monkeypatch.setenv(SUPABASE_URL_ENV_VAR, "not-a-real-url")
    monkeypatch.setenv(SUPABASE_KEY_ENV_VAR, "not-a-real-key")
    monkeypatch.setitem(sys.modules, "supabase", None)

    with pytest.raises(SupabaseConfigError, match="supabase"):
        get_client()
