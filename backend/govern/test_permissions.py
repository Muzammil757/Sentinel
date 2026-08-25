"""
Phase 1: the independent hard-constraint re-check (design §G).

The load-bearing claims here are that GOVERN re-derives constraint status
from RAW evidence rather than reading weigh_output's findings, that
INDETERMINATE blocks exactly like VIOLATED, and that any disagreement between
the two layers is itself blocking.
"""

import copy

from govern import decide
from govern.conftest import (
    build_case,
    no_conflict_release_case,
    payout_vs_dispute_case,
    real_policy,
    rto_vs_retention_case,
)
from govern.permissions import blocking_constraint_codes, recheck_candidate


def _record(output, candidate_id):
    return next(
        record
        for record in output["permission_evaluation"]["candidates"]
        if record["candidate_id"] == candidate_id
    )


def _status(record, constraint_id):
    return next(
        entry["status"]
        for entry in record["constraint_recheck"]
        if entry["constraint_id"] == constraint_id
    )


# --- every required hard constraint is re-derived --------------------------


def test_every_policy_hard_constraint_is_rechecked_for_every_candidate():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    expected = [hc["id"] for hc in policy["hard_constraints"]]
    assert output["permission_evaluation"]["constraints_checked"] == sorted(expected)
    for record in output["permission_evaluation"]["candidates"]:
        assert [e["constraint_id"] for e in record["constraint_recheck"]] == expected


def test_recheck_reads_raw_evidence_not_weigh_findings():
    # Blank out WEIGH's findings entirely. GOVERN must still arrive at the
    # same statuses, because it re-derives them from agent_actions.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    truthful = decide(weigh_output, agent_actions, case_context, policy)

    blanked = copy.deepcopy(weigh_output)
    for candidate in blanked["candidates"]:
        candidate["constraint_findings"] = []
    stripped = decide(blanked, agent_actions, case_context, policy)

    truthful_record = _record(truthful, "defer_to_agent-1")
    stripped_record = _record(stripped, "defer_to_agent-1")
    assert [e["status"] for e in stripped_record["constraint_recheck"]] == [
        e["status"] for e in truthful_record["constraint_recheck"]
    ]
    # ...and blanked findings are themselves a disagreement, which escalates.
    assert stripped["outcome"] == "ESCALATE"
    assert stripped["outcome_basis"] == "GOVERN_WEIGH_DISAGREEMENT"


def test_confidence_floor_is_recomputed_from_the_originating_agents_payload():
    # 0.60 satisfies (inclusive floor); 0.59 violates. GOVERN reads the
    # dispute agent's own confidence out of agent_actions, not out of WEIGH.
    for confidence, expected in [(0.60, "SATISFIED"), (0.59, "VIOLATED")]:
        weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
        agent_actions["dispute"]["confidence"] = confidence
        weigh_candidate = next(
            c for c in weigh_output["candidates"] if c["candidate_id"] == "defer_to_agent-1"
        )
        recheck, _per_action, _disagreements = recheck_candidate(
            weigh_candidate,
            agent_actions,
            case_context,
            policy,
            weigh_output["evidence"]["case_confidence"],
        )
        status = next(
            e["status"] for e in recheck if e["constraint_id"] == "HC_CONFIDENCE_FLOOR"
        )
        assert status == expected, confidence


def test_payout_during_chargeback_blocks_a_release_on_an_open_dispute():
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(10000)
    agent_actions["dispute"]["dispute_status"] = "OPEN"

    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "no_conflict_proceed-1")

    assert _status(record, "HC_PAYOUT_DURING_CHARGEBACK") == "VIOLATED"
    assert record["permitted"] is False
    assert "HC_PAYOUT_DURING_CHARGEBACK:VIOLATED" in record["blocking_reasons"]
    assert output["outcome"] == "ESCALATE"
    assert output["execution_authorized"] is False


def test_thirdwatch_blocks_a_release_when_rto_published_a_hold():
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(10000)
    agent_actions["rto"]["proposed_action"] = "HOLD_ORDER"

    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "no_conflict_proceed-1")

    assert _status(record, "HC_THIRDWATCH_HIGH_RISK_PAYOUT") == "VIOLATED"
    assert output["outcome"] == "ESCALATE"


