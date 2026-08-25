"""
The Claude boundary (design §L, §M, §N).

The claim these tests exist to defend is the demo sentence:

    "Sentinel's governance decision is a deterministic function of policy.
     Claude explains it. Turn Claude off, and the same action executes for
     the same reason."

So: execution_authorized and decision_id are constant across every advisor
state, an advisor is never reachable on an authorizing path, and no advisory
content can override a constraint, grant authority, authorize an action,
change policy, or alter the deterministic ranking.
"""

import copy
import json

import pytest

from govern import decide
from govern.advisor import (
    NullAdvisor,
    _contains_forbidden_key,
    build_request,
    evaluate_gate,
    validate_advisory,
)
from govern.conftest import (
    MalformedAdvisor,
    NoneAdvisor,
    RaisingAdvisor,
    TimingOutAdvisor,
    ValidAdvisor,
    ViolatingAdvisor,
    no_conflict_release_case,
    payout_vs_dispute_case,
    real_policy,
    rto_vs_retention_case,
    valid_advisory,
)
from govern.errors import GovernPolicyError
from govern.schema import ADVISORY_VERSION


def _ambiguous_case():
    """§S.2 -- the only case shape on which the advisor gate opens."""
    return rto_vs_retention_case()


# --- the gate --------------------------------------------------------------


def test_advisor_is_not_invoked_without_one_injected():
    output = decide(*_ambiguous_case())
    assert output["claude"]["gate"]["eligible"] is False
    assert output["claude"]["gate"]["reasons"] == ["NO_ADVISOR_INJECTED"]
    assert output["claude"]["invoked"] is False


def test_null_advisor_is_treated_as_no_advisor():
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=NullAdvisor())

    assert output["claude"]["gate"]["reasons"] == ["NO_ADVISOR_INJECTED"]
    assert output["claude"]["invoked"] is False


def test_advisor_is_not_invoked_when_the_outcome_is_not_ambiguous():
    advisor = ValidAdvisor()
    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["outcome"] == "PROCEED"
    assert output["claude"]["gate"]["eligible"] is False
    assert "OUTCOME_NOT_AMBIGUOUS" in output["claude"]["gate"]["reasons"]
    assert "EXECUTION_AUTHORIZED" in output["claude"]["gate"]["reasons"]
    assert output["claude"]["invoked"] is False
    assert advisor.requests == []


def test_advisor_is_never_reached_on_an_authorizing_path():
    # The structural guarantee that must survive any future edit to the
    # decision table: an advisor cannot participate in an authorized decision.
    advisor = ValidAdvisor()
    for inputs in (payout_vs_dispute_case(), no_conflict_release_case(50000)):
        weigh_output, agent_actions, case_context, policy = inputs
        output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)
        assert output["execution_authorized"] is True
        assert output["claude"]["invoked"] is False
    assert advisor.requests == []


def test_each_gate_condition_independently_closes_the_gate():
    # Design §L.2: four conditions, each recorded by name when it fails.
    advisor = ValidAdvisor()
    clean = [[{"constraint_id": "HC_X", "status": "SATISFIED"}]]
    blocked = [[{"constraint_id": "HC_X", "status": "INDETERMINATE"}]]

    assert evaluate_gate("AMBIGUOUS", False, clean, advisor) == {
        "eligible": True,
        "reasons": [],
    }
    assert evaluate_gate("HOLD", False, clean, advisor)["reasons"] == [
        "OUTCOME_NOT_AMBIGUOUS"
    ]
    # Tightened beyond the policy prose to include INDETERMINATE: a case with
    # unverifiable evidence is not a case to ask a model about.
    assert evaluate_gate("AMBIGUOUS", False, blocked, advisor)["reasons"] == [
        "BLOCKING_CONSTRAINT_PRESENT"
    ]
    assert evaluate_gate("AMBIGUOUS", True, clean, advisor)["reasons"] == [
        "EXECUTION_AUTHORIZED"
    ]
    assert evaluate_gate("AMBIGUOUS", False, clean, None)["reasons"] == [
        "NO_ADVISOR_INJECTED"
    ]
    assert evaluate_gate("AMBIGUOUS", False, clean, NullAdvisor())["reasons"] == [
        "NO_ADVISOR_INJECTED"
    ]


