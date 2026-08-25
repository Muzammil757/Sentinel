"""
Phase 2 -- authority enforcement (design §H).

This is the half of governance WEIGH deliberately never touched: the two
policy lists (`actions_requiring_governance`, `actions_requiring_escalation`)
that WEIGH does not read at all, plus the per-agent facts that turn
HC_UNAUTHORIZED_ACTION's re-check into an auditable authority record.

The module lives on its own **because** authority is precisely what WEIGH
reported and GOVERN enforces -- the WEIGH/GOVERN boundary is visible in the
file tree.

Per-agent limits are not derived a second time here. Phase 1 already
re-derived them from raw evidence via the shared HC_UNAUTHORIZED_ACTION
evaluator; this module re-labels that record into authority vocabulary
(AUTHORIZED / NOT_AUTHORIZED / INDETERMINATE) and adds the two gates on top.
The verified boundary is inclusive: the violation test is
`amount > max_autonomous_amount`, so 50 000 is authorized and 50 001 is not.
"""

from govern.schema import (
    AUTHORITY_INDETERMINATE,
    AUTHORITY_NOT_AUTHORIZED,
    AUTHORITY_RESULT_FROM_CONSTRAINT_STATUS,
)

# Reasons weigh.constraints._eval_unauthorized_action emits when it actually
# compared an amount against a cap, or proved no cap applies. Anything else
# means the amount limit was never reached.
_AMOUNT_LIMIT_EVALUATED_REASONS = frozenset(
    {"no_amount_limit", "within_amount_limit", "amount_exceeds_max_autonomous_amount"}
)


def _per_action_authority(unauthorized_observed: dict) -> dict:
    per_action = {}
    for action in sorted(unauthorized_observed):
        entry = unauthorized_observed[action]
        per_action[action] = {
            "agent": entry.get("agent"),
            "result": AUTHORITY_RESULT_FROM_CONSTRAINT_STATUS.get(
                entry.get("result"), AUTHORITY_INDETERMINATE
            ),
            "reason": entry.get("reason"),
        }
    return per_action


def _escalation_matches(strategy: str, resulting_actions: list, policy: dict) -> list:
    """
    Design §H.2. `authority.actions_requiring_escalation` currently holds
    HOLD_BOTH_PENDING_REVIEW, which is a RESOLVE *strategy*, not an action --
    matching it against resulting_actions alone matches nothing, ever. GOVERN
    therefore matches the list against strategy AND actions, and also reads
    the optional `strategies_requiring_escalation` field proposed in design
    §R.3, so behaviour is identical before and after that policy correction.
    """

    authority = policy["authority"]
    requiring = set(authority.get("actions_requiring_escalation") or [])
    requiring_strategies = set(authority.get("strategies_requiring_escalation") or [])

    matches = {f"action:{action}" for action in resulting_actions if action in requiring}
    if strategy in requiring or strategy in requiring_strategies:
        matches.add(f"strategy:{strategy}")
    return sorted(matches)


def _governance_gate(gated_actions: list, per_action: dict, policy: dict) -> dict:
    """
    Design §H.3. `actions_requiring_governance` must mean something stronger
    than "don't skip governance" -- GOVERN never skips governance for anyone --
    so for these actions, having run governance must be *provable in the
    receipt*, not merely true.

    `all_determinate` is the blocking signal and mirrors §G.2: it is false
    exactly when a gated action's authority verdict is INDETERMINATE, i.e.
    GOVERN could not establish whether the action is authorized. A determinate
    NOT_AUTHORIZED is a governed answer, and blocks via the constraint code
    rather than being mislabelled indeterminate. `checks_run` records what
    GOVERN was actually able to establish, so the receipt can be read without
    re-deriving anything.
    """

    authority_agents = policy["authority"]["agents"]

    originating_agent_resolved = True
    authority_entry_found = True
    amount_limit_evaluated = True
    all_determinate = True

    for action in gated_actions:
        entry = per_action.get(action, {})
        agent = entry.get("agent")
        reason = entry.get("reason")

        if agent is None:
            originating_agent_resolved = False
        if agent is None or agent not in authority_agents:
            authority_entry_found = False
        if reason not in _AMOUNT_LIMIT_EVALUATED_REASONS:
            amount_limit_evaluated = False
        if entry.get("result", AUTHORITY_INDETERMINATE) == AUTHORITY_INDETERMINATE:
            all_determinate = False

    return {
        "gated_actions": list(gated_actions),
        "checks_run": {
            # Phase 1 ran before this module was reachable, for every
            # candidate, with no short-circuit for any case shape.
            "constraint_recheck_performed": True,
            "originating_agent_resolved": originating_agent_resolved,
            "authority_entry_found": authority_entry_found,
            "amount_limit_evaluated": amount_limit_evaluated,
        },
        "all_determinate": all_determinate,
    }


def evaluate_authority(
    weigh_candidate: dict, unauthorized_observed: dict, policy: dict
) -> tuple[dict, dict, list]:
    """
    Returns (authority_block, governance_gate_or_None, gate_blocking_codes).

    A candidate flagged by `actions_requiring_escalation` stays *permitted*:
    it remains in the ordered set and can be candidate_under_review. What it
    can never be is autonomously executed -- the case-level ESCALATE fires
    only when the flagged candidate is permitted[0] (design §H.2, D3).
    """

    resulting_actions = list(weigh_candidate["resulting_actions"])
    per_action = _per_action_authority(unauthorized_observed)
    matches = _escalation_matches(weigh_candidate["strategy"], resulting_actions, policy)

    requiring_governance = set(
        policy["authority"].get("actions_requiring_governance") or []
    )
    gated_actions = sorted({a for a in resulting_actions if a in requiring_governance})

    governance_gate = None
    gate_blocking_codes = []
    if gated_actions:
        governance_gate = _governance_gate(gated_actions, per_action, policy)
        if not governance_gate["all_determinate"]:
            gate_blocking_codes = sorted(
                f"GOVERNANCE_GATE_INDETERMINATE:{action}"
                for action in gated_actions
                if per_action.get(action, {}).get("result", AUTHORITY_INDETERMINATE)
                == AUTHORITY_INDETERMINATE
            )

    authority_block = {
        "per_action": per_action,
        "requires_governance_actions": gated_actions,
        "requires_escalation": bool(matches),
        # The design names a singular `escalation_match` in the receipt
        # schema; a candidate can in principle match on both its strategy and
        # an action, so the full list is kept alongside it rather than lost.
        "escalation_match": matches[0] if matches else None,
        "escalation_matches": matches,
    }

    return authority_block, governance_gate, gate_blocking_codes


def authority_exceeded_codes(authority_block: dict) -> list:
    """
    Sorted `AUTHORITY_EXCEEDED:<AGENT>:<ACTION>` codes for the receipt
    (design §K). Only a determinate NOT_AUTHORIZED with a known originating
    agent produces one -- an unattributable action is reported through the
    constraint's INDETERMINATE code instead.
    """

    codes = set()
    for action, entry in authority_block["per_action"].items():
        if entry["result"] == AUTHORITY_NOT_AUTHORIZED and entry["agent"] is not None:
            codes.add(f"AUTHORITY_EXCEEDED:{entry['agent']}:{action}")
    return sorted(codes)
