import hashlib
import json
from pathlib import Path
from typing import Optional, Union

import yaml
from jsonschema import Draft202012Validator

_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_POLICY_PATH = _PACKAGE_DIR / "policy_bundle.yaml"
SCHEMA_PATH = _PACKAGE_DIR / "policy_schema.json"

REQUIRED_OBJECTIVES = {
    "financial_exposure_prevention",
    "fraud_risk_reduction",
    "compliance_risk_reduction",
    "merchant_trust",
    "operational_cost",
}

REQUIRED_WEIGHT_PROFILES = {"standard", "high_risk_merchant", "trusted_merchant"}

REQUIRED_HARD_CONSTRAINT_IDS = {
    "HC_PAYOUT_DURING_CHARGEBACK",
    "HC_THIRDWATCH_HIGH_RISK_PAYOUT",
    "HC_RETENTION_TO_FLAGGED_MERCHANT",
    "HC_CONFIDENCE_FLOOR",
    "HC_UNAUTHORIZED_ACTION",
}

CLAUDE_FORBIDDEN_CAPABILITY_FLAGS = (
    "may_invent_candidates",
    "may_bypass_hard_constraints",
    "may_override_authority",
    "may_directly_execute_actions",
)

REQUIRED_FALLBACK_KEYS = {
    "on_claude_unavailable",
    "on_invalid_response",
    "on_timeout",
    "on_schema_violation",
}

# Fallback behavior must always be conservative: never PROCEED without
# governance having actually run.
CONSERVATIVE_FALLBACK_ACTIONS = {"HOLD_FOR_REVIEW", "ESCALATE"}

MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0
WEIGHT_SUM_TOLERANCE = 0.01

_schema_cache = None


class PolicyValidationError(ValueError):
    """Raised when a policy bundle is structurally or semantically invalid."""


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
            _schema_cache = json.load(fh)
    return _schema_cache


def _validate_schema(policy: dict) -> None:
    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(policy), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = "policy" + "".join(f"[{step!r}]" for step in first.absolute_path)
        raise PolicyValidationError(
            f"Policy schema validation failed at {location}: {first.message}"
        )


def _validate_objectives(policy: dict) -> None:
    objective_names = set(policy["objectives"].keys())
    missing = REQUIRED_OBJECTIVES - objective_names
    if missing:
        raise PolicyValidationError(
            f"objectives is missing required objective(s): {sorted(missing)}"
        )


def _validate_weights(policy: dict) -> None:
    profiles = policy["weights"]["profiles"]
    missing_profiles = REQUIRED_WEIGHT_PROFILES - profiles.keys()
    if missing_profiles:
        raise PolicyValidationError(
            f"weights.profiles is missing required profile(s): {sorted(missing_profiles)}"
        )

    objective_names = set(policy["objectives"].keys())

    for profile_name in REQUIRED_WEIGHT_PROFILES:
        profile = profiles[profile_name]
        profile_keys = set(profile.keys())
        if profile_keys != objective_names:
            raise PolicyValidationError(
                f"weights.profiles.{profile_name} keys {sorted(profile_keys)} "
                f"do not match objectives {sorted(objective_names)}"
            )

        total = 0.0
        for objective_name, weight in profile.items():
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                raise PolicyValidationError(
                    f"weights.profiles.{profile_name}.{objective_name} must be "
                    f"numeric, got {weight!r}"
                )
            if not (MIN_WEIGHT <= weight <= MAX_WEIGHT):
                raise PolicyValidationError(
                    f"weights.profiles.{profile_name}.{objective_name} = {weight} "
                    f"is outside the allowed range [{MIN_WEIGHT}, {MAX_WEIGHT}]"
                )
            total += weight

        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise PolicyValidationError(
                f"weights.profiles.{profile_name} weights sum to {total}, "
                f"expected 1.0 (+/- {WEIGHT_SUM_TOLERANCE})"
            )