def test_a_blocking_constraint_anywhere_closes_the_gate_end_to_end():
    # rto loses its authority entry, so the DEFER_TO_AGENT candidate is
    # VIOLATED and the advisor is unreachable for this case.
    advisor = ValidAdvisor()
    stripped = copy.deepcopy(real_policy())
    del stripped["authority"]["agents"]["rto"]

    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case(policy=stripped)
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert "BLOCKING_CONSTRAINT_PRESENT" in output["claude"]["gate"]["reasons"]
    assert output["claude"]["invoked"] is False
    assert advisor.requests == []


def test_gate_opens_only_when_all_four_conditions_hold():
    advisor = ValidAdvisor()
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["outcome"] == "AMBIGUOUS"
    assert output["execution_authorized"] is False
    assert output["claude"]["gate"] == {"eligible": True, "reasons": []}
    assert output["claude"]["invoked"] is True
    assert len(advisor.requests) == 1


def test_claude_invariants_are_reasserted_at_the_call_site():
    permissive = copy.deepcopy(real_policy())
    permissive["claude"]["may_override_authority"] = True

    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case(policy=permissive)
    with pytest.raises(GovernPolicyError, match="may_override_authority"):
        decide(weigh_output, agent_actions, case_context, policy, advisor=ValidAdvisor())


# --- what the advisor is allowed to see -----------------------------------


def test_advisor_request_is_redacted_and_whitelisted():
    advisor = ValidAdvisor()
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)
    request = advisor.requests[0]

    assert set(request) == {
        "advisory_request_version",
        "question",
        "case",
        "profile",
        "ambiguity_signals",
        "candidates",
        "constraint_summary",
    }
    assert set(request["case"]) == {"entity_type", "conflict"}

    def walk_keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from walk_keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk_keys(item)

    leaked = {
        "case_id",
        "merchant_id",
        "amount",
        "disputed_amount",
        "days_overdue",
        "rto_score",
        "churn_risk",
        "merchant_flags",
        "dispute_status",
        "customer_value_score",
        "agent_evidence",
    }
    assert set(walk_keys(request)) & leaked == set()
    # And the policy dict never leaves the process.
    assert "hard_constraints" not in json.dumps(request)


def test_advisor_only_sees_permitted_candidates():
    weigh_output, _agent_actions, _case_context, _policy = _ambiguous_case()
    permitted = [
        {
            "candidate_id": "defer_to_agent-1",
            "strategy": "DEFER_TO_AGENT",
            "resulting_actions": ["HOLD_ORDER"],
            "total_score": 0.63,
            "constraint_recheck": [{"constraint_id": "HC_CONFIDENCE_FLOOR", "status": "SATISFIED"}],
        }
    ]
    request = build_request(weigh_output, permitted)

    assert [c["candidate_id"] for c in request["candidates"]] == ["defer_to_agent-1"]
    assert set(request["candidates"][0]) == {
        "candidate_id",
        "strategy",
        "resulting_actions",
        "total_score",
        "objective_contributions",
    }
    assert request["constraint_summary"] == [
        {"constraint_id": "HC_CONFIDENCE_FLOOR", "status": "SATISFIED"}
    ]
    # The second candidate WEIGH scored is absent because it was not permitted.
    assert len(weigh_output["candidates"]) == 2


# --- parity: the whole point ----------------------------------------------


def _advisor_states():
    return [
        ("absent", None),
        ("null", NullAdvisor()),
        ("valid", ValidAdvisor()),
        ("returns_none", NoneAdvisor()),
        ("raises", RaisingAdvisor()),
        ("times_out", TimingOutAdvisor()),
        ("malformed", MalformedAdvisor()),
        ("violating", ViolatingAdvisor()),
    ]


