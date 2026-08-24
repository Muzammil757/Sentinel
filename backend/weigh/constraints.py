"""
Advisory hard-constraint evaluation (design §I).

Every finding here is advisory: WEIGH reports what it observed, but GOVERN
independently re-derives constraint status from policy and raw evidence and
is the sole enforcement point. Nothing in this module executes an action,
enforces authority, or overrides a constraint -- it only marks candidates
ineligible for a high score to route around.

Statuses:
  NOT_APPLICABLE  the guarded action isn't present in this candidate
  SATISFIED       checked against present evidence; constraint holds
  VIOLATED        checked against present evidence; constraint breached
  INDETERMINATE   the guarded action is present but evidence to check it is missing

Both VIOLATED and INDETERMINATE block eligibility (§I.3) -- an unverifiable
constraint is never silently treated as satisfied.
"""

from weigh.errors import WeighPolicyError

FLAGGED_MERCHANT_FLAGS = {"FRAUD_REVIEW", "COMPLIANCE_REVIEW"}


def _finding(constraint: dict, status: str, predicate: str, observed: dict) -> dict:
    return {
        "constraint_id": constraint["id"],
        "status": status,
        "enforcement": constraint["enforcement"],
        "predicate": predicate,
        "observed": observed,
        "parameters": dict(constraint.get("parameters") or {}),
        "advisory": True,
    }


def _eval_payout_during_chargeback(candidate, agent_actions, case_context, constraint, policy, originating_confidence):
    predicate = (
        "'RELEASE_PAYMENT' in candidate.resulting_actions AND "
        "dispute.dispute_status in {OPEN, UNDER_REVIEW}"
    )
    if "RELEASE_PAYMENT" not in candidate["resulting_actions"]:
        return _finding(constraint, "NOT_APPLICABLE", predicate, {})

    dispute = agent_actions.get("dispute")
    dispute_status = dispute.get("dispute_status") if dispute else None
    if not isinstance(dispute_status, str) or not dispute_status:
        return _finding(
            constraint, "INDETERMINATE", predicate, {"dispute.dispute_status": dispute_status}
        )

    status = "VIOLATED" if dispute_status.upper() in {"OPEN", "UNDER_REVIEW"} else "SATISFIED"
    return _finding(constraint, status, predicate, {"dispute.dispute_status": dispute_status.upper()})


def _eval_thirdwatch_high_risk_payout(candidate, agent_actions, case_context, constraint, policy, originating_confidence):
    """
    Design §I.8: defers to the RTO agent's own published verdict
    (proposed_action == "HOLD_ORDER") rather than re-deriving a risk band
    from rto_score. Re-thresholding rto_score here would create a second
    risk classifier that can silently disagree with the agent that owns
    the question -- exactly the Open Track boundary this layer must not
    cross.
    """

    predicate = "'RELEASE_PAYMENT' in candidate.resulting_actions AND rto.proposed_action == 'HOLD_ORDER'"
    if "RELEASE_PAYMENT" not in candidate["resulting_actions"]:
        return _finding(constraint, "NOT_APPLICABLE", predicate, {})

    rto = agent_actions.get("rto")
    rto_action = rto.get("proposed_action") if rto else None
    if not isinstance(rto_action, str) or not rto_action:
        return _finding(constraint, "INDETERMINATE", predicate, {"rto.proposed_action": rto_action})

    status = "VIOLATED" if rto_action == "HOLD_ORDER" else "SATISFIED"
    return _finding(constraint, status, predicate, {"rto.proposed_action": rto_action})


def _eval_retention_to_flagged_merchant(candidate, agent_actions, case_context, constraint, policy, originating_confidence):
    predicate = (
        "'WIN_BACK_OFFER' in candidate.resulting_actions AND "
        "case_context.merchant_flags intersects {FRAUD_REVIEW, COMPLIANCE_REVIEW}"
    )
    if "WIN_BACK_OFFER" not in candidate["resulting_actions"]:
        return _finding(constraint, "NOT_APPLICABLE", predicate, {})

    if "merchant_flags" not in case_context:
        return _finding(constraint, "INDETERMINATE", predicate, {"case_context.merchant_flags": None})

    flags = case_context["merchant_flags"]
    if not isinstance(flags, list):
        return _finding(constraint, "INDETERMINATE", predicate, {"case_context.merchant_flags": flags})

    status = "VIOLATED" if FLAGGED_MERCHANT_FLAGS.intersection(flags) else "SATISFIED"
    return _finding(constraint, status, predicate, {"case_context.merchant_flags": list(flags)})


