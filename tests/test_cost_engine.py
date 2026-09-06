import pytest
from engine.cost_engine import (
    calculate_annual_requests,
    calculate_inference_cost,
    calculate_cost_per_successful_outcome,
    calculate_cost_per_request,
    calculate_tco,
    calculate_roi,
    calculate_payback_months,
    calculate_business_value,
    calculate_risk_cost,
)

# A representative mid-tier model for testing (matches Claude Sonnet 5's
# current published rate — see data/pricing.json).
MID_TIER_MODEL = {
    "id": "test-mid",
    "inputCostPerMillion": 2.0,
    "outputCostPerMillion": 10.0,
    "cachedInputCostPerMillion": 0.2,
    "batchDiscountPct": 50,
}


def test_calculate_annual_requests_matches_hr_worked_example():
    """20,000 pop, 60% adoption, 5 req/day, 250 days."""
    result = calculate_annual_requests(
        population=20000,
        adoption_rate=0.6,
        requests_per_user_per_day=5,
        working_days_per_year=250,
    )
    assert result["active_users"] == 12000
    assert result["annual_requests"] == 15_000_000  # 12,000 * 5 * 250


def test_inference_cost_no_caching_no_batch():
    result = calculate_inference_cost(
        annual_requests=1_000_000,
        input_tokens_per_request=2500,
        output_tokens_per_request=400,
        model=MID_TIER_MODEL,
    )
    # input: 2.5bn tokens / 1M * $2 = $5,000
    # output: 0.4bn tokens / 1M * $10 = $4,000
    assert result["input_cost"] == pytest.approx(5000, abs=0.01)
    assert result["output_cost"] == pytest.approx(4000, abs=0.01)
    assert result["total_cost"] == pytest.approx(9000, abs=0.01)


def test_inference_cost_applies_cache_hit_rate():
    result = calculate_inference_cost(
        annual_requests=1_000_000,
        input_tokens_per_request=2500,
        output_tokens_per_request=400,
        model=MID_TIER_MODEL,
        cache_hit_rate=0.6,
    )
    # 40% uncached: 1bn tokens / 1M * $2 = $2,000
    # 60% cached: 1.5bn tokens / 1M * $0.2 = $300
    assert result["input_cost"] == pytest.approx(2300, abs=0.01)


def test_inference_cost_applies_batch_discount_to_whole_bill():
    no_batch = calculate_inference_cost(
        annual_requests=1_000_000,
        input_tokens_per_request=2500,
        output_tokens_per_request=400,
        model=MID_TIER_MODEL,
    )
    with_batch = calculate_inference_cost(
        annual_requests=1_000_000,
        input_tokens_per_request=2500,
        output_tokens_per_request=400,
        model=MID_TIER_MODEL,
        use_batch=True,
    )
    assert with_batch["total_cost"] == pytest.approx(no_batch["total_cost"] * 0.5, abs=0.01)


def test_cost_per_successful_outcome_matches_playbook_example():
    """100k req, $10k cost, 60% success."""
    result = calculate_cost_per_successful_outcome(total_cost=10000, annual_requests=100000, success_rate=0.6)
    assert result["successful_outcomes"] == 60000
    assert result["cost_per_successful_outcome"] == pytest.approx(0.1667, abs=0.001)


def test_cost_per_successful_outcome_returns_none_at_zero_volume():
    result = calculate_cost_per_successful_outcome(total_cost=0, annual_requests=0, success_rate=0.8)
    assert result["cost_per_successful_outcome"] is None


def test_cost_per_request():
    assert calculate_cost_per_request(total_cost=9000, annual_requests=1_000_000) == pytest.approx(0.009, abs=0.00001)


def test_tco_sums_only_provided_components():
    result = calculate_tco(model_cost=100000, security=20000, human_review=15000)
    assert result["total_tco"] == 135000
    assert result["components"]["infrastructure"] == 0  # untouched default


def test_business_value_matches_hr_example_assumptions():
    """5 min/task, 70% productive-value realisation, 15M requests/year."""
    result = calculate_business_value(
        human_time_per_task_minutes=5,
        loaded_hourly_cost=40,
        annual_requests=15_000_000,
        productive_value_realisation_rate=0.7,
    )
    assert result["hours_saved"] == pytest.approx(1_250_000, abs=1)  # (5/60) * 15M
    assert result["defensible_benefit"] == pytest.approx(1_250_000 * 40 * 0.7, abs=1)


def test_roi_as_percentage():
    assert calculate_roi(annual_benefit=150000, annual_cost=100000) == pytest.approx(50, abs=0.001)


def test_payback_months():
    # 100k invested, 60k net benefit/year -> 5k/month -> 20 months
    assert calculate_payback_months(initial_investment=100000, annual_net_benefit=60000) == pytest.approx(20, abs=0.01)


def test_payback_months_returns_none_when_no_net_benefit():
    assert calculate_payback_months(initial_investment=100000, annual_net_benefit=0) is None


def test_risk_cost_scales_with_failure_rate_and_cost():
    # 25% failure rate, $40 to recover from a failed attempt
    assert calculate_risk_cost(failure_rate=0.25, cost_per_failure=40) == pytest.approx(10, abs=0.001)


def test_risk_cost_is_zero_at_zero_failure_rate():
    assert calculate_risk_cost(failure_rate=0, cost_per_failure=1000) == 0