def test_execution_authorized_and_decision_id_are_identical_across_advisor_states():
    results = {}
    for name, advisor in _advisor_states():
        weigh_output, agent_actions, case_context, policy = _ambiguous_case()
        output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)
        results[name] = (output["execution_authorized"], output["decision_id"])

    assert len(set(results.values())) == 1, results
    authorized, _decision_id = next(iter(results.values()))
    assert authorized is False


def test_outcome_is_identical_except_for_the_one_documented_transition():
    outcomes = {}
    for name, advisor in _advisor_states():
        weigh_output, agent_actions, case_context, policy = _ambiguous_case()
        outcomes[name] = decide(
            weigh_output, agent_actions, case_context, policy, advisor=advisor
        )["outcome"]

    assert outcomes["violating"] == "ESCALATE"
    del outcomes["violating"]
    assert set(outcomes.values()) == {"AMBIGUOUS"}


def test_a_valid_advisory_changes_nothing_but_the_claude_and_narrative_fields():
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    without = decide(weigh_output, agent_actions, case_context, policy)
    with_advisor = decide(
        *_ambiguous_case(), advisor=ValidAdvisor()
    )

    assert with_advisor["claude"]["output_used"] is True
    assert with_advisor["rationale"]["claude_narrative"] is not None

    stripped_with = copy.deepcopy(with_advisor)
    stripped_without = copy.deepcopy(without)
    for output in (stripped_with, stripped_without):
        output.pop("claude")
        output["rationale"].pop("claude_narrative")

    assert json.dumps(stripped_with, sort_keys=True) == json.dumps(
        stripped_without, sort_keys=True
    )


# --- failure containment ---------------------------------------------------


@pytest.mark.parametrize(
    "advisor,expected_error",
    [
        (NoneAdvisor(), "UNAVAILABLE"),
        (RaisingAdvisor(), "UNAVAILABLE"),
        (RaisingAdvisor(ValueError("bad json from the model")), "UNAVAILABLE"),
        (RaisingAdvisor(ConnectionError("dns failure")), "UNAVAILABLE"),
        (TimingOutAdvisor(), "TIMEOUT"),
        (MalformedAdvisor(), "INVALID_RESPONSE"),
        (ViolatingAdvisor(), "SCHEMA_VIOLATION"),
    ],
)
def test_every_advisor_failure_is_contained(advisor, expected_error):
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["claude"]["invoked"] is True
    assert output["claude"]["error"] == expected_error
    assert output["claude"]["output_used"] is False
    assert output["claude"]["advisory"] is None
    assert output["rationale"]["claude_narrative"] is None
    assert output["execution_authorized"] is False


@pytest.mark.parametrize(
    "advisor,expected_fallback",
    [
        (NoneAdvisor(), "HOLD"),
        (RaisingAdvisor(), "HOLD"),
        (TimingOutAdvisor(), "HOLD"),
        (MalformedAdvisor(), "HOLD"),
        (ViolatingAdvisor(), "ESCALATE"),
    ],
)
def test_fallback_vocabulary_is_bridged_onto_a_legal_outcome(advisor, expected_fallback):
    # policy.fallback speaks HOLD_FOR_REVIEW, which is not a member of
    # escalation.outcomes. It is aliased, never assigned to `outcome` raw.
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    assert policy["fallback"]["on_claude_unavailable"] == "HOLD_FOR_REVIEW"

    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["claude"]["fallback_applied"] == expected_fallback
    assert output["outcome"] in policy["escalation"]["outcomes"]
    assert output["outcome"] != "HOLD_FOR_REVIEW"


def test_non_schema_failures_leave_the_outcome_untouched():
    for advisor in (NoneAdvisor(), RaisingAdvisor(), TimingOutAdvisor(), MalformedAdvisor()):
        weigh_output, agent_actions, case_context, policy = _ambiguous_case()
        output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)
        assert output["outcome"] == "AMBIGUOUS"
        assert output["outcome_basis"] == "AMBIGUITY_DETECTED"
        assert any(note["code"] == "G_CLAUDE_FALLBACK_APPLIED" for note in output["notes"])


