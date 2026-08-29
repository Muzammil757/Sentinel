"""
CaseReader: the read-model counterpart to PersistenceStore.

Same stance as store.py -- this class never decides, scores, ranks, or
recomputes anything. Every method is a SELECT (optionally filtered by a
single `.eq(...)`, then sorted/grouped in Python) shaped to answer exactly
the read questions docs/data_layer_design.md section M and section I.2
describe: case lists, one case's full stage chain, and a chronological
audit timeline. No aggregation beyond counting rows, no derived business
outcome -- outcome/status always come verbatim from govern_results /
case_runs, never re-evaluated here.

`client` is the same minimal surface PersistenceStore uses --
`.table(name).select(...).eq(...).execute()` -- so this class works
unmodified against both `persistence.conftest.FakeSupabaseClient` and a real
Supabase client from `persistence.connection.get_client()`.
"""

import uuid


def _rows(response) -> list:
    return getattr(response, "data", None) or []


def _one(rows: list) -> dict | None:
    return rows[0] if rows else None


def _is_uuid(value) -> bool:
    """
    True only for a syntactically valid UUID string.

    `cases.id` / `case_runs.id` are `uuid` columns; a real Postgres/PostgREST
    backend raises on `.eq("id", <non-uuid text>)` (invalid input syntax for
    type uuid) rather than returning zero rows, which previously surfaced as
    a 502 instead of the intended 404. Every id-column lookup below guards
    with this check first, so a malformed id reads back as "not found" (None)
    exactly like a well-formed id with no matching row, instead of reaching
    the database at all.
    """

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class CaseReader:
    def __init__(self, client):
        self._client = client

    # -- cases / case_runs --------------------------------------------------

    def list_cases(self) -> list:
        response = self._client.table("cases").select("*").execute()
        return sorted(_rows(response), key=lambda row: row.get("created_at") or "", reverse=True)

    def get_case(self, case_id: str) -> dict | None:
        if not _is_uuid(case_id):
            return None
        response = self._client.table("cases").select("*").eq("id", case_id).execute()
        return _one(_rows(response))

    def get_case_by_external_id(self, external_case_id: str) -> dict | None:
        response = (
            self._client.table("cases").select("*").eq("external_case_id", external_case_id).execute()
        )
        return _one(_rows(response))

    def list_case_runs_for_case(self, case_id: str) -> list:
        response = self._client.table("case_runs").select("*").eq("case_id", case_id).execute()
        return sorted(_rows(response), key=lambda row: row.get("created_at") or "", reverse=True)

    def get_latest_case_run(self, case_id: str) -> dict | None:
        runs = self.list_case_runs_for_case(case_id)
        return runs[0] if runs else None

    def get_case_run(self, case_run_id: str) -> dict | None:
        response = self._client.table("case_runs").select("*").eq("id", case_run_id).execute()
        return _one(_rows(response))

    def list_all_case_runs(self) -> list:
        response = self._client.table("case_runs").select("*").execute()
        return sorted(_rows(response), key=lambda row: row.get("created_at") or "", reverse=True)

    # -- per-run stage tables -------------------------------------------------

    def list_agent_outputs(self, case_run_id: str) -> list:
        response = self._client.table("agent_outputs").select("*").eq("case_run_id", case_run_id).execute()
        return _rows(response)

    def get_conflict(self, case_run_id: str) -> dict | None:
        response = self._client.table("conflicts").select("*").eq("case_run_id", case_run_id).execute()
        return _one(_rows(response))

    def list_candidates(self, case_run_id: str) -> list:
        response = self._client.table("candidates").select("*").eq("case_run_id", case_run_id).execute()
        return _rows(response)

    def list_candidate_scores(self, candidate_row_ids: list) -> list:
        """All candidate_scores rows whose candidate_row_id is in the given list.
        The fake and real clients both only support single-column `.eq(...)`
        filters, so the `IN` semantics are applied in Python rather than by
        issuing one query per candidate."""

        response = self._client.table("candidate_scores").select("*").execute()
        wanted = set(candidate_row_ids)
        return [row for row in _rows(response) if row.get("candidate_row_id") in wanted]

    def get_weigh_result(self, case_run_id: str) -> dict | None:
        response = self._client.table("weigh_results").select("*").eq("case_run_id", case_run_id).execute()
        return _one(_rows(response))

    def get_govern_result(self, case_run_id: str) -> dict | None:
        response = self._client.table("govern_results").select("*").eq("case_run_id", case_run_id).execute()
        return _one(_rows(response))

    def get_execution_receipt(self, case_run_id: str) -> dict | None:
        response = (
            self._client.table("execution_receipts").select("*").eq("case_run_id", case_run_id).execute()
        )
        return _one(_rows(response))

    # -- audit trail ----------------------------------------------------------

    def list_audit_events(self, case_run_id: str) -> list:
        # Sorted by occurred_at only, via Python's *stable* sort: rows the
        # fake client doesn't timestamp (it has no DB-side `now()` default)
        # all compare equal and keep their original insertion order, which
        # for the fake client is already chronological. A real Supabase
        # response's occurred_at is always DB-populated, so this still
        # produces true chronological order there.
        response = self._client.table("audit_events").select("*").eq("case_run_id", case_run_id).execute()
        return sorted(_rows(response), key=lambda row: row.get("occurred_at") or "")

    def list_all_audit_events(self) -> list:
        response = self._client.table("audit_events").select("*").execute()
        return _rows(response)

    # -- human review -----------------------------------------------------------

    def list_human_reviews(self, case_run_id: str) -> list:
        response = self._client.table("human_reviews").select("*").eq("case_run_id", case_run_id).execute()
        return sorted(_rows(response), key=lambda row: row.get("created_at") or "")
