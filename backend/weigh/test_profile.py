import copy

import pytest

from policy.loader import load_policy
from weigh.errors import WeighPolicyError
from weigh.profile import select_profile


def _policy():
    return load_policy()


def test_first_matching_rule_wins():
    policy = _policy()
    case_context = {"merchant_risk_tier": "high", "merchant_trust_tier": "trusted"}

    profile = select_profile(case_context, policy)

    assert profile["profile_name"] == "high_risk_merchant"
    assert profile["reason"] == "matched_rule"
    assert profile["matched_rule_index"] == 0


def test_second_rule_matches_when_first_does_not():
    policy = _policy()
    case_context = {"merchant_trust_tier": "trusted"}

    profile = select_profile(case_context, policy)

    assert profile["profile_name"] == "trusted_merchant"
    assert profile["matched_rule_index"] == 1


def test_falls_back_to_default_profile_when_no_rule_matches():
    policy = _policy()

    profile = select_profile({}, policy)

    assert profile["profile_name"] == "standard"
    assert profile["reason"] == "default"
    assert profile["matched_rule_index"] is None
    assert profile["matched_rule"] is None


def test_exact_match_only_no_partial_or_type_coercion():
    policy = _policy()
    # Wrong value for the tier -- must not match.
    case_context = {"merchant_risk_tier": "HIGH"}

    profile = select_profile(case_context, policy)

    assert profile["profile_name"] == "standard"


def test_extra_case_context_keys_are_ignored():
    policy = _policy()
    case_context = {"merchant_risk_tier": "high", "unrelated_field": "whatever"}

    profile = select_profile(case_context, policy)

    assert profile["profile_name"] == "high_risk_merchant"


def test_weights_dict_is_sorted_and_matches_policy():
    policy = _policy()

    profile = select_profile({}, policy)

    assert list(profile["weights"].keys()) == sorted(profile["weights"].keys())
    assert profile["weights"] == dict(policy["weights"]["profiles"]["standard"])


def test_unknown_profile_named_by_rule_raises_policy_error():
    policy = _policy()
    policy["profile_selection"]["rules"][0]["profile"] = "nonexistent_profile"

    with pytest.raises(WeighPolicyError):
        select_profile({"merchant_risk_tier": "high"}, policy)


def test_unknown_default_profile_raises_policy_error():
    policy = _policy()
    policy["profile_selection"]["default_profile"] = "nonexistent_profile"

    with pytest.raises(WeighPolicyError):
        select_profile({}, policy)


def test_selection_does_not_mutate_policy():
    policy = _policy()
    before = copy.deepcopy(policy)

    select_profile({"merchant_risk_tier": "high"}, policy)

    assert policy == before
