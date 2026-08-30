"""
Wires the engine modules together into one assessment: rank candidate
models, cost out the winner, and run adoption-sensitivity on it. Still a
pure function — every number here traces back to a cost_engine/model_scoring/
sensitivity call, nothing is computed inline.
"""

from engine.cost_engine import (
    calculate_annual_requests,
    calculate_inference_cost,
    calculate_tco,
    calculate_cost_per_successful_outcome,
    calculate_cost_per_request,
    calculate_cost_per_user,
    calculate_business_value,
    calculate_roi,
    calculate_payback_months,
)
from engine.model_scoring import rank_models
from engine.sensitivity import run_adoption_scenarios


def run_assessment(
    models,
    population,
    requests_per_user_per_day,
    input_tokens_per_request,
    output_tokens_per_request,
    complexity_tier,
    min_model_tier,
    weights,
    adoption_scenarios,
    success_rate,
    working_days_per_year=250,
    cache_hit_rate=0,
    use_batch=False,
    tco_components=None,
    business_value_inputs=None,
    initial_investment=0,
    human_cost_per_request=None,
    data_sensitivity=None,
    base_adoption_rate=None,
):
    """
    Ranks candidate models, costs out the top-ranked one at the base
    adoption scenario (or `base_adoption_rate` if given), and runs adoption
    sensitivity on that model. Returns `recommended_model: None` when no
    model meets `min_model_tier` — callers must check that before reading
    the rest of the result.
    """
    base_adoption_rate = base_adoption_rate if base_adoption_rate is not None else adoption_scenarios["base"]

    requests_result = calculate_annual_requests(
        population, base_adoption_rate, requests_per_user_per_day, working_days_per_year
    )
    annual_requests = requests_result["annual_requests"]

    inference_cost_by_model_id = {}
    cost_per_request_by_model_id = {}
    for model in models:
        cost_result = calculate_inference_cost(
            annual_requests, input_tokens_per_request, output_tokens_per_request, model, cache_hit_rate, use_batch
        )
        inference_cost_by_model_id[model["id"]] = cost_result
        cost_per_request_by_model_id[model["id"]] = calculate_cost_per_request(cost_result["total_cost"], annual_requests)

    ranking = rank_models(models, min_model_tier, data_sensitivity, complexity_tier, weights, cost_per_request_by_model_id)

    if not ranking["candidates"]:
        return {"ranking": ranking, "recommended_model": None}

    top_model_id = ranking["candidates"][0]["model_id"]
    recommended_model = next(m for m in models if m["id"] == top_model_id)
    top_inference_cost = inference_cost_by_model_id[top_model_id]

    tco_result = calculate_tco(model_cost=top_inference_cost["total_cost"], **(tco_components or {}))

    outcome_result = calculate_cost_per_successful_outcome(tco_result["total_tco"], annual_requests, success_rate)
    cost_per_request = calculate_cost_per_request(tco_result["total_tco"], annual_requests)
    cost_per_user = calculate_cost_per_user(tco_result["total_tco"], requests_result["active_users"])

    business_value = None
    roi = None
    payback_months = None
    if business_value_inputs:
        business_value = calculate_business_value(annual_requests=annual_requests, **business_value_inputs)
        roi = calculate_roi(business_value["conservative_total"], tco_result["total_tco"])
        payback_months = calculate_payback_months(
            initial_investment, business_value["conservative_total"] - tco_result["total_tco"]
        )

    base_inputs = {
        "population": population,
        "requests_per_user_per_day": requests_per_user_per_day,
        "working_days_per_year": working_days_per_year,
        "input_tokens_per_request": input_tokens_per_request,
        "output_tokens_per_request": output_tokens_per_request,
        "success_rate": success_rate,
        "cache_hit_rate": cache_hit_rate,
        "use_batch": use_batch,
    }
    adoption_sensitivity = run_adoption_scenarios(base_inputs, adoption_scenarios, recommended_model, human_cost_per_request)

    return {
        "ranking": ranking,
        "recommended_model": recommended_model,
        "annual_requests": annual_requests,
        "active_users": requests_result["active_users"],
        "inference_cost": top_inference_cost,
        "tco": tco_result,
        "outcome": outcome_result,
        "cost_per_request": cost_per_request,
        "cost_per_user": cost_per_user,
        "business_value": business_value,
        "roi": roi,
        "payback_months": payback_months,
        "adoption_sensitivity": adoption_sensitivity,
    }
