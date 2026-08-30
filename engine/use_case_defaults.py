import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"

with open(_DATA_DIR / "usecases.json") as f:
    _usecases_data = json.load(f)


def get_use_case(use_case_id):
    """Look up a use case definition by id. Raises if not found."""
    for uc in _usecases_data["useCases"]:
        if uc["id"] == use_case_id:
            return uc
    raise ValueError(f"Unknown use case id: {use_case_id}")


def get_all_use_cases():
    return _usecases_data["useCases"]


def get_priority_weights(priority_key):
    weights = _usecases_data["priorityWeightProfiles"].get(priority_key)
    if weights is None:
        raise ValueError(f"Unknown priority profile: {priority_key}")
    return weights


def get_adoption_scenarios():
    return _usecases_data["adoptionScenarios"]


def get_priority_weight_profiles():
    return _usecases_data["priorityWeightProfiles"]


def resolve_assumptions(use_case, overrides=None):
    """
    Merge a use case's defaults with any user-provided overrides.
    Only fields explicitly present (and not None) in `overrides` replace the
    default — keeps this function pure and predictable, and tags each
    resolved value with its source (default vs. user-provided) so the UI can
    show that provenance if useful.
    """
    overrides = overrides or {}

    def resolve(key, default_key):
        has_override = overrides.get(key) is not None
        return {
            "value": overrides[key] if has_override else use_case[default_key],
            "source": "user-provided" if has_override else "default",
        }

    return {
        "input_tokens": resolve("input_tokens", "defaultInputTokens"),
        "output_tokens": resolve("output_tokens", "defaultOutputTokens"),
        "success_rate": resolve("success_rate", "defaultSuccessRate"),
        "min_model_tier": use_case["minModelTier"],
        "complexity_tier": use_case["complexityTier"],
    }