def _validate_hard_constraints(policy: dict) -> None:
    constraints = policy["hard_constraints"]
    ids = [constraint.get("id") for constraint in constraints]

    if len(ids) != len(set(ids)):
        raise PolicyValidationError("hard_constraints contains duplicate id(s)")

    missing = REQUIRED_HARD_CONSTRAINT_IDS - set(ids)
    if missing:
        raise PolicyValidationError(
            f"hard_constraints is missing required id(s): {sorted(missing)}"
        )

    for constraint in constraints:
        for field in ("id", "description", "enforcement"):
            value = constraint.get(field)
            if not isinstance(value, str) or not value.strip():
                raise PolicyValidationError(
                    f"hard_constraint {constraint.get('id', '<unknown>')} has an "
                    f"invalid or missing '{field}'"
                )


def _validate_authority(policy: dict) -> None:
    agents = policy["authority"]["agents"]
    if not agents:
        raise PolicyValidationError("authority.agents must define at least one agent")


def _validate_ambiguity(policy: dict) -> None:
    ambiguity = policy["ambiguity"]
    for key in ("near_tie_threshold", "low_confidence_threshold"):
        value = ambiguity[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0 <= value <= 1):
            raise PolicyValidationError(
                f"ambiguity.{key} must be a number between 0 and 1, got {value!r}"
            )


def _validate_claude(policy: dict) -> None:
    claude = policy["claude"]
    for flag in CLAUDE_FORBIDDEN_CAPABILITY_FLAGS:
        if claude.get(flag) is not False:
            raise PolicyValidationError(
                f"claude.{flag} must be explicitly set to false; Sentinel policy "
                f"forbids this capability"
            )


def _validate_fallback(policy: dict) -> None:
    fallback = policy["fallback"]
    for key in REQUIRED_FALLBACK_KEYS:
        action = fallback[key]
        if action not in CONSERVATIVE_FALLBACK_ACTIONS:
            raise PolicyValidationError(
                f"fallback.{key} = {action!r} must be one of "
                f"{sorted(CONSERVATIVE_FALLBACK_ACTIONS)} (fallback must stay conservative)"
            )


def _validate_metadata_disclaimer(policy: dict) -> None:
    disclaimer = policy["policy"]["metadata"].get("disclaimer", "")
    lowered = disclaimer.lower()
    if "sentinel" not in lowered or "demo" not in lowered:
        raise PolicyValidationError(
            "policy.metadata.disclaimer must clearly identify these as Sentinel "
            "demo policy values, not a real payment processor's internal policy"
        )


def load_policy(path: Optional[Union[str, Path]] = None) -> dict:
    """
    Load and validate the Sentinel governance policy bundle.

    Locates policy_bundle.yaml relative to this package (regardless of the
    current working directory) unless an explicit path is given, parses it
    with yaml.safe_load (no arbitrary object construction, no eval/exec),
    validates it against policy_schema.json, then runs the business-level
    checks that are impractical to express purely in JSON Schema. Raises
    PolicyValidationError with a deterministic message on any failure.
    Never fills in missing values and never mutates the loaded structure.
    """

    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH

    if not policy_path.is_file():
        raise PolicyValidationError(f"Policy file not found: {policy_path}")

    try:
        with policy_path.open("r", encoding="utf-8") as fh:
            policy = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise PolicyValidationError(f"Policy file is not valid YAML: {exc}") from exc

    if not isinstance(policy, dict):
        raise PolicyValidationError("Policy file must contain a top-level mapping/object")

    _validate_schema(policy)
    _validate_objectives(policy)
    _validate_weights(policy)
    _validate_hard_constraints(policy)
    _validate_authority(policy)
    _validate_ambiguity(policy)
    _validate_claude(policy)
    _validate_fallback(policy)
    _validate_metadata_disclaimer(policy)

    return policy


def compute_policy_hash(policy: dict) -> str:
    """
    Deterministic SHA-256 hash of a policy's canonical JSON form.

    Lets a future Decision Receipt identify exactly which policy content
    governed a decision. Not a cryptographic signature -- HMAC/signing is
    out of scope for this phase.
    """

    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
