"""
Read-model assembly for the API layer's GET endpoints, and the human-review
write path. Every function here takes a persistence.reader.CaseReader (and,
for the one write path, a persistence.store.PersistenceStore) and shapes
already-persisted rows into the response the corresponding route needs.

No function here computes a score, a rank, an outcome, or an authorization --
every such value is read verbatim from a row written by PersistenceStore
after the real pipeline already decided it. This module's only logic is
"which rows does this endpoint need, and how do they nest."
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from persistence.reader import CaseReader
from persistence.store import PersistenceStore

from .errors import CaseNotFoundError, RunNotFoundError
from .orchestrator import RunOutcome

RECENT_RUNS_LIMIT = 10


def _require_case(reader: CaseReader, case_id: str) -> dict:
    """
    `case_id` is accepted either as the internal case row id or as the
    caller's business-facing external_case_id -- the same identifier
    POST /cases/{case_id}/run uses to get_or_create_case. Trying the
    internal id first, then falling back to an external-id lookup, means a
    client that only ever knows its own business id can still GET the case
    it just ran.
    """

    case = reader.get_case(case_id)
    if case is None:
        case = reader.get_case_by_external_id(case_id)
    if case is None:
        raise CaseNotFoundError(f"case {case_id!r} was not found")
    return case


def _resolve_run(reader: CaseReader, case: dict, run_id: Optional[str]) -> Optional[dict]:
    """The run this request means: an explicit run_id (which must actually
    belong to this case), or the case's latest run, or None when the case
    has no runs yet."""

    if run_id is not None:
        run = reader.get_case_run(run_id)
        if run is None or run["case_id"] != case["id"]:
            raise RunNotFoundError(f"run {run_id!r} was not found for case {case['id']!r}")
        return run
    return reader.get_latest_case_run(case["id"])


def _require_case_and_run(reader: CaseReader, case_id: str, run_id: Optional[str]) -> tuple[dict, dict]:
    case = _require_case(reader, case_id)
    run = _resolve_run(reader, case, run_id)
    if run is None:
        raise RunNotFoundError(f"case {case_id!r} has no runs yet")
    return case, run


def _candidates_with_scores(reader: CaseReader, case_run_id: str) -> list:
    candidates = reader.list_candidates(case_run_id)
    scores = reader.list_candidate_scores([c["id"] for c in candidates])
    scores_by_candidate_row_id = {s["candidate_row_id"]: s for s in scores}
    return [{**candidate, "score": scores_by_candidate_row_id.get(candidate["id"])} for candidate in candidates]


# --- Command Center ----------------------------------------------------------


def _case_summary(reader: CaseReader, case: dict) -> dict:
    latest_run = reader.get_latest_case_run(case["id"])
    govern_result = reader.get_govern_result(latest_run["id"]) if latest_run else None
    receipt = reader.get_execution_receipt(latest_run["id"]) if latest_run else None
    outcome = govern_result["outcome"] if govern_result else None
    status = latest_run["status"] if latest_run else None

    human_review_required: Optional[bool]
    if status == "FAILED":
        human_review_required = True
    elif outcome is not None:
        human_review_required = outcome != "PROCEED"
    else:
        human_review_required = None

    return {
        "case_id": case["id"],
        "external_case_id": case.get("external_case_id"),
        "case_created_at": case.get("created_at"),
        "latest_run_id": latest_run["id"] if latest_run else None,
        "latest_run_created_at": latest_run.get("created_at") if latest_run else None,
        "entity_type": latest_run.get("entity_type") if latest_run else None,
        "run_count": len(reader.list_case_runs_for_case(case["id"])),
        "status": status,
        "outcome": outcome,
        "execution_authorized": govern_result.get("execution_authorized") if govern_result else None,
        "executed": bool(receipt and receipt.get("status") == "EXECUTED"),
        "human_review_required": human_review_required,
    }


def list_cases(reader: CaseReader) -> list:
    return [_case_summary(reader, case) for case in reader.list_cases()]


def list_case_runs(reader: CaseReader, case_id: str) -> list:
    """
    One row per run for a case, newest first (reader.list_case_runs_for_case
    already sorts that way) -- enough for a run-history picker without
    fetching each run's full detail. outcome/executed are read the same way
    _case_summary reads them for the case list, never recomputed.
    """

    case = _require_case(reader, case_id)
    runs = reader.list_case_runs_for_case(case["id"])

    rows = []
    for run in runs:
        govern_result = reader.get_govern_result(run["id"])
        receipt = reader.get_execution_receipt(run["id"])
        rows.append(
            {
                "case_run_id": run["id"],
                "status": run.get("status"),
                "created_at": run.get("created_at"),
                "entity_type": run.get("entity_type"),
                "outcome": govern_result["outcome"] if govern_result else None,
                "executed": bool(receipt and receipt.get("status") == "EXECUTED"),
            }
        )
    return rows


def get_case_detail(reader: CaseReader, case_id: str, run_id: Optional[str] = None) -> dict:
    case = _require_case(reader, case_id)
    run = _resolve_run(reader, case, run_id)
    if run is None:
        return {
            "case": case,
            "run": None,
            "agents": [],
            "conflict": None,
            "candidates": [],
            "weigh_result": None,
            "govern_result": None,
            "execution_receipt": None,
            "timeline": [],
            "human_reviews": [],
        }

    return {
        "case": case,
        "run": run,
        "agents": reader.list_agent_outputs(run["id"]),
        "conflict": reader.get_conflict(run["id"]),
        "candidates": _candidates_with_scores(reader, run["id"]),
        "weigh_result": reader.get_weigh_result(run["id"]),
        "govern_result": reader.get_govern_result(run["id"]),
        "execution_receipt": reader.get_execution_receipt(run["id"]),
        "timeline": reader.list_audit_events(run["id"]),
        "human_reviews": reader.list_human_reviews(run["id"]),
    }


# --- decision investigation ---------------------------------------------------


def get_decision(reader: CaseReader, case_id: str, run_id: Optional[str] = None) -> dict:
    case, run = _require_case_and_run(reader, case_id, run_id)
    govern_result = reader.get_govern_result(run["id"])

    if govern_result is None:
        # The run exists but never reached GOVERN (it failed earlier, or is
        # still in progress) -- report that gap rather than fabricating one.
        return {
            "case_id": case["id"],
            "run_id": run["id"],
            "run_status": run.get("status"),
            "govern_result": None,
            "note": "GOVERN did not produce a result for this run; see the timeline for what happened.",
        }

    candidates_by_row_id = {c["id"]: c for c in reader.list_candidates(run["id"])}

    return {
        "case_id": case["id"],
        "run_id": run["id"],
        "outcome": govern_result["outcome"],
        "outcome_basis": govern_result["outcome_basis"],
        "execution_authorized": govern_result["execution_authorized"],
        "decision_id": govern_result["decision_id"],
        "selected_candidate": candidates_by_row_id.get(govern_result.get("selected_candidate_row_id")),
        "candidate_under_review": candidates_by_row_id.get(govern_result.get("candidate_under_review_row_id")),
        "authorized_actions": govern_result["authorized_actions"],
        "profile_selected": govern_result["profile_selected"],
        "weights_used": govern_result["weights_used"],
        "objectives_considered": govern_result["objectives_considered"],
        "score_band": govern_result["score_band"],
        "permission_evaluation": govern_result["permission_evaluation"],
        "escalation": govern_result["escalation"],
        "rationale": govern_result["rationale"],
        "policy_hash": govern_result["policy_hash"],
        "raw_output": govern_result["raw_output"],
    }


# --- evidence / agent positions ------------------------------------------------


def get_evidence(reader: CaseReader, case_id: str, run_id: Optional[str] = None) -> dict:
    case, run = _require_case_and_run(reader, case_id, run_id)
    return {
        "case_id": case["id"],
        "run_id": run["id"],
        "agents": reader.list_agent_outputs(run["id"]),
        "conflict": reader.get_conflict(run["id"]),
        "candidates": _candidates_with_scores(reader, run["id"]),
        "weigh_result": reader.get_weigh_result(run["id"]),
    }


# --- timeline / audit -----------------------------------------------------------


def get_timeline(reader: CaseReader, case_id: str, run_id: Optional[str] = None) -> dict:
    case, run = _require_case_and_run(reader, case_id, run_id)
    return {
        "case_id": case["id"],
        "run_id": run["id"],
        "events": reader.list_audit_events(run["id"]),
        "human_reviews": reader.list_human_reviews(run["id"]),
    }


# --- human review ----------------------------------------------------------------


def record_review(
    store: PersistenceStore,
    reader: CaseReader,
    case_id: str,
    run_id: Optional[str],
    action: str,
    reviewer: Optional[str],
    reason: Optional[str],
) -> dict:
    case, run = _require_case_and_run(reader, case_id, run_id)
    status_snapshot = run.get("status") or "IN_PROGRESS"

    row = store.record_human_review(run["id"], action, reviewer, reason, status_snapshot)

    return {
        "case_id": case["id"],
        "run_id": run["id"],
        "action": action,
        "reviewer": reviewer,
        "reason": reason,
        "case_run_status_at_review": status_snapshot,
        "recorded_at": row.get("created_at"),
        "note": (
            "Recorded as an annotation only. It does not change GOVERN's outcome, "
            "does not set execution_authorized, and does not trigger EXECUTOR."
        ),
    }


# --- run response shaping ---------------------------------------------------------


def render_run_outcome(outcome: RunOutcome) -> dict:
    """
    Shape a RunOutcome into the response for POST /run and
    POST /scenarios/{id}/run. A failed run is not an HTTP error -- it is a
    fully audited, real pipeline result (RUN_FAILED) -- so this always
    returns a body; `failed` tells the caller which shape to expect.
    """

    response = {
        "case_id": outcome.case["id"],
        "external_case_id": outcome.case.get("external_case_id"),
        "case_run_id": outcome.case_run["id"],
        "status": outcome.case_run.get("status"),
        "failed": outcome.failed,
    }
    if outcome.failed:
        response["failed_stage"] = outcome.failed_stage
        response["error"] = outcome.error_message
        return response

    response.update(
        {
            "conflict": outcome.conflict_result,
            "resolve_result": outcome.resolve_output,
            "weigh_result": outcome.weigh_output,
            "govern_result": outcome.govern_output,
            "execution_receipt": outcome.receipt,
        }
    )
    return response


# --- system reliability -----------------------------------------------------------


def get_reliability(reader: CaseReader) -> dict:
    runs = reader.list_all_case_runs()
    events = reader.list_all_audit_events()
    run_ids_with_events = {event["case_run_id"] for event in events}

    executed_count = 0
    rejected_count = 0
    for run in runs:
        receipt = reader.get_execution_receipt(run["id"])
        if receipt is None:
            continue
        if receipt["status"] == "EXECUTED":
            executed_count += 1
        elif receipt["status"] == "REJECTED":
            rejected_count += 1

    recent_runs = [
        {
            "case_run_id": run["id"],
            "case_id": run["case_id"],
            "status": run.get("status"),
            "created_at": run.get("created_at"),
        }
        for run in runs[:RECENT_RUNS_LIMIT]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_runs": len(runs),
        "runs_by_status": dict(Counter(run.get("status") for run in runs)),
        "executed_count": executed_count,
        "rejected_count": rejected_count,
        "audit_events_total": len(events),
        "runs_missing_audit_trail": sum(1 for run in runs if run["id"] not in run_ids_with_events),
        "recent_runs": recent_runs,
    }
