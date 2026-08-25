"""
persistence.connection never invents a credential and never hard-codes one.
No live Supabase project is available in this environment (see the final
report's local-testing-strategy section), so these tests only exercise the
fail-safe paths: missing environment variables, and the real, unmocked
absence of the `supabase` package from this project's dependencies today.
"""

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
    # get_client() only ever fails past this point on the (real, currently
    # true) absence of the `supabase` package, never by falling back to a
    # baked-in URL or key.
    monkeypatch.setenv(SUPABASE_URL_ENV_VAR, "not-a-real-url")
    monkeypatch.setenv(SUPABASE_KEY_ENV_VAR, "not-a-real-key")

    with pytest.raises(SupabaseConfigError, match="supabase"):
        get_client()