def test_schema_violation_escalates_but_never_authorizes():
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=ViolatingAdvisor())

    assert output["outcome"] == "ESCALATE"
    assert output["outcome_basis"] == "CLAUDE_SCHEMA_VIOLATION"
    assert output["execution_authorized"] is False
    assert output["selected_candidate"] is None
    assert output["authorized_actions"] == []
    assert "CLAUDE_SCHEMA_VIOLATION" in output["escalation"]["reasons"]
    assert any(note["code"] == "G_OUTCOME_TRANSITIONED" for note in output["notes"])


def test_schema_violation_transition_is_policy_driven():
    # Flip the policy fallback and the transition stops firing -- but the
    # outcome still authorizes nothing either way.
    lenient = copy.deepcopy(real_policy())
    lenient["fallback"]["on_schema_violation"] = "HOLD_FOR_REVIEW"

    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case(policy=lenient)
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=ViolatingAdvisor())

    assert output["claude"]["error"] == "SCHEMA_VIOLATION"
    assert output["claude"]["fallback_applied"] == "HOLD"
    assert output["outcome"] == "AMBIGUOUS"
    assert output["execution_authorized"] is False


def test_unmappable_fallback_token_raises_at_preflight():
    broken = copy.deepcopy(real_policy())
    broken["fallback"]["on_timeout"] = "PROCEED"

    weigh_output, agent_actions, case_context, policy = payout_vs_dispute_case(policy=broken)
    with pytest.raises(GovernPolicyError, match="on_timeout"):
        decide(weigh_output, agent_actions, case_context, policy)


# --- what an advisory can never do ----------------------------------------


def test_advisor_cannot_introduce_a_candidate():
    for suggested in ("hold_both_pending_review-99", "defer_to_agent-2", "", "anything"):
        advisor = ValidAdvisor(valid_advisory(suggested_candidate_id=suggested))
        weigh_output, agent_actions, case_context, policy = _ambiguous_case()
        output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

        assert output["claude"]["error"] == "SCHEMA_VIOLATION", suggested
        assert output["claude"]["advisory"] is None
        assert {
            c["candidate_id"] for c in output["permission_evaluation"]["candidates"]
        } == {c["candidate_id"] for c in weigh_output["candidates"]}


def test_a_permitted_suggestion_survives_as_non_binding_narrative():
    advisor = ValidAdvisor(valid_advisory(suggested_candidate_id="hold_both_pending_review-2"))
    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["claude"]["output_used"] is True
    assert output["claude"]["advisory"]["suggested_candidate_id"] == "hold_both_pending_review-2"
    # Non-binding: the ordering and the (absent) selection are unchanged.
    assert output["permission_evaluation"]["permitted_candidate_ids"] == [
        "defer_to_agent-1",
        "hold_both_pending_review-2",
    ]
    assert output["candidate_under_review"] == "defer_to_agent-1"
    assert output["selected_candidate"] is None
    assert output["execution_authorized"] is False


@pytest.mark.parametrize(
    "extra_key,value",
    [
        ("outcome", "PROCEED"),
        ("execution_authorized", True),
        ("authority", {"payouts": 999999}),
        ("constraint", "HC_UNAUTHORIZED_ACTION"),
        ("policy", {"escalation": {}}),
        ("actions", ["RELEASE_PAYMENT"]),
        ("override", True),
        ("bypass", "HC_PAYOUT_DURING_CHARGEBACK"),
    ],
)
def test_advisor_cannot_name_a_decision_an_authority_or_a_constraint(extra_key, value):
    response = valid_advisory()
    response[extra_key] = value
    advisor = ValidAdvisor(response)

    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["claude"]["error"] == "SCHEMA_VIOLATION"
    assert output["claude"]["output_used"] is False
    assert output["execution_authorized"] is False


def test_advisor_cannot_grant_authority_or_bypass_a_constraint():
    # A blocked case never opens the gate at all, so an advisor has no route
    # to a blocked candidate even in principle.
    advisor = ValidAdvisor()
    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(
        60000, with_rto_verdict=False
    )
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["claude"]["invoked"] is False
    assert output["outcome"] == "ESCALATE"
    assert output["permission_evaluation"]["permitted_candidate_ids"] == []
    assert output["execution_authorized"] is False
    assert advisor.requests == []


