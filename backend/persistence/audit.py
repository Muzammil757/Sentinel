"""
audit_events vocabulary: the closed set of `stage` and `outcome` values,
matching the CHECK constraints in
supabase/migrations/20260825000000_initial_schema.sql exactly.

A stage that fails leaves no row in its own result table (design section I.1) --
that is the one fact the eight other tables structurally cannot record.
`map_run_failed_event` is how a caller (an orchestrator, or a test simulating
one) turns "WEIGH raised" into the single row that proves WEIGH was reached
and failed, without ever fabricating a successful weigh_results row.

Pure mapping only -- no client, no decision about what a failure means.
"""

STAGE_RUN_STARTED = "RUN_STARTED"
STAGE_AGENTS_RECORDED = "AGENTS_RECORDED"
STAGE_CONFLICT_EVALUATED = "CONFLICT_EVALUATED"
STAGE_RESOLVE_COMPLETED = "RESOLVE_COMPLETED"
STAGE_WEIGH_COMPLETED = "WEIGH_COMPLETED"
STAGE_GOVERN_DECIDED = "GOVERN_DECIDED"
STAGE_EXECUTOR_COMPLETED = "EXECUTOR_COMPLETED"
STAGE_RUN_FAILED = "RUN_FAILED"

STAGES = frozenset(
    {
        STAGE_RUN_STARTED,
        STAGE_AGENTS_RECORDED,
        STAGE_CONFLICT_EVALUATED,
        STAGE_RESOLVE_COMPLETED,
        STAGE_WEIGH_COMPLETED,
        STAGE_GOVERN_DECIDED,
        STAGE_EXECUTOR_COMPLETED,
        STAGE_RUN_FAILED,
    }
)

OUTCOME_SUCCEEDED = "SUCCEEDED"
OUTCOME_FAILED = "FAILED"

OUTCOMES = frozenset({OUTCOME_SUCCEEDED, OUTCOME_FAILED})


def map_audit_event(stage: str, outcome: str, summary: str, detail: dict | None = None) -> dict:
    """
    One audit_events row. `stage` and `outcome` must be members of the closed
    vocabulary above -- persistence never invents a stage or outcome the
    schema does not already define.
    """

    if stage not in STAGES:
        raise ValueError(f"unknown audit stage {stage!r}; must be one of {sorted(STAGES)}")
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown audit outcome {outcome!r}; must be one of {sorted(OUTCOMES)}")

    return {"stage": stage, "outcome": outcome, "summary": summary, "detail": detail}


def map_run_failed_event(failed_stage: str, exc: BaseException, summary: str | None = None) -> dict:
    """
    The only record that a stage was ever reached, when that stage raises
    before producing a result. `detail` is kept small (design section F.10): an
    error type and message, never the full document a successful stage would
    have produced.
    """

    detail = {
        "failed_stage": failed_stage,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }
    return map_audit_event(
        STAGE_RUN_FAILED,
        OUTCOME_FAILED,
        summary or f"{failed_stage} failed: {type(exc).__name__}: {exc}",
        detail=detail,
    )
