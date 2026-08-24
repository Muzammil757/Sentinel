"""
WEIGH: deterministic evaluation of RESOLVE candidates against Sentinel
governance policy (docs/weigh_layer_design.md).

evaluate_candidates() is a pure function: same four inputs, same output,
every time. It never executes an action, writes to a database, calls
Claude or any network service, reads the clock, or invents/drops/modifies
a RESOLVE candidate. It never names a final governance decision -- that is
GOVERN's job, downstream of this module.
"""

from policy.loader import compute_policy_hash

from weigh.ambiguity import evaluate_ambiguity
from weigh.confidence import compute_case_confidence, resolve_originating_confidence
from weigh.constraints import CONSTRAINT_EVALUATORS, evaluate_constraints_for_candidate
from weigh.errors import WeighInputError, WeighPolicyError
from weigh.profile import select_profile
from weigh.scoring import build_ranking, score_candidate
from weigh.schema import (
    CONFIDENCE_METHOD,
    REQUIRED_CANDIDATE_KEYS,
    REQUIRED_POLICY_SECTIONS,
    REQUIRED_RESOLVE_KEYS,
    SCORING_METHOD,
    WEIGH_VERSION,
)


def _validate_input(resolve_output: dict, agent_actions: dict) -> None:
    if not isinstance(resolve_output, dict):
        raise WeighInputError("resolve_output must be a mapping")

    missing = REQUIRED_RESOLVE_KEYS - resolve_output.keys()
    if missing:
        raise WeighInputError(f"resolve_output is missing required key(s): {sorted(missing)}")

    candidates = resolve_output["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise WeighInputError("resolve_output.candidates must be a non-empty list")

    candidate_ids = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise WeighInputError(f"resolve_output.candidates[{index}] must be a mapping")
        missing_keys = REQUIRED_CANDIDATE_KEYS - candidate.keys()
        if missing_keys:
            raise WeighInputError(
                f"resolve_output.candidates[{index}] is missing required key(s): "
                f"{sorted(missing_keys)}"
            )
        candidate_ids.append(candidate["candidate_id"])

    if len(candidate_ids) != len(set(candidate_ids)):
        raise WeighInputError("resolve_output.candidates contains duplicate candidate_id values")

    if not isinstance(agent_actions, dict):
        raise WeighInputError("agent_actions must be a mapping of agent name to agent payload")

    agent_a = resolve_output["agent_a"]
    agent_b = resolve_output["agent_b"]
    if agent_a not in agent_actions:
        raise WeighInputError(f"agent_actions is missing entry for agent_a {agent_a!r}")
    if agent_b not in agent_actions:
        raise WeighInputError(f"agent_actions is missing entry for agent_b {agent_b!r}")

    for candidate in candidates:
        preferred = candidate["preferred_agent"]
        if preferred is not None and preferred not in agent_actions:
            raise WeighInputError(
                f"candidate {candidate['candidate_id']!r} preferred_agent {preferred!r} "
                f"is not present in agent_actions"
            )


def _preflight_policy_checks(resolve_output: dict, policy: dict) -> None:
    for section in REQUIRED_POLICY_SECTIONS:
        if section not in policy:
            raise WeighPolicyError(f"policy is missing required section {section!r}")

    for constraint in policy["hard_constraints"]:
        if constraint["id"] not in CONSTRAINT_EVALUATORS:
            raise WeighPolicyError(
                f"No WEIGH evaluator registered for hard constraint {constraint['id']!r}"
            )

    action_effects = policy["scoring"]["action_effects"]
    strategy_effects = policy["scoring"]["strategy_effects"]

    for candidate in resolve_output["candidates"]:
        strategy = candidate["strategy"]
        if strategy not in strategy_effects:
            raise WeighPolicyError(
                f"No scoring.strategy_effects entry for strategy {strategy!r} "
                f"referenced by candidate {candidate['candidate_id']!r}"
            )
        for action in candidate["resulting_actions"]:
            if action not in action_effects:
                raise WeighPolicyError(
                    f"No scoring.action_effects entry for action {action!r} "
                    f"referenced by candidate {candidate['candidate_id']!r}"
                )


def _count_supporting_signals(contributing_agents: list, agent_actions: dict) -> int:
    """
    Design §J.3: the number of contributing agents whose payload carries
    both a non-empty proposed_action and a valid numeric confidence. This
    counts usable declarations, not risk indicators -- counting risk
    indicators would be a step toward scoring the entity rather than the
    governance options.
    """

    count = 0
    for agent in contributing_agents:
        payload = agent_actions.get(agent)
        if not payload:
            continue
        action = payload.get("proposed_action")
        confidence = payload.get("confidence")
        valid_confidence = (
            not isinstance(confidence, bool)
            and isinstance(confidence, (int, float))
            and 0.0 <= confidence <= 1.0
        )
        if action and valid_confidence:
            count += 1
    return count


def _candidate_evidence_complete(candidate: dict, findings: list, missing_confidence_agents: list) -> bool:
    if any(f["status"] == "INDETERMINATE" for f in findings):
        return False
    preferred = candidate["preferred_agent"]
    if preferred is None:
        return len(missing_confidence_agents) == 0
    return preferred not in missing_confidence_agents


def _build_case_block(resolve_output: dict, case_context: dict) -> dict:
    case = {
        "entity_type": resolve_output["entity_type"],
        "agent_a": resolve_output["agent_a"],
        "agent_b": resolve_output["agent_b"],
        "conflict": resolve_output["conflict"],
        "unresolved": resolve_output["unresolved"],
    }
    if "case_id" in case_context:
        case = {"case_id": case_context["case_id"], **case}
    return case


def evaluate_candidates(resolve_output: dict, agent_actions: dict, case_context: dict, policy: dict) -> dict:
    _validate_input(resolve_output, agent_actions)
    if not isinstance(case_context, dict):
        raise WeighInputError("case_context must be a mapping")

    _preflight_policy_checks(resolve_output, policy)

    policy_id = policy["policy"]["policy_id"]
    policy_version = policy["policy"]["version"]
    policy_hash = compute_policy_hash(policy)

    profile = select_profile(case_context, policy)
    weights = profile["weights"]

    agent_a = resolve_output["agent_a"]
    agent_b = resolve_output["agent_b"]
    contributing_agents = sorted({agent_a, agent_b})

    alpha = policy["scoring"]["confidence"]["min_weight"]
    case_confidence, confidence_inputs, missing_confidence_agents = compute_case_confidence(
        contributing_agents, agent_actions, alpha
    )

    supporting_signals = _count_supporting_signals(contributing_agents, agent_actions)

    scoring_policy = policy["scoring"]
    hard_constraints = policy["hard_constraints"]

    evaluated_candidates = []
    notes = []
    for agent in missing_confidence_agents:
        notes.append(
            {
                "code": "E_MISSING_CONFIDENCE",
                "message": f"Agent '{agent}' confidence missing or invalid; treated as 0.0.",
                "candidate_id": None,
                "agent": agent,
            }
        )

    for candidate in resolve_output["candidates"]:
        objective_impacts, total_score = score_candidate(candidate, scoring_policy, weights)

        originating_confidence = resolve_originating_confidence(
            candidate["preferred_agent"], agent_actions, case_confidence
        )

        findings, eligible = evaluate_constraints_for_candidate(
            candidate, agent_actions, case_context, hard_constraints, policy, originating_confidence
        )

        evidence_complete = _candidate_evidence_complete(candidate, findings, missing_confidence_agents)

        if eligible:
            eligibility_basis = "no_blocking_findings"
        else:
            blocking = sorted(
                {f["constraint_id"] for f in findings if f["status"] in ("VIOLATED", "INDETERMINATE")}
            )
            eligibility_basis = "blocked_by:" + ",".join(blocking)

        evaluated_candidates.append(
            {
                "candidate_id": candidate["candidate_id"],
                "strategy": candidate["strategy"],
                "preferred_agent": candidate["preferred_agent"],
                "resulting_actions": list(candidate["resulting_actions"]),
                "rationale": candidate["rationale"],
                "source_rule": candidate["source_rule"],
                "objective_impacts": objective_impacts,
                "total_score": total_score,
                "originating_agent": candidate["preferred_agent"],
                "originating_confidence": originating_confidence,
                "constraint_findings": findings,
                "eligible": eligible,
                "eligibility_basis": eligibility_basis,
                "evidence_complete": evidence_complete,
            }
        )

    any_evidence_incomplete = any(not c["evidence_complete"] for c in evaluated_candidates)

    ranking = build_ranking(evaluated_candidates)

    ambiguity_block, tie_group_ids = evaluate_ambiguity(
        evaluated_candidates, policy["ambiguity"], case_confidence, supporting_signals, any_evidence_incomplete
    )

    for entry in ranking:
        entry["tie_group"] = 1 if entry["candidate_id"] in tie_group_ids else None

    constraints_checked = sorted(hc["id"] for hc in hard_constraints)
    violated_ids = sorted(
        {
            c["candidate_id"]
            for c in evaluated_candidates
            for f in c["constraint_findings"]
            if f["status"] == "VIOLATED"
        }
    )
    indeterminate_ids = sorted(
        {
            c["candidate_id"]
            for c in evaluated_candidates
            for f in c["constraint_findings"]
            if f["status"] == "INDETERMINATE"
        }
    )

    agent_evidence = {
        agent: {
            "proposed_action": agent_actions[agent].get("proposed_action"),
            "confidence": agent_actions[agent].get("confidence"),
        }
        for agent in contributing_agents
        if agent in agent_actions
    }

    return {
        "weigh_version": WEIGH_VERSION,
        "scoring_method": SCORING_METHOD,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "case": _build_case_block(resolve_output, case_context),
        "profile": profile,
        "evidence": {
            "contributing_agents": contributing_agents,
            "agent_evidence": agent_evidence,
            "case_confidence": case_confidence,
            "confidence_method": CONFIDENCE_METHOD,
            "confidence_inputs": confidence_inputs,
            "supporting_signals": supporting_signals,
            "evidence_complete": not any_evidence_incomplete,
        },
        "candidates": evaluated_candidates,
        "ranking": ranking,
        "ambiguity": ambiguity_block,
        "constraint_evaluation": {
            "authority": "advisory_only",
            "rechecked_by": "GOVERN",
            "constraints_checked": constraints_checked,
            "violated_candidate_ids": violated_ids,
            "indeterminate_candidate_ids": indeterminate_ids,
        },
        "notes": sorted(notes, key=lambda n: (n["code"], n.get("agent") or "", n.get("candidate_id") or "")),
    }
