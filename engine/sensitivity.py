from engine.cost_engine import (
    calculate_annual_requests,
    calculate_inference_cost,
    calculate_cost_per_successful_outcome,
)


def run_adoption_scenarios(base_inputs, adoption_scenarios, model, human_cost_per_request=None):
    """
    Runs the same cost/benefit calculation across low/base/high adoption
    scenarios instead of returning one false-precise number.

    base_inputs: dict with population, requests_per_user_per_day,
      working_days_per_year, input_tokens_per_request, output_tokens_per_request,
      success_rate, and optionally cache_hit_rate / use_batch.
    adoption_scenarios: e.g. {"low": 0.3, "base": 0.6, "high": 0.9}
    """
    results = {}

    for scenario_name, adoption_rate in adoption_scenarios.items():
        requests_result = calculate_annual_requests(
            population=base_inputs["population"],
            adoption_rate=adoption_rate,
            requests_per_user_per_day=base_inputs["requests_per_user_per_day"],
            working_days_per_year=base_inputs.get("working_days_per_year", 250),
        )
        active_users = requests_result["active_users"]
        annual_requests = requests_result["annual_requests"]

        cost_result = calculate_inference_cost(
            annual_requests=annual_requests,
            input_tokens_per_request=base_inputs["input_tokens_per_request"],
            output_tokens_per_request=base_inputs["output_tokens_per_request"],
            model=model,
            cache_hit_rate=base_inputs.get("cache_hit_rate", 0),
            use_batch=base_inputs.get("use_batch", False),
        )
        total_cost = cost_result["total_cost"]

        outcome_result = calculate_cost_per_successful_outcome(
            total_cost=total_cost,
            annual_requests=annual_requests,
            success_rate=base_inputs["success_rate"],
        )
        cost_per_successful_outcome = outcome_result["cost_per_successful_outcome"]

        vs_human_baseline = None
        if human_cost_per_request is not None:
            vs_human_baseline = (human_cost_per_request - (cost_per_successful_outcome or 0)) * annual_requests

        results[scenario_name] = {
            "adoption_rate": adoption_rate,
            "active_users": active_users,
            "annual_requests": annual_requests,
            "total_cost": total_cost,
            "cost_per_successful_outcome": cost_per_successful_outcome,
            "vs_human_baseline": vs_human_baseline,
        }

    return results


def find_break_even_adoption(cost_at_adoption, benefit_at_adoption, tolerance=0.001):
    """
    The adoption rate at which cumulative annual benefit first exceeds
    cumulative annual cost, found by bisection search over [0, 1] rather
    than requiring a closed-form solution.

    cost_at_adoption / benefit_at_adoption: callables taking an adoption
    rate (0-1) and returning annual cost / benefit.
    """
    low, high = 0.0, 1.0

    def net_at(rate):
        return benefit_at_adoption(rate) - cost_at_adoption(rate)

    if net_at(high) < 0:
        return {"break_even_adoption": None, "note": "Benefit never exceeds cost, even at 100% adoption."}
    if net_at(low) >= 0:
        return {"break_even_adoption": 0, "note": "Benefit exceeds cost even at 0% adoption — check inputs."}

    while high - low > tolerance:
        mid = (low + high) / 2
        if net_at(mid) >= 0:
            high = mid
        else:
            low = mid

    return {"break_even_adoption": high, "note": None}


def find_break_even_volume(cost_per_outcome_at_volume, human_cost_per_outcome, max_volume_to_search, tolerance=1):
    """
    The request volume at which cost-per-successful-outcome first drops
    below a stated human/manual-process baseline cost. Useful when fixed TCO
    components (integration, security setup, etc.) dominate at low volume.
    """
    low, high = 0.0, float(max_volume_to_search)

    def diff_at(vol):
        return human_cost_per_outcome - cost_per_outcome_at_volume(vol)

    if diff_at(high) < 0:
        return {"break_even_volume": None, "note": "Never becomes cheaper than the human baseline within the searched range."}
    if diff_at(low) >= 0:
        return {"break_even_volume": 0, "note": "Cheaper than the human baseline even at minimal volume."}

    while high - low > tolerance:
        mid = (low + high) / 2
        if diff_at(mid) >= 0:
            high = mid
        else:
            low = mid

    return {"break_even_volume": high, "note": None}
