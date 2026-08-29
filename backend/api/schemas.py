"""
Request/response models for the Sentinel API.

Request models are the security-critical half of this file: RunRequest and
ReviewRequest deliberately expose no field a client could use to name an
outcome, an authorization, or a candidate selection. `model_config =
ConfigDict(extra="forbid")` on both means a client that tries to slip in
`execution_authorized`, `outcome`, or `govern_output` at the top level gets a
422, not a silently-ignored field.

Agent action payloads stay loosely typed (`dict[str, Any]`, validated for
just the three keys every pipeline layer reads by name) rather than a rigid
per-agent-type model, mirroring case_context's own "schema-light, unknown
keys ignored" contract (docs/data_layer_design.md section H.1) -- the same
raw evidence shape mock_agents/*.py already produces.

Response models are intentionally loose on the JSONB-shaped fields (raw
pipeline documents) -- those are echoed verbatim from GOVERN/WEIGH/EXECUTOR,
never reconstructed from typed sub-fields, for the same tamper-evidence
reason the data layer design keeps `raw_output` columns (design section H.4).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

REQUIRED_AGENT_ACTION_KEYS = ("agent", "proposed_action", "confidence")


def _validate_agent_action(payload: dict, field_name: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(f"{field_name} must be an object")
    missing = [key for key in REQUIRED_AGENT_ACTION_KEYS if key not in payload]
    if missing:
        raise ValueError(f"{field_name} is missing required key(s): {missing}")
    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError(f"{field_name}.confidence must be numeric")
    if not (0.0 <= float(confidence) <= 1.0):
        raise ValueError(f"{field_name}.confidence must be between 0 and 1")
    if not isinstance(payload["agent"], str) or not payload["agent"]:
        raise ValueError(f"{field_name}.agent must be a non-empty string")
    if not isinstance(payload["proposed_action"], str) or not payload["proposed_action"]:
        raise ValueError(f"{field_name}.proposed_action must be a non-empty string")
    return payload


class RunRequest(BaseModel):
    """
    Raw evidence for one pipeline run -- nothing else.

    This is deliberately the *only* shape the run endpoint accepts: two
    agent action payloads, the entity type they concern, optional case
    context, and optional additional agent payloads (constraint evidence
    only, never a party to the conflict itself -- design section B.2).
    `execution_request` is an optional caller assertion forwarded verbatim to
    EXECUTOR's own `request` parameter, which can only narrow or reject an
    authorization, never grant one.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(..., description='"order_vendor" or "customer" today.')
    agent_a: dict[str, Any] = Field(..., description="First conflicting agent's payload (agent, proposed_action, confidence, plus domain fields).")
    agent_b: dict[str, Any] = Field(..., description="Second conflicting agent's payload.")
    extra_agents: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Additional agent payloads present only as constraint evidence."
    )
    case_context: Optional[dict[str, Any]] = Field(
        default=None, description="Optional case_id/merchant fields; all keys optional, unknown keys ignored."
    )
    execution_request: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional caller assertion of what it believes is being executed "
            "({'candidate_id': ..., 'actions': [...]}). Compared against GOVERN's "
            "authorization by EXECUTOR; any mismatch is a rejection. Never a way to "
            "authorize anything -- omit to execute exactly what GOVERN authorized."
        ),
    )

    @field_validator("agent_a", "agent_b")
    @classmethod
    def _validate_conflict_agent(cls, value: dict, info) -> dict:
        return _validate_agent_action(value, info.field_name)

    @field_validator("extra_agents")
    @classmethod
    def _validate_extra_agents(cls, value):
        if value is None:
            return value
        return [_validate_agent_action(item, f"extra_agents[{i}]") for i, item in enumerate(value)]


ReviewAction = Literal["approve", "reject", "request_more_evidence", "override"]


class ReviewRequest(BaseModel):
    """
    A human reviewer's action on a case run.

    Only approve / reject / request_more_evidence are actually supportable
    today -- they are recorded as pure annotations and never change
    GOVERN's outcome or trigger EXECUTOR. "override" is accepted by the
    schema so the API can refuse it explicitly (400, naming the missing
    domain model) rather than reject it as an unrecognized value.
    """

    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    run_id: Optional[str] = Field(default=None, description="Case run this review applies to; defaults to the case's latest run.")
    reviewer: Optional[str] = Field(default=None, description="Free-text reviewer identity.")
    reason: Optional[str] = Field(default=None, description="Free-text justification.")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    application: dict[str, Any]
    database: dict[str, Any]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
