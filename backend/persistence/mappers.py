"""
Pure mapping functions: pipeline stage output -> Supabase row dict(s).

No I/O, no client, no decision logic. Each function takes exactly the dict
the corresponding layer already produced (or the raw evidence upstream of
WEIGH) and produces the row(s) docs/data_layer_design.md's table-by-table
schema says that table stores. If a function ever needed to compute something
the pipeline did not already hand it, that would mean the schema is wrong,
not that the mapper needs to get smarter (design's Supabase implementation
plan, step 5).

Every "results" mapper keeps the complete verbatim stage document under
raw_output -- never reconstructed from the structured fields alongside it,
per the auditability rule in design section H.4.

`case_run_id` (and, for candidate_scores, `candidate_row_id`) are database row
ids the caller (persistence.store.PersistenceStore) already knows from a
prior insert. Mappers never invent or look up an id themselves -- they only
shape data already fully determined by the pipeline and the caller.
"""

from .errors import PersistenceError


def map_agent_output(agent_name: str, payload: dict, role: str) -> dict:
    return {
        "agent_name": agent_name,
        "role": role,
        "proposed_action": payload.get("proposed_action"),
        "confidence": payload.get("confidence"),
        # Full payload as produced by mock_agents/*.py -- kept whole rather
        # than split into sparse per-agent-type columns (design section H.2).
        "payload": payload,
    }


def map_agent_outputs(agent_actions: dict, agent_a: str, agent_b: str) -> list:
    """
    One row per agent payload the run consumed: the two conflict parties,
    plus any additional agents present purely as constraint evidence
    (design section F.3, the `no_conflict_release_case(with_rto_verdict=True)`
    pattern in govern/conftest.py).
    """

    rows = []
    for name, payload in agent_actions.items():
        if name == agent_a:
            role = "agent_a"
        elif name == agent_b:
            role = "agent_b"
        else:
            role = "extra"
        rows.append(map_agent_output(name, payload, role))
    return rows


def map_conflict(conflict_result: dict) -> dict:
    """conflict_matrix.integration.evaluate_agent_actions' output (design F.4)."""

    return {
        "action_a": conflict_result["action_a"],
        "action_b": conflict_result["action_b"],
        "conflict": conflict_result["conflict"],
        "reason": conflict_result["reason"],
    }


def map_candidates(resolve_candidates: list) -> list:
    """RESOLVE's substance, verbatim and immutable once written (design F.5)."""

    return [
        {
            "candidate_id": candidate["candidate_id"],
            "strategy": candidate["strategy"],
            "preferred_agent": candidate["preferred_agent"],
            "resulting_actions": list(candidate["resulting_actions"]),
            "rationale": candidate["rationale"],
            "source_rule": candidate["source_rule"],
        }
        for candidate in resolve_candidates
    ]


def map_candidate_scores(weigh_output: dict, candidate_row_ids: dict) -> list:
    """
    WEIGH's enrichment, one row per candidate (design F.6). `candidate_row_ids`
    maps RESOLVE's candidate_id to the database row id already assigned when
    the candidates rows were inserted -- persistence never invents that link,
    it only requires that candidates were persisted first.
    """

    rank_by_id = {}
    score_rank_by_id = {}
    tie_group_by_id = {}
    for entry in weigh_output["ranking"]:
        rank_by_id[entry["candidate_id"]] = entry["rank"]
        score_rank_by_id[entry["candidate_id"]] = entry["score_rank"]
        tie_group_by_id[entry["candidate_id"]] = entry["tie_group"]

    rows = []
    for candidate in weigh_output["candidates"]:
        candidate_id = candidate["candidate_id"]
        if candidate_id not in candidate_row_ids:
            raise PersistenceError(
                f"no candidate row id for candidate_id {candidate_id!r}; candidates "
                f"must be persisted before candidate_scores"
            )
        rows.append(
            {
                "candidate_row_id": candidate_row_ids[candidate_id],
                "total_score": candidate["total_score"],
                "eligible": candidate["eligible"],
                "eligibility_basis": candidate["eligibility_basis"],
                "rank": rank_by_id[candidate_id],
                "score_rank": score_rank_by_id[candidate_id],
                "tie_group": tie_group_by_id[candidate_id],
                "originating_agent": candidate["originating_agent"],
                "originating_confidence": candidate["originating_confidence"],
                "evidence_complete": candidate["evidence_complete"],
                "objective_impacts": candidate["objective_impacts"],
                "constraint_findings": candidate["constraint_findings"],
            }
        )
    return rows


def map_weigh_result(weigh_output: dict) -> dict:
    """
    Run-level WEIGH row (design F.7). `profile_name`, not `profile_selected` --
    weigh/profile.py emits `profile_name`; see design section B.
    """

    profile = weigh_output["profile"]
    evidence = weigh_output["evidence"]
    ambiguity = weigh_output["ambiguity"]

    return {
        "weigh_version": weigh_output["weigh_version"],
        "scoring_method": weigh_output["scoring_method"],
        "profile_name": profile["profile_name"],
        "profile_reason": profile["reason"],
        "matched_rule_index": profile["matched_rule_index"],
        "matched_rule": profile["matched_rule"],
        "weights_used": profile["weights"],
        "case_confidence": evidence["case_confidence"],
        "confidence_method": evidence["confidence_method"],
        "supporting_signals": evidence["supporting_signals"],
        "evidence_complete": evidence["evidence_complete"],
        "ambiguity_detected": ambiguity["detected"],
        "ambiguity_signals": ambiguity["signals"],
        "near_tie_group": ambiguity["near_tie_group"],
        "top_gap": ambiguity["top_gap"],
        "constraint_evaluation": weigh_output["constraint_evaluation"],
        "notes": weigh_output.get("notes", []),
        # The complete, verbatim weigh_output document -- the tamper-evident
        # copy (design section H.4).
        "raw_output": weigh_output,
    }


