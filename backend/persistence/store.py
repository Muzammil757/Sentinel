"""
PersistenceStore: the passive sink docs/data_layer_design.md describes.

Every method takes exactly the dict the corresponding pipeline layer already
produced (or the raw evidence upstream of WEIGH) and writes the row(s)
design section F says that table stores. No method here scores, ranks,
authorizes, executes, or picks a candidate -- every one of those decisions
already happened before its output reached this class. See
backend/persistence/test_safety.py for the structural proof.

`client` is any object satisfying the small surface this module actually
uses -- `.table(name).insert(rows).execute()`, `.table(name).select(...)
.eq(...).execute()`, and `.table(name).update(...).eq(...).execute()` --
mirroring the real `supabase` Python client closely enough that either it or
`persistence.conftest.FakeSupabaseClient` works unmodified. Production code
obtains a real client from `persistence.connection.get_client()`; this class
never constructs one itself, so it stays fully unit-testable without a live
Supabase project.
"""

from persistence import mappers
from persistence.audit import map_audit_event, map_run_failed_event
from persistence.errors import PersistenceError


def _first_row(response) -> dict:
    data = getattr(response, "data", None)
    if not data:
        raise PersistenceError("insert returned no row")
    return data[0]


class PersistenceStore:
    def __init__(self, client):
        self._client = client

    # -- case / case_run identity (design section D, section J) -----------

    def get_or_create_case(self, external_case_id: str | None = None) -> dict:
        """
        Case identity only (design F.1). A supplied external_case_id is
        looked up first, so a legitimate re-run reuses the same case row; a
        missing one always inserts a fresh case, since multiple cases with no
        external id are allowed to coexist.
        """

        if external_case_id is not None:
            existing = (
                self._client.table("cases")
                .select("*")
                .eq("external_case_id", external_case_id)
                .execute()
            )
            rows = getattr(existing, "data", None) or []
            if rows:
                return rows[0]

        response = (
            self._client.table("cases").insert({"external_case_id": external_case_id}).execute()
        )
        return _first_row(response)

    def create_case_run(
        self,
        case_id: str,
        resolve_output: dict,
        case_context: dict,
        policy_id: str,
        policy_version: str,
        policy_hash: str,
        status: str = "IN_PROGRESS",
    ) -> dict:
        """
        Always inserts a new row (design J): a rerun of the same case never
        overwrites a previous run.
        """

        row = mappers.map_case_run(
            case_id,
            resolve_output,
            case_context,
            policy_id,
            policy_version,
            policy_hash,
            status,
        )
        response = self._client.table("case_runs").insert(row).execute()
        return _first_row(response)

    def update_case_run_status(self, case_run_id: str, status: str) -> None:
        """
        The one deliberate mutation in the whole schema (design F.2.1):
        written once, immediately after govern_results is inserted, mirroring
        govern_results.outcome. govern_results.outcome remains authoritative;
        this column exists only so a case-list read never has to join it.
        """

        self._client.table("case_runs").update({"status": status}).eq("id", case_run_id).execute()

    # -- per-run stage tables ---------------------------------------------

    def record_agent_outputs(self, case_run_id: str, agent_actions: dict, agent_a: str, agent_b: str) -> list:
        rows = [
            {**row, "case_run_id": case_run_id}
            for row in mappers.map_agent_outputs(agent_actions, agent_a, agent_b)
        ]
        response = self._client.table("agent_outputs").insert(rows).execute()
        return getattr(response, "data", None) or []

    def record_conflict(self, case_run_id: str, conflict_result: dict) -> dict:
        row = {**mappers.map_conflict(conflict_result), "case_run_id": case_run_id}
        response = self._client.table("conflicts").insert(row).execute()
        return _first_row(response)

    def record_candidates(self, case_run_id: str, resolve_candidates: list) -> list:
        """
        Returns the inserted rows, in RESOLVE's original order, so the caller
        can build the candidate_id -> row id map that candidate_scores and
        govern_results both need (design F.5, F.6, F.8).
        """

        rows = [
            {**row, "case_run_id": case_run_id} for row in mappers.map_candidates(resolve_candidates)
        ]
        response = self._client.table("candidates").insert(rows).execute()
        return getattr(response, "data", None) or []

    def record_candidate_scores(self, weigh_output: dict, candidate_row_ids: dict) -> list:
        rows = mappers.map_candidate_scores(weigh_output, candidate_row_ids)
        response = self._client.table("candidate_scores").insert(rows).execute()
        return getattr(response, "data", None) or []

    def record_weigh_result(self, case_run_id: str, weigh_output: dict) -> dict:
        row = {**mappers.map_weigh_result(weigh_output), "case_run_id": case_run_id}
        response = self._client.table("weigh_results").insert(row).execute()
        return _first_row(response)

    def record_govern_result(self, case_run_id: str, govern_output: dict, candidate_row_ids: dict) -> dict:
        row = {
            **mappers.map_govern_result(govern_output, candidate_row_ids),
            "case_run_id": case_run_id,
        }
        response = self._client.table("govern_results").insert(row).execute()
        return _first_row(response)

    def record_execution_receipt(self, case_run_id: str, govern_result_id: str, receipt: dict) -> dict:
        """
        Records exactly what EXECUTOR returned. `receipt["status"]` travels
        through unchanged -- persistence never turns a REJECTED receipt into
        an EXECUTED one, and never fabricates a receipt EXECUTOR did not
        produce (design section 12).
        """

        row = {
            **mappers.map_execution_receipt(receipt, govern_result_id),
            "case_run_id": case_run_id,
        }
        response = self._client.table("execution_receipts").insert(row).execute()
        return _first_row(response)

    # -- audit trail (design section I) ------------------------------------

    def record_audit_event(
        self, case_run_id: str, stage: str, outcome: str, summary: str, detail: dict | None = None
    ) -> dict:
        row = {**map_audit_event(stage, outcome, summary, detail), "case_run_id": case_run_id}
        response = self._client.table("audit_events").insert(row).execute()
        return _first_row(response)

    def record_run_failed(self, case_run_id: str, failed_stage: str, exc: BaseException, summary: str | None = None) -> dict:
        """
        The observability guarantee for a stage that raises: no row exists in
        that stage's own result table, so this is the only record proving the
        stage was ever reached (design section I.1).
        """

        row = {**map_run_failed_event(failed_stage, exc, summary), "case_run_id": case_run_id}
        response = self._client.table("audit_events").insert(row).execute()
        return _first_row(response)


def candidate_row_id_map(candidate_rows: list) -> dict:
    """Re-exported for callers that persisted candidates and now need the
    candidate_id -> row id map for record_candidate_scores / record_govern_result."""

    return mappers.candidate_row_id_map(candidate_rows)