def _eval_confidence_floor(candidate, agent_actions, case_context, constraint, policy, originating_confidence):
    """
    Design §I.5: no action, no violation. A candidate with empty
    resulting_actions (e.g. HOLD_BOTH_PENDING_REVIEW) is NOT_APPLICABLE
    here regardless of confidence -- weak evidence must never make the
    conservative fallback itself ineligible.
    """

    predicate = (
        "candidate.resulting_actions is non-empty AND "
        "originating_confidence < hard_constraints.HC_CONFIDENCE_FLOOR.parameters.min_confidence"
    )
    if not candidate["resulting_actions"]:
        return _finding(constraint, "NOT_APPLICABLE", predicate, {})

    min_confidence = (constraint.get("parameters") or {}).get("min_confidence")
    if isinstance(min_confidence, bool) or not isinstance(min_confidence, (int, float)):
        raise WeighPolicyError(
            f"hard_constraints.{constraint['id']}.parameters.min_confidence must be "
            f"numeric, got {min_confidence!r}"
        )

    status = "VIOLATED" if originating_confidence < min_confidence else "SATISFIED"
    observed = {"originating_confidence": originating_confidence, "min_confidence": min_confidence}
    return _finding(constraint, status, predicate, observed)


def _eval_unauthorized_action(candidate, agent_actions, case_context, constraint, policy, originating_confidence):
    """
    Attributes each resulting action to the agent that proposed it (via
    agent_actions), then checks that action against
    authority.agents[agent].autonomous_actions and max_autonomous_amount.
    An agent with no authority.agents entry is treated as having no
    autonomous actions at all (VIOLATED, not INDETERMINATE -- absence of
    an authority entry is a determinate "not authorized"). An amount limit
    that applies but has no corresponding "amount" field on the agent's
    payload is INDETERMINATE (e.g. retention's 5000 cap; the mock
    retention agent publishes no amount field).
    """

    predicate = (
        "each resulting action is listed in its originating agent's "
        "authority.agents[agent].autonomous_actions, and its amount (if any) "
        "does not exceed authority.agents[agent].max_autonomous_amount"
    )
    resulting_actions = candidate["resulting_actions"]
    if not resulting_actions:
        return _finding(constraint, "NOT_APPLICABLE", predicate, {})

    authority_agents = policy["authority"]["agents"]

    action_to_agents: dict = {}
    for agent_name, payload in agent_actions.items():
        action = payload.get("proposed_action")
        if action:
            action_to_agents.setdefault(action, []).append(agent_name)

    per_action = {}
    statuses = []
    for action in resulting_actions:
        owners = action_to_agents.get(action, [])
        if len(owners) != 1:
            per_action[action] = {"agent": None, "result": "INDETERMINATE", "reason": "ambiguous_or_unknown_originating_agent"}
            statuses.append("INDETERMINATE")
            continue

        agent = owners[0]
        agent_authority = authority_agents.get(agent)
        if agent_authority is None:
            per_action[action] = {"agent": agent, "result": "VIOLATED", "reason": "agent_has_no_authority_entry"}
            statuses.append("VIOLATED")
            continue

        allowed_actions = agent_authority.get("autonomous_actions", [])
        if action not in allowed_actions:
            per_action[action] = {"agent": agent, "result": "VIOLATED", "reason": "action_not_in_autonomous_actions"}
            statuses.append("VIOLATED")
            continue

        max_amount = agent_authority.get("max_autonomous_amount")
        if max_amount is None:
            per_action[action] = {"agent": agent, "result": "SATISFIED", "reason": "no_amount_limit"}
            statuses.append("SATISFIED")
            continue

        amount = agent_actions.get(agent, {}).get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            per_action[action] = {"agent": agent, "result": "INDETERMINATE", "reason": "amount_required_but_missing"}
            statuses.append("INDETERMINATE")
            continue

        if amount > max_amount:
            per_action[action] = {"agent": agent, "result": "VIOLATED", "reason": "amount_exceeds_max_autonomous_amount"}
            statuses.append("VIOLATED")
        else:
            per_action[action] = {"agent": agent, "result": "SATISFIED", "reason": "within_amount_limit"}
            statuses.append("SATISFIED")

    if "VIOLATED" in statuses:
        overall = "VIOLATED"
    elif "INDETERMINATE" in statuses:
        overall = "INDETERMINATE"
    else:
        overall = "SATISFIED"

    return _finding(constraint, overall, predicate, {"per_action": per_action})


CONSTRAINT_EVALUATORS = {
    "HC_PAYOUT_DURING_CHARGEBACK": _eval_payout_during_chargeback,
    "HC_THIRDWATCH_HIGH_RISK_PAYOUT": _eval_thirdwatch_high_risk_payout,
    "HC_RETENTION_TO_FLAGGED_MERCHANT": _eval_retention_to_flagged_merchant,
    "HC_CONFIDENCE_FLOOR": _eval_confidence_floor,
    "HC_UNAUTHORIZED_ACTION": _eval_unauthorized_action,
}


def evaluate_constraints_for_candidate(
    candidate, agent_actions, case_context, hard_constraints, policy, originating_confidence
):
    findings = []
    for index, constraint in enumerate(hard_constraints):
        evaluator = CONSTRAINT_EVALUATORS[constraint["id"]]
        finding = evaluator(candidate, agent_actions, case_context, constraint, policy, originating_confidence)
        finding["source"] = f"policy.hard_constraints[{index}]"
        findings.append(finding)

    eligible = not any(f["status"] in ("VIOLATED", "INDETERMINATE") for f in findings)
    return findings, eligible