def map_govern_result(govern_output: dict, candidate_row_ids: dict) -> dict:
    """
    Run-level GOVERN row (design F.8). `candidate_row_ids` resolves GOVERN's
    business-level candidate_id references (`selected_candidate`,
    `candidate_under_review`) to the database row ids assigned when
    candidates were persisted. `selected_candidate_row_id` stays None on every
    outcome but PROCEED -- persistence copies that null-ness, it does not
    decide it.
    """

    selected = govern_output["selected_candidate"]
    selected_row_id = None
    if selected is not None:
        candidate_id = selected["candidate_id"]
        if candidate_id not in candidate_row_ids:
            raise PersistenceError(
                f"no candidate row id for selected_candidate {candidate_id!r}"
            )
        selected_row_id = candidate_row_ids[candidate_id]

    under_review = govern_output["candidate_under_review"]
    under_review_row_id = None
    if under_review is not None:
        if under_review not in candidate_row_ids:
            raise PersistenceError(
                f"no candidate row id for candidate_under_review {under_review!r}"
            )
        under_review_row_id = candidate_row_ids[under_review]

    return {
        "govern_version": govern_output["govern_version"],
        "decision_method": govern_output["decision_method"],
        # Content fingerprint, not a unique event id (design section D) --
        # never given a UNIQUE constraint by this layer or the schema.
        "decision_id": govern_output["decision_id"],
        "outcome": govern_output["outcome"],
        "outcome_basis": govern_output["outcome_basis"],
        "execution_authorized": govern_output["execution_authorized"],
        "selected_candidate_row_id": selected_row_id,
        "authorized_actions": list(govern_output["authorized_actions"]),
        "candidate_under_review_row_id": under_review_row_id,
        "profile_selected": govern_output["profile_selected"],
        "weights_used": govern_output["weights_used"],
        "objectives_considered": list(govern_output["objectives_considered"]),
        "score_band": govern_output["score_band"],
        "permission_evaluation": govern_output["permission_evaluation"],
        "escalation": govern_output["escalation"],
        "claude": govern_output["claude"],
        "rationale": govern_output["rationale"],
        "policy_hash": govern_output["policy_hash"],
        # The complete, verbatim govern_output document (design section H.4).
        "raw_output": govern_output,
    }


def map_execution_receipt(receipt: dict, govern_result_id: str) -> dict:
    """
    EXECUTOR's receipt, verbatim (design F.9). Persistence records what
    EXECUTOR returned -- `status`, `executed_actions`, `rejection` -- and
    never reinterprets it: a REJECTED receipt is stored as REJECTED.
    """

    return {
        "govern_result_id": govern_result_id,
        # Content fingerprint, same non-unique reasoning as decision_id.
        "receipt_id": receipt["receipt_id"],
        "executor_version": receipt["executor_version"],
        "execution_method": receipt["execution_method"],
        "execution_mode": receipt["execution_mode"],
        "status": receipt["status"],
        "authorization": receipt["authorization"],
        "authorization_checks": receipt["authorization_checks"],
        "executed_actions": receipt["executed_actions"],
        "rejection": receipt["rejection"],
        # The complete, verbatim receipt (design section H.4).
        "raw_output": receipt,
    }


def map_case_run(
    case_id: str,
    resolve_output: dict,
    case_context: dict,
    policy_id: str,
    policy_version: str,
    policy_hash: str,
    status: str = "IN_PROGRESS",
) -> dict:
    """
    The hub row for one pipeline execution (design F.2). Always a fresh row --
    persistence.store.PersistenceStore.create_case_run never updates an
    existing one; a rerun creates a sibling under the same case_id.
    """

    return {
        "case_id": case_id,
        "entity_type": resolve_output["entity_type"],
        "agent_a": resolve_output["agent_a"],
        "agent_b": resolve_output["agent_b"],
        "conflict": resolve_output["conflict"],
        "unresolved": resolve_output["unresolved"],
        "case_context": case_context,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "status": status,
    }


def map_human_review(
    action: str, reviewer: str | None, reason: str | None, case_run_status_at_review: str
) -> dict:
    """
    A human reviewer's annotation (design gap identified for the API layer --
    no table for this existed before). Pure annotation: never a field that
    feeds back into GOVERN's outcome or execution_authorized.
    """

    return {
        "action": action,
        "reviewer": reviewer,
        "reason": reason,
        "case_run_status_at_review": case_run_status_at_review,
    }


def candidate_row_id_map(candidate_rows: list) -> dict:
    """{RESOLVE's candidate_id: database row id}, built from the rows
    record_candidates already inserted -- the link candidate_scores and
    govern_results both need."""

    return {row["candidate_id"]: row["id"] for row in candidate_rows}
