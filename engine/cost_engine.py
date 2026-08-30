"""
All functions in this module are pure: same input always produces the same
output, no side effects, no reliance on external state. This is deliberate —
an LLM may interpret a use case, but it must never be the thing computing a
dollar figure. These functions are that boundary.
"""


def calculate_annual_requests(population, adoption_rate, requests_per_user_per_day, working_days_per_year=250):
    """Total requests/year from population, adoption, frequency, and working days."""
    active_users = population * adoption_rate
    annual_requests = active_users * requests_per_user_per_day * working_days_per_year
    return {"active_users": active_users, "annual_requests": annual_requests}


def calculate_inference_cost(
    annual_requests,
    input_tokens_per_request,
    output_tokens_per_request,
    model,  # one entry from pricing.json's `models` list
    cache_hit_rate=0,
    use_batch=False,
):
    """
    Token/inference cost for a given volume against a single model's pricing.
    Pricing fields are per-million-token rates, matching pricing.json's unit.

    cache_hit_rate: fraction (0-1) of input tokens served from cache (e.g. a
    repeated system prompt / retrieved context prefix in RAG).

    use_batch: if true, applies the model's batchDiscountPct to the whole
    bill (a flat % off both input and output, not stackable with fast-mode
    surcharges).
    """
    total_input_tokens = annual_requests * input_tokens_per_request
    total_output_tokens = annual_requests * output_tokens_per_request

    cached_input_tokens = total_input_tokens * cache_hit_rate
    uncached_input_tokens = total_input_tokens * (1 - cache_hit_rate)

    input_cost = (uncached_input_tokens / 1_000_000) * model["inputCostPerMillion"] + (
        cached_input_tokens / 1_000_000
    ) * model["cachedInputCostPerMillion"]

    output_cost = (total_output_tokens / 1_000_000) * model["outputCostPerMillion"]

    total_cost = input_cost + output_cost

    if use_batch and model.get("batchDiscountPct"):
        total_cost = total_cost * (1 - model["batchDiscountPct"] / 100)

    return {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def calculate_tco(
    model_cost,
    data_preparation=0,
    integration=0,
    security=0,
    monitoring=0,
    human_review=0,
    maintenance=0,
    change_management=0,
    infrastructure=0,  # only non-zero for self-hosted deployments
):
    """
    TCO component set, built dynamically per use case rather than always
    summing all ten playbook components. All figures here are inputs the
    user supplies or accepts as defaults — this function only sums what's
    given, it never invents a number.
    """
    components = {
        "model_cost": model_cost,
        "data_preparation": data_preparation,
        "integration": integration,
        "security": security,
        "monitoring": monitoring,
        "human_review": human_review,
        "maintenance": maintenance,
        "change_management": change_management,
        "infrastructure": infrastructure,
    }
    total_tco = sum(components.values())
    return {"components": components, "total_tco": total_tco}


def calculate_cost_per_successful_outcome(total_cost, annual_requests, success_rate):
    """The headline unit-economics metric: cost per successful outcome, not cost per request."""
    successful_outcomes = annual_requests * success_rate
    if successful_outcomes == 0:
        return {"successful_outcomes": 0, "cost_per_successful_outcome": None}
    return {
        "successful_outcomes": successful_outcomes,
        "cost_per_successful_outcome": total_cost / successful_outcomes,
    }


def calculate_cost_per_request(total_cost, annual_requests):
    if annual_requests == 0:
        return None
    return total_cost / annual_requests


def calculate_cost_per_user(total_cost, active_users):
    if active_users == 0:
        return None
    return total_cost / active_users


def calculate_business_value(
    human_time_per_task_minutes,
    loaded_hourly_cost,
    annual_requests,
    productive_value_realisation_rate=1,  # 0-1, e.g. 0.7 = 70% of time saved is real value
    soft_benefit_annual=0,
):
    """
    Splits benefit into "defensible" (direct, measurable savings) and "soft"
    (strategic/productivity value the user believes exists but can't fully
    substantiate). Both are returned separately — never blended into one
    number by default.
    """
    hours_saved = (human_time_per_task_minutes / 60) * annual_requests
    gross_value = hours_saved * loaded_hourly_cost
    defensible_benefit = gross_value * productive_value_realisation_rate
    return {
        "hours_saved": hours_saved,
        "defensible_benefit": defensible_benefit,
        "soft_benefit": soft_benefit_annual,
        "conservative_total": defensible_benefit,
        "full_total": defensible_benefit + soft_benefit_annual,
    }


def calculate_roi(annual_benefit, annual_cost):
    if annual_cost == 0:
        return None
    return ((annual_benefit - annual_cost) / annual_cost) * 100


def calculate_payback_months(initial_investment, annual_net_benefit):
    if annual_net_benefit <= 0:
        return None
    monthly_net_benefit = annual_net_benefit / 12
    return initial_investment / monthly_net_benefit
