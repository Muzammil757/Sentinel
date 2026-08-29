"""
Route handlers. Every handler is thin: parse/validate the request (FastAPI +
backend.api.schemas already did most of that), call one function in
backend.api.service or backend.api.orchestrator, and return its result. No
handler here contains a governance decision, a score, or a direct Supabase
query -- reads go through persistence.reader.CaseReader, writes go through
persistence.store.PersistenceStore, and the one place the real pipeline runs
is backend.api.orchestrator.run_pipeline.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from persistence.reader import CaseReader
from persistence.store import PersistenceStore

from . import scenarios as scenario_registry
from . import service
from .deps import get_application_health, get_database_health, get_reader, get_store
from .errors import ScenarioNotFoundError, UnsupportedOperationError
from .orchestrator import run_pipeline
from .schemas import ReviewRequest, RunRequest

router = APIRouter(prefix="/api")


# --- health --------------------------------------------------------------------


@router.get(
    "/health",
    summary="Application and persistence health",
    description=(
        "Reports application health (this process is up) and database health "
        "(a live Supabase read succeeded) as two independent fields. The "
        "process being up never implies the database is reachable."
    ),
)
def health(
    application: dict = Depends(get_application_health), database: dict = Depends(get_database_health)
) -> dict:
    return {"status": "ok", "application": application, "database": database}


# --- Command Center --------------------------------------------------------------


@router.get(
    "/cases",
    summary="List cases for the Command Center",
    description="One row per case, summarizing its latest run's outcome/status/execution state.",
)
def list_cases(reader: CaseReader = Depends(get_reader)) -> list:
    return service.list_cases(reader)


@router.get(
    "/cases/{case_id}/runs",
    summary="List every run for a case",
    description=(
        "One row per run (case_run_id, status, entity_type, outcome, executed, "
        "created_at), newest first -- enough for a run-history picker. Fetch "
        "GET /cases/{case_id}?run_id=... for a specific run's full detail."
    ),
)
def list_case_runs(case_id: str, reader: CaseReader = Depends(get_reader)) -> list:
    return service.list_case_runs(reader, case_id)


@router.get(
    "/cases/{case_id}",
    summary="Case investigation detail",
    description=(
        "The complete operational summary for one case's run: agents, conflict, "
        "candidates and their scores, WEIGH result, GOVERN result, execution "
        "receipt, and timeline. Defaults to the case's latest run; pass run_id "
        "to inspect an earlier one."
    ),
)
def get_case(
    case_id: str, run_id: Optional[str] = Query(default=None), reader: CaseReader = Depends(get_reader)
) -> dict:
    return service.get_case_detail(reader, case_id, run_id)


# --- decision investigation --------------------------------------------------------


@router.get(
    "/cases/{case_id}/decision",
    summary="GOVERN decision detail",
    description=(
        "The GOVERN decision and the information that explains it: outcome, "
        "execution_authorized, selected/under-review candidate, scores, and "
        "policy/permission detail already produced by GOVERN. Never adds a "
        "confidence figure or narrative GOVERN did not itself produce."
    ),
)
def get_decision(
    case_id: str, run_id: Optional[str] = Query(default=None), reader: CaseReader = Depends(get_reader)
) -> dict:
    return service.get_decision(reader, case_id, run_id)


# --- evidence / agent positions -----------------------------------------------------


@router.get(
    "/cases/{case_id}/evidence",
    summary="Agent positions and evidence",
    description="Each agent's payload, the conflict finding, RESOLVE's candidates, and WEIGH's scoring of each -- exactly as the pipeline produced them.",
)
def get_evidence(
    case_id: str, run_id: Optional[str] = Query(default=None), reader: CaseReader = Depends(get_reader)
) -> dict:
    return service.get_evidence(reader, case_id, run_id)


# --- timeline / audit -----------------------------------------------------------------


@router.get(
    "/cases/{case_id}/timeline",
    summary="Audit timeline",
    description="audit_events for one run, in chronological order, plus any recorded human reviews.",
)
def get_timeline(
    case_id: str, run_id: Optional[str] = Query(default=None), reader: CaseReader = Depends(get_reader)
) -> dict:
    return service.get_timeline(reader, case_id, run_id)


# --- running a case ---------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/run",
    summary="Run the real Sentinel pipeline for a case",
    description=(
        "Invokes the existing conflict_matrix -> resolve -> weigh -> govern -> executor "
        "pipeline, unmodified, and persists every stage. `case_id` is the caller's "
        "business-facing case id (reused if it already exists; a run is always a new "
        "row). The request carries only raw agent evidence -- there is no field through "
        "which a client can name an outcome or force execution_authorized."
    ),
)
def run_case(case_id: str, body: RunRequest, store: PersistenceStore = Depends(get_store)) -> dict:
    outcome = run_pipeline(
        store,
        external_case_id=case_id,
        entity_type=body.entity_type,
        agent_a=body.agent_a,
        agent_b=body.agent_b,
        case_context=body.case_context,
        extra_agents=body.extra_agents,
        execution_request=body.execution_request,
    )
    return service.render_run_outcome(outcome)


# --- human review -----------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/review",
    summary="Record a human review action",
    description=(
        "Records a reviewer's approve / reject / request_more_evidence action as a "
        "durable annotation. It never changes GOVERN's outcome, never sets "
        "execution_authorized, and never triggers EXECUTOR -- GOVERN's original "
        "decision remains the sole authorization record. 'override' is refused: the "
        "current architecture has no policy/authorization model for a human "
        "overriding GOVERN, so it is not implemented rather than invented casually."
    ),
)
def review_case(case_id: str, body: ReviewRequest, store: PersistenceStore = Depends(get_store), reader: CaseReader = Depends(get_reader)) -> dict:
    if body.action == "override":
        raise UnsupportedOperationError(
            "The 'override' review action is not supported: the current architecture has "
            "no policy or authorization model for a human overriding GOVERN's decision. "
            "Supported actions are approve, reject, and request_more_evidence, none of "
            "which change GOVERN's outcome or trigger execution."
        )
    return service.record_review(store, reader, case_id, body.run_id, body.action, body.reviewer, body.reason)


# --- Scenario Lab ------------------------------------------------------------------------


@router.get(
    "/scenarios",
    summary="List Scenario Lab scenarios",
    description="Curated, deterministic scenarios, each backed by real agent evidence that is run through the actual pipeline when executed.",
)
def list_scenarios() -> list:
    return [
        {"id": scenario.id, "title": scenario.title, "description": scenario.description}
        for scenario in scenario_registry.list_scenarios()
    ]


@router.post(
    "/scenarios/{scenario_id}/run",
    summary="Run a Scenario Lab scenario through the real pipeline",
    description="Runs the scenario's fixed evidence through the same orchestrator POST /cases/{id}/run uses -- the same pipeline, not a mocked response.",
)
def run_scenario(scenario_id: str, store: PersistenceStore = Depends(get_store)) -> dict:
    scenario = scenario_registry.get_scenario(scenario_id)
    if scenario is None:
        raise ScenarioNotFoundError(f"scenario {scenario_id!r} was not found")
    outcome = run_pipeline(store, **scenario.build())
    response = service.render_run_outcome(outcome)
    response["scenario_id"] = scenario.id
    response["scenario_title"] = scenario.title
    return response


# --- reliability ---------------------------------------------------------------------------


@router.get(
    "/system/reliability",
    summary="System reliability metrics",
    description=(
        "Metrics actually derivable from persisted runs: counts by outcome/status, "
        "executed/rejected counts, audit-trail coverage, and recent runs. Never a "
        "hard-coded figure -- a metric this endpoint cannot honestly source (e.g. "
        "automated test counts, which would require a CI integration this API does "
        "not have) is simply not included."
    ),
)
def get_reliability(reader: CaseReader = Depends(get_reader)) -> dict:
    return service.get_reliability(reader)
