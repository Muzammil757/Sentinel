import copy
import builtins

import pytest
import yaml

from policy.loader import (
    DEFAULT_POLICY_PATH,
    REQUIRED_HARD_CONSTRAINT_IDS,
    REQUIRED_OBJECTIVES,
    REQUIRED_WEIGHT_PROFILES,
    PolicyValidationError,
    compute_policy_hash,
    load_policy,
)


def _raw_policy_dict() -> dict:
    """A validation-free copy of the default policy, safe to mutate for negative tests."""
    with DEFAULT_POLICY_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _write_policy(tmp_path, policy_dict, name="policy_bundle.yaml"):
    policy_path = tmp_path / name
    policy_path.write_text(yaml.safe_dump(policy_dict, sort_keys=False), encoding="utf-8")
    return policy_path


def test_load_default_policy():
    policy = load_policy()

    assert isinstance(policy, dict)
    assert policy["policy"]["policy_id"] == "sentinel_demo_policy_v1"


def test_required_sections_present():
    policy = load_policy()

    required_sections = {
        "policy",
        "objectives",
        "weights",
        "profile_selection",
        "hard_constraints",
        "authority",
        "escalation",
        "ambiguity",
        "claude",
        "fallback",
        "audit",
    }

    assert required_sections.issubset(policy.keys())


def test_objectives_are_complete():
    policy = load_policy()

    assert REQUIRED_OBJECTIVES.issubset(policy["objectives"].keys())


def test_weight_profiles_are_valid():
    policy = load_policy()
    profiles = policy["weights"]["profiles"]

    assert REQUIRED_WEIGHT_PROFILES.issubset(profiles.keys())

    objective_names = set(policy["objectives"].keys())

    for profile_name in REQUIRED_WEIGHT_PROFILES:
        profile = profiles[profile_name]
        assert set(profile.keys()) == objective_names

        total = 0.0
        for weight in profile.values():
            assert isinstance(weight, (int, float)) and not isinstance(weight, bool)
            assert 0.0 <= weight <= 1.0
            total += weight

        assert abs(total - 1.0) <= 0.01


def test_required_hard_constraints_present():
    policy = load_policy()
    ids = {constraint["id"] for constraint in policy["hard_constraints"]}

    assert REQUIRED_HARD_CONSTRAINT_IDS.issubset(ids)


def test_policy_rejects_missing_required_section(tmp_path):
    broken = _raw_policy_dict()
    del broken["hard_constraints"]

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_policy_rejects_invalid_weight(tmp_path):
    broken = _raw_policy_dict()
    broken["weights"]["profiles"]["standard"]["financial_exposure_prevention"] = "very high"

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_policy_rejects_invalid_weight_out_of_range(tmp_path):
    broken = _raw_policy_dict()
    broken["weights"]["profiles"]["standard"]["financial_exposure_prevention"] = 5.0

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_policy_rejects_invalid_constraint(tmp_path):
    broken = _raw_policy_dict()
    del broken["hard_constraints"][0]["description"]

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_policy_rejects_constraint_missing_required_id(tmp_path):
    broken = _raw_policy_dict()
    broken["hard_constraints"] = [
        constraint
        for constraint in broken["hard_constraints"]
        if constraint["id"] != "HC_CONFIDENCE_FLOOR"
    ]

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_policy_hash_is_deterministic():
    policy_1 = load_policy()
    policy_2 = load_policy()

    assert compute_policy_hash(policy_1) == compute_policy_hash(policy_2)


def test_policy_hash_changes_when_policy_changes():
    policy = load_policy()
    changed = copy.deepcopy(policy)
    changed["weights"]["profiles"]["standard"]["operational_cost"] = 0.09
    changed["weights"]["profiles"]["standard"]["merchant_trust"] = 0.16

    assert compute_policy_hash(policy) != compute_policy_hash(changed)


def test_no_eval_or_dynamic_execution(tmp_path, monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("policy loading must never call eval()/exec()")

    monkeypatch.setattr(builtins, "eval", _forbidden)
    monkeypatch.setattr(builtins, "exec", _forbidden)

    # Loading the real default policy must not touch eval/exec.
    load_policy()

    # A policy carrying a string that *looks* like executable code must be
    # treated as inert data, never interpreted.
    tricky = _raw_policy_dict()
    tricky["profile_selection"]["rules"].append(
        {"when": {"note": "__import__('os').system('echo pwned')"}, "profile": "standard"}
    )
    tricky_path = _write_policy(tmp_path, tricky)

    loaded = load_policy(tricky_path)
    injected_note = loaded["profile_selection"]["rules"][-1]["when"]["note"]
    assert injected_note == "__import__('os').system('echo pwned')"


def test_yaml_python_object_tags_are_rejected(tmp_path):
    malicious_yaml = "policy: !!python/object/apply:os.system ['echo pwned']\n"
    malicious_path = tmp_path / "policy_bundle.yaml"
    malicious_path.write_text(malicious_yaml, encoding="utf-8")

    with pytest.raises(PolicyValidationError):
        load_policy(malicious_path)


def test_claude_policy_is_bounded():
    policy = load_policy()
    claude = policy["claude"]

    assert claude["may_invent_candidates"] is False
    assert claude["may_bypass_hard_constraints"] is False
    assert claude["may_override_authority"] is False
    assert claude["may_directly_execute_actions"] is False


def test_claude_policy_rejects_unbounded_capability(tmp_path):
    broken = _raw_policy_dict()
    broken["claude"]["may_bypass_hard_constraints"] = True

    broken_path = _write_policy(tmp_path, broken)

    with pytest.raises(PolicyValidationError):
        load_policy(broken_path)


def test_demo_policy_values_are_documented_as_sentinel_values():
    policy = load_policy()
    disclaimer = policy["policy"]["metadata"]["disclaimer"].lower()

    assert "sentinel" in disclaimer
    assert "demo" in disclaimer
    assert "do not represent razorpay" in disclaimer
