"""
Supabase connection factory.

Persistence never decides anything; this module's only job is to hand back a
client that talks to Supabase's Postgres via the service-role key, exactly as
docs/data_layer_design.md's RLS section describes: RLS ties INSERT to the service role
(the trusted backend), and SELECT to any authenticated caller. No RLS policy
in this design gates whether an action executes -- GOVERN already decided
that before persistence saw anything.

Credentials come from environment variables only:

    SUPABASE_URL                 the project's REST endpoint
    SUPABASE_SERVICE_ROLE_KEY    the service-role key (bypasses RLS, per design)

Nothing here hard-codes a URL, key, or default, and nothing here reads or
writes a secret to a log. The `supabase` package is imported lazily inside
get_client() -- not at module import time -- so every other module in this
package (and its whole test suite) works in an environment where the package
is not installed and no live Supabase project exists, which is the case in
this repository today.
"""

import os

SUPABASE_URL_ENV_VAR = "SUPABASE_URL"
SUPABASE_KEY_ENV_VAR = "SUPABASE_SERVICE_ROLE_KEY"


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase credentials are required but not available."""


def get_client():
    """
    Build a live Supabase client from environment variables.

    Raises SupabaseConfigError if SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is
    unset, or if the `supabase` package is not installed. Never falls back to
    a default credential and never invents one.
    """

    url = os.environ.get(SUPABASE_URL_ENV_VAR)
    key = os.environ.get(SUPABASE_KEY_ENV_VAR)
    if not url or not key:
        raise SupabaseConfigError(
            f"{SUPABASE_URL_ENV_VAR} and {SUPABASE_KEY_ENV_VAR} must be set as "
            f"environment variables to connect to Supabase; no credential is "
            f"hard-coded or defaulted here."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseConfigError(
            "The 'supabase' package is not installed. It is listed in "
            "requirements.txt; install it to obtain a live client."
        ) from exc

    return create_client(url, key)