def test_retention_to_flagged_merchant_blocks_a_win_back_offer():
    rto = {"agent": "rto", "proposed_action": "HOLD_ORDER", "confidence": 0.95}
    retention = {
        "agent": "retention",
        "proposed_action": "WIN_BACK_OFFER",
        "confidence": 0.95,
        "amount": 1000,
    }
    weigh_output, agent_actions, case_context, policy = build_case(
        rto, retention, "customer", {"merchant_flags": ["FRAUD_REVIEW"]}
    )
    # The winning candidate defers to rto, so WIN_BACK_OFFER is not in any
    # candidate's actions and the constraint is NOT_APPLICABLE -- which is
    # itself worth pinning, since it is why this constraint rarely fires.
    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "defer_to_agent-1")
    assert _status(record, "HC_RETENTION_TO_FLAGGED_MERCHANT") == "NOT_APPLICABLE"

    # Evaluated directly against a candidate that DOES carry the action, the
    # flagged merchant blocks it.
    win_back_candidate = {
        "candidate_id": "synthetic-win-back",
        "strategy": "DEFER_TO_AGENT",
        "preferred_agent": "retention",
        "resulting_actions": ["WIN_BACK_OFFER"],
        "constraint_findings": [],
    }
    recheck, _per_action, _d = recheck_candidate(
        win_back_candidate, agent_actions, case_context, policy, 0.95
    )
    status = next(
        e["status"] for e in recheck if e["constraint_id"] == "HC_RETENTION_TO_FLAGGED_MERCHANT"
    )
    assert status == "VIOLATED"


# --- INDETERMINATE blocks exactly like VIOLATED ---------------------------


def test_no_conflict_does_not_bypass_constraints():
    # Design §S.3 Variant B and the single most important safety claim in the
    # demo: with no RTO verdict in evidence at all, a benign 10 000 release
    # is NOT permitted. Missing evidence is not read as absence of risk.
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(
        10000, with_rto_verdict=False
    )
    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "no_conflict_proceed-1")

    assert _status(record, "HC_THIRDWATCH_HIGH_RISK_PAYOUT") == "INDETERMINATE"
    observed = next(
        entry["observed"]
        for entry in record["constraint_recheck"]
        if entry["constraint_id"] == "HC_THIRDWATCH_HIGH_RISK_PAYOUT"
    )
    assert observed == {"rto.proposed_action": None}
    assert record["permitted"] is False
    assert "HC_THIRDWATCH_HIGH_RISK_PAYOUT:INDETERMINATE" in record["blocking_reasons"]
    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "NO_PERMITTED_CANDIDATE"
    assert output["execution_authorized"] is False
    assert output["authorized_actions"] == []


def test_indeterminate_blocks_at_every_amount():
    # The score is 0.3100 at every amount and the band is never read on a
    # no-conflict case, so if INDETERMINATE did not block, all four of these
    # would release.
    for amount in (10000, 50000, 50001, 60000):
        output = decide(*no_conflict_release_case(amount, with_rto_verdict=False))
        assert output["outcome"] == "ESCALATE", amount
        assert output["execution_authorized"] is False, amount


def test_constrained_candidate_can_never_become_the_final_action():
    for amount in (50001, 60000):
        weigh_output, agent_actions, case_context, policy = no_conflict_release_case(amount)
        output = decide(weigh_output, agent_actions, case_context, policy)

        assert output["permission_evaluation"]["permitted_candidate_ids"] == []
        assert output["selected_candidate"] is None
        assert output["candidate_under_review"] is None
        assert output["authorized_actions"] == []
        assert output["execution_authorized"] is False


# --- the union rule and the disagreement rule -----------------------------


