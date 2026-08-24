from weigh.confidence import compute_case_confidence, resolve_originating_confidence


def _agents(a_confidence, b_confidence):
    return {
        "agent_a": {"agent": "agent_a", "proposed_action": "X", "confidence": a_confidence},
        "agent_b": {"agent": "agent_b", "proposed_action": "Y", "confidence": b_confidence},
    }


def test_blend_formula_matches_design_worked_example():
    # design §H.2: {0.40, 0.95}, alpha=0.5 -> 0.5375
    case_confidence, inputs, missing = compute_case_confidence(
        ["agent_a", "agent_b"], _agents(0.40, 0.95), alpha=0.5
    )

    assert case_confidence == 0.5375
    assert inputs["min"] == 0.40
    assert inputs["mean"] == 0.675
    assert missing == []


def test_alpha_one_is_pure_worst_case():
    case_confidence, _inputs, _missing = compute_case_confidence(
        ["agent_a", "agent_b"], _agents(0.40, 0.95), alpha=1.0
    )
    assert case_confidence == 0.40


def test_alpha_zero_is_pure_mean():
    case_confidence, _inputs, _missing = compute_case_confidence(
        ["agent_a", "agent_b"], _agents(0.40, 0.95), alpha=0.0
    )
    assert case_confidence == 0.675


def test_single_contributing_agent_is_identity():
    case_confidence, _inputs, _missing = compute_case_confidence(["agent_a"], _agents(0.72, 0.10), alpha=0.5)
    assert case_confidence == 0.72


def test_blend_is_never_degenerate_max_or_min():
    # The rejected "mean floored by min" formulations collapse to one term.
    # This blend must sit strictly between min and mean when the inputs differ.
    case_confidence, inputs, _missing = compute_case_confidence(
        ["agent_a", "agent_b"], _agents(0.40, 0.95), alpha=0.5
    )
    assert inputs["min"] < case_confidence < inputs["mean"]


def test_blend_is_monotone_non_decreasing_in_each_input():
    lower, _i1, _m1 = compute_case_confidence(["agent_a", "agent_b"], _agents(0.40, 0.95), alpha=0.5)
    higher, _i2, _m2 = compute_case_confidence(["agent_a", "agent_b"], _agents(0.50, 0.95), alpha=0.5)
    assert higher >= lower


def test_missing_confidence_is_treated_as_zero_and_reported():
    payloads = {
        "agent_a": {"agent": "agent_a", "proposed_action": "X"},  # no confidence field
        "agent_b": {"agent": "agent_b", "proposed_action": "Y", "confidence": 0.90},
    }

    case_confidence, inputs, missing = compute_case_confidence(["agent_a", "agent_b"], payloads, alpha=0.5)

    assert missing == ["agent_a"]
    assert inputs["min"] == 0.0
    assert case_confidence == round(0.5 * 0.0 + 0.5 * 0.45, 4)


def test_invalid_confidence_values_are_treated_as_zero():
    for bad_value in [True, "high", -0.1, 1.1, None]:
        payloads = {
            "agent_a": {"agent": "agent_a", "proposed_action": "X", "confidence": bad_value},
            "agent_b": {"agent": "agent_b", "proposed_action": "Y", "confidence": 0.80},
        }
        _case_confidence, inputs, missing = compute_case_confidence(["agent_a", "agent_b"], payloads, alpha=0.5)
        assert missing == ["agent_a"], bad_value
        assert inputs["min"] == 0.0, bad_value


def test_originating_confidence_uses_preferred_agent():
    payloads = _agents(0.40, 0.95)
    value = resolve_originating_confidence("agent_b", payloads, case_confidence=0.5375)
    assert value == 0.95


def test_originating_confidence_falls_back_to_case_confidence_when_no_preferred_agent():
    payloads = _agents(0.40, 0.95)
    value = resolve_originating_confidence(None, payloads, case_confidence=0.5375)
    assert value == 0.5375


def test_originating_confidence_missing_agent_confidence_is_zero():
    payloads = {"agent_a": {"agent": "agent_a", "proposed_action": "X"}}
    value = resolve_originating_confidence("agent_a", payloads, case_confidence=0.5)
    assert value == 0.0
