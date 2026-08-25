"""
The mock action registry.

Two things matter here: the registry speaks the project's real action
vocabulary (nothing invented, nothing missing), and performing an action is a
pure deterministic lookup with no side effect of any kind.
"""

import copy

import pytest

from executor.actions import (
    SUPPORTED_ACTIONS,
    is_supported,
    perform,
    perform_all,
    registry_snapshot,
    unsupported,
)
from policy.loader import load_policy


def test_registry_covers_the_projects_action_vocabulary():
    # The vocabulary is the policy's, not EXECUTOR's: every action the policy
    # bundle prices in scoring.action_effects can be carried out, and EXECUTOR
    # invents no action the rest of the system has never heard of.
    priced = set(load_policy()["scoring"]["action_effects"])
    assert set(SUPPORTED_ACTIONS) == priced


def test_registry_covers_every_action_the_mock_agents_propose():
    from mock_agents.disputes import generate_dispute_action
    from mock_agents.payouts import generate_payout_action
    from mock_agents.retention import generate_retention_action
    from mock_agents.rto import generate_rto_action

    proposed = {
        generate_payout_action("v1", 1000, "inv1", 9)["proposed_action"],
        generate_dispute_action("d1", "o1", "OPEN", 100)["proposed_action"],
        generate_dispute_action("d1", "o1", "CLOSED", 0)["proposed_action"],
        generate_rto_action("o1", "c1", 0.9, "IN_TRANSIT")["proposed_action"],
        generate_rto_action("o1", "c1", 0.6, "IN_TRANSIT")["proposed_action"],
        generate_rto_action("o1", "c1", 0.1, "IN_TRANSIT")["proposed_action"],
        generate_retention_action("c1", "o1", 0.9, 0.9)["proposed_action"],
        generate_retention_action("c1", "o1", 0.9, 0.6)["proposed_action"],
        generate_retention_action("c1", "o1", 0.9, 0.1)["proposed_action"],
    }
    assert proposed <= set(SUPPORTED_ACTIONS)


@pytest.mark.parametrize("action", sorted(SUPPORTED_ACTIONS))
def test_every_entry_is_complete(action):
    entry = SUPPORTED_ACTIONS[action]
    assert set(entry) == {"effect", "target", "detail"}
    assert all(isinstance(value, str) and value for value in entry.values())


def test_effects_are_distinguishable():
    # Two different actions never report the same effect, so a receipt reader
    # can tell from the effect alone what was actually done.
    effects = [entry["effect"] for entry in SUPPORTED_ACTIONS.values()]
    assert len(set(effects)) == len(effects)


@pytest.mark.parametrize("action", sorted(SUPPORTED_ACTIONS))
def test_perform_is_deterministic(action):
    assert perform(action) == perform(action)


def test_perform_returns_a_fresh_record_each_time():
    # A caller editing one effect record must not corrupt the registry or any
    # other receipt.
    first = perform("HOLD_ORDER")
    first["effect"] = "TAMPERED"
    assert perform("HOLD_ORDER")["effect"] == "ORDER_HELD"
    assert SUPPORTED_ACTIONS["HOLD_ORDER"]["effect"] == "ORDER_HELD"


def test_perform_all_preserves_the_authorized_order():
    performed = perform_all(["RELEASE_PAYMENT", "CLOSE_CASE"])
    assert [entry["action"] for entry in performed] == ["RELEASE_PAYMENT", "CLOSE_CASE"]

    reversed_order = perform_all(["CLOSE_CASE", "RELEASE_PAYMENT"])
    assert [entry["action"] for entry in reversed_order] == ["CLOSE_CASE", "RELEASE_PAYMENT"]


def test_unknown_action_raises_rather_than_being_skipped():
    # perform() is reached only past the ladder. If a caller ever gets here
    # with an unknown action that is a bug, and a bug must not become a silent
    # non-execution.
    with pytest.raises(KeyError):
        perform("WIRE_MONEY_ANYWHERE")


@pytest.mark.parametrize(
    "action", ["WIRE_MONEY_ANYWHERE", "release_payment", "", None, 42, ["RELEASE_PAYMENT"]]
)
def test_is_supported_is_exact(action):
    # Case-sensitive and type-strict: 'release_payment' is not RELEASE_PAYMENT.
    assert is_supported(action) is False


def test_unsupported_reports_sorted_unique_unknowns():
    assert unsupported(["CLOSE_CASE", "B_ACTION", "A_ACTION", "B_ACTION"]) == [
        "A_ACTION",
        "B_ACTION",
    ]
    assert unsupported(["CLOSE_CASE", "HOLD_ORDER"]) == []


def test_registry_snapshot_cannot_be_used_to_edit_the_registry():
    snapshot = registry_snapshot()
    snapshot["RELEASE_PAYMENT"]["effect"] = "TAMPERED"
    assert SUPPORTED_ACTIONS["RELEASE_PAYMENT"]["effect"] == "PAYOUT_RELEASE_SIMULATED"


def test_registry_is_not_mutated_by_use():
    before = copy.deepcopy(SUPPORTED_ACTIONS)
    perform_all(sorted(SUPPORTED_ACTIONS))
    assert SUPPORTED_ACTIONS == before
