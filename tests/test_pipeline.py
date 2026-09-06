import pytest
from engine.pipeline import run_assessment

CHEAP_MODEL = {
    "id": "test-cheap",
    "tier": "cheap",
    "inputCostPerMillion": 1.0,
    "outputCostPerMillion": 5.0,
    "cachedInputCostPerMillion": 0.1,
    "batchDiscountPct": 50,
}
MID_MODEL = {
    "id": "test-mid",
    "tier": "mid",
    "inputCostPerMillion": 2.0,
    "outputCostPerMillion": 10.0,
    "cachedInputCostPerMillion": 0.2,
    "batchDiscountPct": 50,
}
MODELS = [CHEAP_MODEL, MID_MODEL]

WEIGHTS = {"capabilityFit": 0.3, "costEfficiency": 0.3, "latencyFit": 0.25, "deploymentFit": 0.15}
ADOPTION_SCENARIOS = {"low": 0.3, "base": 0.6, "high": 0.9}


def test_run_assessment_matches_hr_worked_example_end_to_end():
    """20,000 pop, 60% adoption, 5 req/day, 250 days -> 15M annual requests."""
    result = run_assessment(
        models=MODELS,
        population=20000,
        requests_per_user_per_day=5,
        input_tokens_per_request=800,
        output_tokens_per_request=300,
        complexity_tier="simple",
        min_model_tier="cheap",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.85,
    )
    assert result["recommended_model"]["id"] == "test-cheap"  # cheapest model clears a "simple" bar outright
    assert result["annual_requests"] == 15_000_000
    assert result["active_users"] == 12000
    assert set(result["adoption_sensitivity"].keys()) == {"low", "base", "high"}


def test_run_assessment_excludes_models_below_min_tier():
    result = run_assessment(
        models=MODELS,
        population=1000,
        requests_per_user_per_day=1,
        input_tokens_per_request=500,
        output_tokens_per_request=200,
        complexity_tier="moderate",
        min_model_tier="mid",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.8,
    )
    assert result["recommended_model"]["id"] == "test-mid"


def test_run_assessment_returns_no_recommendation_when_no_model_qualifies():
    result = run_assessment(
        models=MODELS,
        population=1000,
        requests_per_user_per_day=1,
        input_tokens_per_request=500,
        output_tokens_per_request=200,
        complexity_tier="complex",
        min_model_tier="frontier-extended",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.8,
    )
    assert result["recommended_model"] is None
    assert result["ranking"]["note"]


def test_run_assessment_wires_tco_and_business_value():
    result = run_assessment(
        models=MODELS,
        population=20000,
        requests_per_user_per_day=5,
        input_tokens_per_request=800,
        output_tokens_per_request=300,
        complexity_tier="simple",
        min_model_tier="cheap",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.85,
        tco_components={"human_review": 15000, "monitoring": 5000},
        business_value_inputs={
            "human_time_per_task_minutes": 5,
            "loaded_hourly_cost": 40,
            "productive_value_realisation_rate": 0.7,
        },
        initial_investment=10000,
    )
    assert result["tco"]["total_tco"] == pytest.approx(
        result["inference_cost"]["total_cost"] + 20000, abs=0.01
    )
    assert result["business_value"]["defensible_benefit"] == pytest.approx(1_250_000 * 40 * 0.7, abs=1)
    assert result["roi"] is not None
    assert result["payback_months"] is not None
    assert result["route_comparison"] is None  # not requested in this call


def test_run_assessment_wires_route_comparison_when_requested():
    result = run_assessment(
        models=MODELS,
        population=20000,
        requests_per_user_per_day=5,
        input_tokens_per_request=800,
        output_tokens_per_request=300,
        complexity_tier="simple",
        min_model_tier="cheap",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.85,
        business_value_inputs={
            "human_time_per_task_minutes": 5,
            "loaded_hourly_cost": 40,
            "productive_value_realisation_rate": 0.7,
        },
        route_comparison_inputs={
            "human_success_rate": 0.97,
            "cost_per_failure": 20.0,
            "hybrid_time_saving_factor": 0.5,
        },
    )
    rc = result["route_comparison"]
    assert rc is not None
    assert set(rc["routes"].keys()) == {"AGENT", "HUMAN", "HYBRID"}
    # human_cost_per_task = 40 * (5/60) = $3.33, derived from business_value_inputs
    assert rc["routes"]["HUMAN"]["cost_exec"] == pytest.approx(40 * (5 / 60), abs=0.01)


def test_run_assessment_skips_route_comparison_without_business_value_inputs():
    result = run_assessment(
        models=MODELS,
        population=20000,
        requests_per_user_per_day=5,
        input_tokens_per_request=800,
        output_tokens_per_request=300,
        complexity_tier="simple",
        min_model_tier="cheap",
        weights=WEIGHTS,
        adoption_scenarios=ADOPTION_SCENARIOS,
        success_rate=0.85,
        route_comparison_inputs={
            "human_success_rate": 0.97,
            "cost_per_failure": 20.0,
            "hybrid_time_saving_factor": 0.5,
        },
    )
    assert result["route_comparison"] is None
