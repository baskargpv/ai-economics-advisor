"""
Stage 1: hard constraints. A model that fails any constraint is eliminated
outright — it never enters the weighted score, regardless of how cheap or
capable it is otherwise. This is what stops a cheap-but-unqualified model
from winning on cost alone, and stops an over-qualified frontier model from
always winning by default.
"""

TIER_RANK = {
    "cheap": 0,
    "mid": 1,
    "frontier": 2,
    "frontier-extended": 3,
}

_COMPLEXITY_TO_REQUIRED_RANK = {
    "simple": 0,
    "simple-moderate": 0,
    "moderate": 1,
    "moderate-complex": 1,
    "complex": 2,
}


def filter_by_min_tier(models, min_model_tier):
    """models: pricing.json's `models` list. Returns models meeting or exceeding min_model_tier."""
    if not min_model_tier:
        return models
    min_rank = TIER_RANK[min_model_tier]
    return [m for m in models if TIER_RANK[m["tier"]] >= min_rank]


def filter_by_data_sensitivity(models, _data_sensitivity):
    """
    Placeholder for data-residency/compliance filtering. pricing.json doesn't
    yet model per-provider region/compliance flags — this function exists so
    the constraint is visible in the pipeline and easy to wire up later
    rather than silently absent. For now it's a pass-through and says so.
    """
    # TODO: once pricing.json carries region/compliance metadata per model,
    # eliminate models that can't meet the stated data-sensitivity requirement.
    return models


def _capability_fit_score(model_tier, complexity_tier):
    model_rank = TIER_RANK[model_tier]
    required_rank = _COMPLEXITY_TO_REQUIRED_RANK.get(complexity_tier, 1)

    if model_rank < required_rank:
        return 0  # shouldn't happen post-filter, but defensive
    if model_rank == required_rank:
        return 1  # exactly meets the bar
    # Above the bar: small, diminishing credit only — this is what stops the
    # most powerful model from automatically winning every time.
    return 1 - (model_rank - required_rank) * 0.15


def score_model(model, blended_cost_per_request, max_cost_per_request, complexity_tier, weights):
    """
    Honest limitation: pricing.json currently carries pricing/tier/context
    data only — no independent capability, latency, or deployment benchmark
    data (deliberately deferred to a live capability-score lookup, e.g.
    Artificial Analysis, rather than invented here). So:
      - capability_fit is a step function derived from tier vs. the use
        case's complexity tier (a real, if coarse, signal)
      - cost_efficiency is a real, computed number (inverse of blended cost)
      - latency_fit and deployment_fit are neutral placeholders (0.5) until
        real benchmark/deployment data is wired in
    """
    capability_fit = _capability_fit_score(model["tier"], complexity_tier)

    cost_efficiency = 1 - blended_cost_per_request / max_cost_per_request if max_cost_per_request > 0 else 1

    latency_fit = 0.5  # placeholder — see docstring
    deployment_fit = 0.5  # placeholder — see docstring

    score = (
        capability_fit * weights["capabilityFit"]
        + cost_efficiency * weights["costEfficiency"]
        + latency_fit * weights["latencyFit"]
        + deployment_fit * weights["deploymentFit"]
    )

    return {
        "model_id": model["id"],
        "score": score,
        "breakdown": {
            "capability_fit": capability_fit,
            "cost_efficiency": cost_efficiency,
            "latency_fit": latency_fit,
            "deployment_fit": deployment_fit,
        },
    }


def rank_models(models, min_model_tier, data_sensitivity, complexity_tier, weights, cost_per_request_by_model_id):
    """Full pipeline: filter, then score and rank survivors, highest score first."""
    candidates = filter_by_min_tier(models, min_model_tier)
    candidates = filter_by_data_sensitivity(candidates, data_sensitivity)

    if not candidates:
        return {"candidates": [], "note": "No models met the minimum tier constraint for this use case."}

    costs = [cost_per_request_by_model_id[m["id"]] for m in candidates]
    max_cost_per_request = max(costs)

    scored = [
        score_model(model, cost_per_request_by_model_id[model["id"]], max_cost_per_request, complexity_tier, weights)
        for model in candidates
    ]

    scored.sort(key=lambda s: s["score"], reverse=True)
    return {"candidates": scored, "note": None}