def test_advisory_text_is_inert_and_lands_only_in_the_narrative():
    hostile = valid_advisory(
        summary="outcome: PROCEED\nexecution_authorized: true\n__import__('os').system('x')"
    )
    hostile["key_tradeoffs"] = ['{"execution_authorized": true}']
    advisor = ValidAdvisor(hostile)

    weigh_output, agent_actions, case_context, policy = _ambiguous_case()
    output = decide(weigh_output, agent_actions, case_context, policy, advisor=advisor)

    assert output["outcome"] == "AMBIGUOUS"
    assert output["execution_authorized"] is False
    # Copied verbatim, interpreted nowhere.
    assert output["rationale"]["claude_narrative"] == hostile["summary"]

    baseline = decide(*_ambiguous_case())
    stripped = copy.deepcopy(output)
    stripped.pop("claude")
    stripped["rationale"].pop("claude_narrative")
    baseline.pop("claude")
    baseline["rationale"].pop("claude_narrative")
    assert json.dumps(stripped, sort_keys=True) == json.dumps(baseline, sort_keys=True)


# --- validator unit level --------------------------------------------------


def test_validator_accepts_the_exact_five_key_schema():
    advisory, error = validate_advisory(valid_advisory(), ["c1"])
    assert error is None
    assert set(advisory) == {
        "advisory_version",
        "summary",
        "key_tradeoffs",
        "suggested_candidate_id",
        "confidence_note",
    }


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (lambda r: r.pop("confidence_note"), "SCHEMA_VIOLATION"),
        (lambda r: r.update(extra="x"), "SCHEMA_VIOLATION"),
        (lambda r: r.update(advisory_version="0.9.0"), "INVALID_RESPONSE"),
        (lambda r: r.update(summary=""), "INVALID_RESPONSE"),
        (lambda r: r.update(summary="x" * 501), "INVALID_RESPONSE"),
        (lambda r: r.update(summary=123), "INVALID_RESPONSE"),
        (lambda r: r.update(key_tradeoffs="not a list"), "INVALID_RESPONSE"),
        (lambda r: r.update(key_tradeoffs=["ok"] * 6), "INVALID_RESPONSE"),
        (lambda r: r.update(key_tradeoffs=["x" * 201]), "INVALID_RESPONSE"),
        (lambda r: r.update(confidence_note="x" * 201), "INVALID_RESPONSE"),
        (lambda r: r.update(suggested_candidate_id="unknown"), "SCHEMA_VIOLATION"),
    ],
)
def test_validator_rejects_malformed_and_overreaching_responses(mutate, expected):
    response = valid_advisory()
    mutate(response)
    advisory, error = validate_advisory(response, ["c1"])
    assert advisory is None
    assert error == expected


def test_validator_rejects_non_dict_responses():
    for raw in ("a string", 42, [], None, True):
        advisory, error = validate_advisory(raw, ["c1"])
        assert advisory is None
        assert error == "SCHEMA_VIOLATION"


def test_forbidden_key_walk_reaches_any_depth():
    # Defence in depth: with the five-key schema and its type bounds, a
    # nested dict cannot actually survive far enough to reach this walk
    # today. It is asserted directly so that a future widening of the
    # advisory schema cannot quietly open that door.
    assert _contains_forbidden_key({"summary": "fine"}) is False
    assert _contains_forbidden_key({"a": {"b": [{"execution_authorized": True}]}}) is True
    assert _contains_forbidden_key([{"nested": {"authority": {}}}]) is True
    # A key that merely CONTAINS a forbidden word is not itself forbidden --
    # matching is exact, so `suggested_candidate_id` stays legal.
    assert _contains_forbidden_key({"suggested_candidate_id": "c1"}) is False


def test_minimal_valid_advisory_is_accepted():
    minimal = {
        "advisory_version": ADVISORY_VERSION,
        "summary": "s",
        "key_tradeoffs": [],
        "suggested_candidate_id": None,
        "confidence_note": None,
    }
    advisory, error = validate_advisory(minimal, ["c1"])
    assert error is None
    assert advisory == minimal
