from weigh.errors import WeighPolicyError


def select_profile(case_context: dict, policy: dict) -> dict:
    """
    Deterministic, first-match weight-profile selection (design §L).

    case_context supplies plain governance facts (e.g. merchant_risk_tier);
    it is never inferred from agent evidence. Rules are evaluated in the
    order policy declares them; the first rule whose "when" key/value pairs
    all match case_context wins. An empty "when" matches everything.
    """

    rules = policy["profile_selection"]["rules"]
    profiles = policy["weights"]["profiles"]

    for index, rule in enumerate(rules):
        when = rule["when"]
        if all(case_context.get(key) == value for key, value in when.items()):
            profile_name = rule["profile"]
            weights = profiles.get(profile_name)
            if weights is None:
                raise WeighPolicyError(
                    f"profile_selection.rules[{index}] selects profile "
                    f"{profile_name!r}, which is not defined in weights.profiles"
                )
            return {
                "profile_name": profile_name,
                "reason": "matched_rule",
                "matched_rule_index": index,
                "matched_rule": {"when": dict(when), "profile": profile_name},
                "weights": dict(sorted(weights.items())),
            }

    default_profile = policy["profile_selection"]["default_profile"]
    weights = profiles.get(default_profile)
    if weights is None:
        raise WeighPolicyError(
            f"profile_selection.default_profile = {default_profile!r} is not "
            f"defined in weights.profiles"
        )

    return {
        "profile_name": default_profile,
        "reason": "default",
        "matched_rule_index": None,
        "matched_rule": None,
        "weights": dict(sorted(weights.items())),
    }
