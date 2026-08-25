"""
Phase 1 -- the independent hard-constraint re-check (design §G).

This is where "don't trust weigh_output" lives. GOVERN re-derives every
constraint status by running the shared evaluators against RAW
agent_actions / case_context / policy, and treats
weigh_output.candidates[].constraint_findings purely as a value to compare
against.

Why re-run weigh.constraints rather than reimplement it (design §G.1): the
independence that matters here is independence *from weigh_output*, not
independence from the evaluator code. A second hand-written copy of the five
predicates would be ~150 lines whose realistic failure mode -- the two copies
drifting apart -- is worse than the failure it guards against. The threat this
re-check defends against is a weigh_output that is stale, hand-edited,
replayed under a different policy, or corrupted in transit, and re-running the
evaluators from raw evidence catches all four.

One value is read from weigh_output rather than re-derived: case_confidence.
Re-deriving it would require policy.scoring.confidence.min_weight, and design
§D.3 puts the whole `scoring` section off-limits to GOVERN -- re-reading
WEIGH's scoring inputs is how re-scoring starts. case_confidence only reaches
a constraint for candidates with no preferred_agent; every candidate that
names an acting agent has its confidence read straight from that agent's raw
payload.

Blocked is the UNION of both layers' blocking sets, and any per-constraint
disagreement is itself blocking and forces ESCALATE upstream (§C.2, D2). Two
independent layers must agree before anything executes.
"""

from govern.errors import GovernPolicyError
from govern.schema import (
    BLOCKING_CONSTRAINT_STATUSES,
    UNAUTHORIZED_ACTION_CONSTRAINT_ID,
)
from weigh.confidence import resolve_originating_confidence
from weigh.constraints import evaluate_constraints_for_candidate
from weigh.errors import WeighPolicyError


def _weigh_statuses(weigh_candidate: dict) -> dict:
    return {
        finding["constraint_id"]: finding["status"]
        for finding in weigh_candidate["constraint_findings"]
        if isinstance(finding, dict) and "constraint_id" in finding
    }


def recheck_candidate(
    weigh_candidate: dict,
    agent_actions: dict,
    case_context: dict,
    policy: dict,
    case_confidence: float,
) -> tuple[list, dict, list]:
    """
    Re-derive every hard constraint for one candidate from raw evidence.

    Returns (constraint_recheck, unauthorized_action_observed, disagreements).
    `unauthorized_action_observed` is HC_UNAUTHORIZED_ACTION's per-action
    detail, which Phase 2 re-labels into authority vocabulary rather than
    deriving a second time.
    """

    # A minimal projection, so the evaluators cannot read anything WEIGH
    # computed -- only what RESOLVE declared about the candidate.
    candidate = {
        "candidate_id": weigh_candidate["candidate_id"],
        "strategy": weigh_candidate["strategy"],
        "preferred_agent": weigh_candidate["preferred_agent"],
        "resulting_actions": list(weigh_candidate["resulting_actions"]),
    }

    originating_confidence = resolve_originating_confidence(
        candidate["preferred_agent"], agent_actions, case_confidence
    )

    try:
        findings, _eligible = evaluate_constraints_for_candidate(
            candidate,
            agent_actions,
            case_context,
            policy["hard_constraints"],
            policy,
            originating_confidence,
        )
    except WeighPolicyError as exc:
        # A policy gap surfacing inside a shared evaluator is still a policy
        # gap. Design §Q: policy gaps raise, and they raise as GOVERN's own
        # error type so callers need not know which layer noticed.
        raise GovernPolicyError(
            f"hard-constraint re-check for candidate "
            f"{candidate['candidate_id']!r} could not run: {exc}"
        ) from exc

    weigh_status_by_id = _weigh_statuses(weigh_candidate)

    constraint_recheck = []
    disagreements = []
    unauthorized_observed = {}

    for finding in findings:
        constraint_id = finding["constraint_id"]
        govern_status = finding["status"]
        weigh_status = weigh_status_by_id.get(constraint_id)
        agrees = govern_status == weigh_status

        constraint_recheck.append(
            {
                "constraint_id": constraint_id,
                "status": govern_status,
                "observed": finding["observed"],
                "weigh_status": weigh_status,
                "agrees": agrees,
            }
        )

        if not agrees:
            disagreements.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "constraint_id": constraint_id,
                    "govern_status": govern_status,
                    "weigh_status": weigh_status,
                }
            )

        if constraint_id == UNAUTHORIZED_ACTION_CONSTRAINT_ID:
            unauthorized_observed = finding["observed"].get("per_action", {})

    return constraint_recheck, unauthorized_observed, disagreements


def blocking_constraint_codes(constraint_recheck: list, weigh_candidate: dict) -> list:
    """
    The union of both layers' blocking findings, as sorted machine codes
    (`HC_<ID>:<STATUS>`).

    A candidate WEIGH blocked and GOVERN cleared is still not permitted, and
    vice versa (design §C.2). VIOLATED and INDETERMINATE both block -- an
    unverifiable constraint is never read as satisfied (§G.2).
    """

    codes = set()

    for entry in constraint_recheck:
        if entry["status"] in BLOCKING_CONSTRAINT_STATUSES:
            codes.add(f"{entry['constraint_id']}:{entry['status']}")

    for finding in weigh_candidate["constraint_findings"]:
        if finding.get("status") in BLOCKING_CONSTRAINT_STATUSES:
            codes.add(f"{finding['constraint_id']}:{finding['status']}")

    return sorted(codes)
