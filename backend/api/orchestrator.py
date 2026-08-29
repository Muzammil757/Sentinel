"""
Runs the existing Sentinel pipeline exactly once for one request, persisting
every stage as it completes.

This module makes no decision of any kind. It sequences five already-existing
pure functions in the same order and with the same call shape
persistence/test_store.py::_persist_full_run already exercises against real
pipeline output, and writes through the same PersistenceStore every existing
persistence test uses:

    conflict_matrix.integration.evaluate_agent_actions
    resolve.resolver.generate_resolution_candidates
    weigh.evaluate_candidates
    govern.decide
    executor.execute

A stage that raises is never converted into a success: run_pipeline catches
each stage's real exception, records it as a RUN_FAILED audit event (the one
fact the result tables cannot hold on their own -- design section I.1), marks
the run FAILED, and returns a RunOutcome with `failed=True` and the stage
name. Nothing downstream of a failed stage runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from conflict_matrix.integration import evaluate_agent_actions
from executor import execute
from govern import decide
from persistence.audit import (
    OUTCOME_SUCCEEDED,
    STAGE_AGENTS_RECORDED,
    STAGE_CONFLICT_EVALUATED,
    STAGE_EXECUTOR_COMPLETED,
    STAGE_GOVERN_DECIDED,
    STAGE_RESOLVE_COMPLETED,
    STAGE_RUN_STARTED,
    STAGE_WEIGH_COMPLETED,
)
from persistence.store import PersistenceStore, candidate_row_id_map
from policy.loader import compute_policy_hash, load_policy
from resolve.resolver import generate_resolution_candidates
from weigh import evaluate_candidates


@dataclass
class RunOutcome:
    """Everything a caller (an API route, a scenario runner) needs to shape a
    response, whichever stage the run reached."""

    case: dict
    case_run: dict
    failed: bool = False
    failed_stage: Optional[str] = None
    error_message: Optional[str] = None
    conflict_result: Optional[dict] = None
    resolve_output: Optional[dict] = None
    agent_actions: Optional[dict] = None
    candidate_rows: list = field(default_factory=list)
    weigh_output: Optional[dict] = None
    govern_output: Optional[dict] = None
    govern_row: Optional[dict] = None
    receipt: Optional[dict] = None
    receipt_row: Optional[dict] = None


def _seed_resolve_shape(entity_type: str, agent_a: dict, agent_b: dict) -> dict:
    """
    A case_runs row needs entity_type/agent_a/agent_b/conflict/unresolved
    even when the run failed before RESOLVE ever produced them (e.g. a
    malformed agent payload the API's own request validation would normally
    catch, but a Scenario Lab fixture can still exercise deliberately). This
    is bookkeeping to give the RUN_FAILED audit event a case_run to attach
    to -- conflict/unresolved are placeholders here, never read as a real
    pipeline finding; the row's status is set to FAILED in the same
    transaction sequence.
    """

    return {
        "entity_type": entity_type,
        "agent_a": agent_a.get("agent", "unknown"),
        "agent_b": agent_b.get("agent", "unknown"),
        "conflict": False,
        "unresolved": True,
    }


def run_pipeline(
    store: PersistenceStore,
    *,
    external_case_id: Optional[str],
    entity_type: str,
    agent_a: dict,
    agent_b: dict,
    case_context: Optional[dict] = None,
    extra_agents: Optional[list] = None,
    execution_request: Optional[dict] = None,
    policy: Optional[dict] = None,
) -> RunOutcome:
    """
    Run the real pipeline once and persist every stage.

    `policy` defaults to the real bundle (policy.loader.load_policy()) --
    there is no parameter through which a caller can substitute a different
    policy from an HTTP request; backend.api.router never accepts one.
    """

    case_context = dict(case_context or {})
    policy = policy if policy is not None else load_policy()
    policy_id = policy["policy"]["policy_id"]
    policy_version = policy["policy"]["version"]
    policy_hash = compute_policy_hash(policy)

    case = store.get_or_create_case(external_case_id)

    # -- conflict + resolve (no case_run row exists yet) ---------------------
    try:
        conflict_result = evaluate_agent_actions(agent_a, agent_b, entity_type)
        resolve_output = generate_resolution_candidates(conflict_result, agent_a, agent_b)
    except Exception as exc:
        case_run = store.create_case_run(
            case["id"],
            _seed_resolve_shape(entity_type, agent_a, agent_b),
            case_context,
            policy_id,
            policy_version,
            policy_hash,
            status="FAILED",
        )
        store.record_audit_event(case_run["id"], STAGE_RUN_STARTED, OUTCOME_SUCCEEDED, "run started")
        store.record_run_failed(case_run["id"], "CONFLICT_OR_RESOLVE", exc)
        case_run["status"] = "FAILED"
        return RunOutcome(
            case=case, case_run=case_run, failed=True, failed_stage="CONFLICT_OR_RESOLVE", error_message=str(exc)
        )

    case_run = store.create_case_run(
        case["id"], resolve_output, case_context, policy_id, policy_version, policy_hash
    )
    store.record_audit_event(case_run["id"], STAGE_RUN_STARTED, OUTCOME_SUCCEEDED, "run started")

    agent_actions = {agent_a["agent"]: agent_a, agent_b["agent"]: agent_b}
    for extra in extra_agents or []:
        agent_actions[extra["agent"]] = extra

    store.record_agent_outputs(case_run["id"], agent_actions, resolve_output["agent_a"], resolve_output["agent_b"])
    store.record_audit_event(
        case_run["id"], STAGE_AGENTS_RECORDED, OUTCOME_SUCCEEDED, f"{len(agent_actions)} agent payload(s) recorded"
    )

    store.record_conflict(case_run["id"], conflict_result)
    store.record_audit_event(case_run["id"], STAGE_CONFLICT_EVALUATED, OUTCOME_SUCCEEDED, conflict_result["reason"])

    candidate_rows = store.record_candidates(case_run["id"], resolve_output["candidates"])
    row_ids = candidate_row_id_map(candidate_rows)
    store.record_audit_event(
        case_run["id"], STAGE_RESOLVE_COMPLETED, OUTCOME_SUCCEEDED, f"{len(candidate_rows)} candidate(s) generated"
    )

    outcome = RunOutcome(
        case=case,
        case_run=case_run,
        conflict_result=conflict_result,
        resolve_output=resolve_output,
        agent_actions=agent_actions,
        candidate_rows=candidate_rows,
    )

    # -- WEIGH -----------------------------------------------------------------
    try:
        weigh_output = evaluate_candidates(resolve_output, agent_actions, case_context, policy)
    except Exception as exc:
        store.update_case_run_status(case_run["id"], "FAILED")
        store.record_run_failed(case_run["id"], "WEIGH", exc)
        case_run["status"] = "FAILED"
        outcome.failed, outcome.failed_stage, outcome.error_message = True, "WEIGH", str(exc)
        return outcome

    store.record_candidate_scores(weigh_output, row_ids)
    store.record_weigh_result(case_run["id"], weigh_output)
    store.record_audit_event(
        case_run["id"],
        STAGE_WEIGH_COMPLETED,
        OUTCOME_SUCCEEDED,
        f"scored via profile {weigh_output['profile']['profile_name']}",
    )
    outcome.weigh_output = weigh_output

    # -- GOVERN ------------------------------------------------------------------
    try:
        govern_output = decide(weigh_output, agent_actions, case_context, policy)
    except Exception as exc:
        store.update_case_run_status(case_run["id"], "FAILED")
        store.record_run_failed(case_run["id"], "GOVERN", exc)
        case_run["status"] = "FAILED"
        outcome.failed, outcome.failed_stage, outcome.error_message = True, "GOVERN", str(exc)
        return outcome

    govern_row = store.record_govern_result(case_run["id"], govern_output, row_ids)
    store.update_case_run_status(case_run["id"], govern_output["outcome"])
    case_run["status"] = govern_output["outcome"]
    store.record_audit_event(
        case_run["id"], STAGE_GOVERN_DECIDED, OUTCOME_SUCCEEDED, govern_output["rationale"]["outcome_sentence"]
    )
    outcome.govern_output = govern_output
    outcome.govern_row = govern_row

    # -- EXECUTOR ------------------------------------------------------------------
    try:
        receipt = execute(govern_output, request=execution_request)
    except Exception as exc:
        store.record_run_failed(case_run["id"], "EXECUTOR", exc)
        outcome.failed, outcome.failed_stage, outcome.error_message = True, "EXECUTOR", str(exc)
        return outcome

    receipt_row = store.record_execution_receipt(case_run["id"], govern_row["id"], receipt)
    # EXECUTOR itself completed normally either way -- a REJECTED receipt is a
    # correct, fully-audited refusal, not a failure of the stage. The audit
    # outcome vocabulary (SUCCEEDED/FAILED) tracks whether the stage raised,
    # exactly like STAGE_GOVERN_DECIDED stays SUCCEEDED for every outcome
    # including ESCALATE/HOLD/AMBIGUOUS.
    store.record_audit_event(
        case_run["id"], STAGE_EXECUTOR_COMPLETED, OUTCOME_SUCCEEDED, f"receipt status {receipt['status']}"
    )
    outcome.receipt = receipt
    outcome.receipt_row = receipt_row

    return outcome