def test_weigh_blocking_finding_blocks_even_when_govern_clears_it():
    # Blocked is the UNION of both layers. A candidate WEIGH blocked and
    # GOVERN cleared is still not permitted.
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    candidate = next(
        c for c in tampered["candidates"] if c["candidate_id"] == "defer_to_agent-1"
    )
    finding = next(
        f for f in candidate["constraint_findings"] if f["constraint_id"] == "HC_CONFIDENCE_FLOOR"
    )
    finding["status"] = "VIOLATED"

    output = decide(tampered, agent_actions, case_context, policy)
    record = _record(output, "defer_to_agent-1")

    assert _status(record, "HC_CONFIDENCE_FLOOR") == "SATISFIED"  # GOVERN cleared it
    assert record["permitted"] is False  # ...and it is still blocked
    assert "HC_CONFIDENCE_FLOOR:VIOLATED" in record["blocking_reasons"]


def test_govern_weigh_disagreement_escalates():
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    tampered = copy.deepcopy(weigh_output)
    candidate = next(
        c for c in tampered["candidates"] if c["candidate_id"] == "defer_to_agent-1"
    )
    finding = next(
        f for f in candidate["constraint_findings"] if f["constraint_id"] == "HC_CONFIDENCE_FLOOR"
    )
    finding["status"] = "VIOLATED"

    output = decide(tampered, agent_actions, case_context, policy)
    agreement = output["permission_evaluation"]["weigh_agreement"]

    assert agreement["agreed"] is False
    assert agreement["disagreements"] == [
        {
            "candidate_id": "defer_to_agent-1",
            "constraint_id": "HC_CONFIDENCE_FLOOR",
            "govern_status": "SATISFIED",
            "weigh_status": "VIOLATED",
        }
    ]
    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "GOVERN_WEIGH_DISAGREEMENT"
    assert output["execution_authorized"] is False
    assert (
        "GOVERN_WEIGH_DISAGREEMENT:defer_to_agent-1:HC_CONFIDENCE_FLOOR"
        in output["escalation"]["reasons"]
    )
    assert any(note["code"] == "G_WEIGH_DISAGREEMENT" for note in output["notes"])


def test_agreement_is_recorded_per_constraint_per_candidate():
    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case()
    output = decide(weigh_output, agent_actions, case_context, policy)

    for record in output["permission_evaluation"]["candidates"]:
        for entry in record["constraint_recheck"]:
            assert entry["agrees"] is True
            assert entry["weigh_status"] == entry["status"]
    assert output["permission_evaluation"]["weigh_agreement"] == {
        "agreed": True,
        "disagreements": [],
    }


# --- unit level ------------------------------------------------------------


def test_blocking_constraint_codes_unions_both_layers():
    recheck = [
        {"constraint_id": "HC_A", "status": "SATISFIED"},
        {"constraint_id": "HC_B", "status": "INDETERMINATE"},
    ]
    weigh_candidate = {
        "constraint_findings": [
            {"constraint_id": "HC_A", "status": "VIOLATED"},
            {"constraint_id": "HC_B", "status": "SATISFIED"},
        ]
    }
    assert blocking_constraint_codes(recheck, weigh_candidate) == [
        "HC_A:VIOLATED",
        "HC_B:INDETERMINATE",
    ]


def test_all_candidates_blocked_escalates_but_still_reports_every_candidate():
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(60000)
    output = decide(weigh_output, agent_actions, case_context, policy)

    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "NO_PERMITTED_CANDIDATE"
    assert "NO_PERMITTED_CANDIDATE" in output["escalation"]["reasons"]
    # Nothing is dropped from the receipt just because it was blocked.
    assert len(output["permission_evaluation"]["candidates"]) == len(weigh_output["candidates"])
    for record in output["permission_evaluation"]["candidates"]:
        assert record["blocking_reasons"]
        assert record["permission_basis"].startswith("blocked_by:")


def test_policy_can_relax_the_confidence_floor_without_a_code_change():
    strict = copy.deepcopy(real_policy())
    strict_hc = next(
        hc for hc in strict["hard_constraints"] if hc["id"] == "HC_CONFIDENCE_FLOOR"
    )
    strict_hc["parameters"]["min_confidence"] = 0.96

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=strict)
    output = decide(weigh_output, agent_actions, case_context, policy)
    record = _record(output, "defer_to_agent-1")

    # 0.95 confidence now falls below a 0.96 floor -- one policy number moved.
    assert _status(record, "HC_CONFIDENCE_FLOOR") == "VIOLATED"
    assert record["permitted"] is False
    assert output["outcome"] == "ESCALATE"
