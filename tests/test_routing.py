import pytest
from engine.routing import compare_routes


def test_compare_routes_picks_hybrid_when_agent_risk_dominates():
    """
    An agent that's cheap but fails often enough that recovering from its
    failures (a high per-failure cost) outweighs its execution-cost edge,
    against a reliable but slow-and-expensive human baseline. Hybrid keeps
    the agent's low execution cost for most of the task while inheriting
    the human's much lower failure rate, landing below both pure routes.
    """
    result = compare_routes(
        agent_cost_per_task=0.5,
        agent_success_rate=0.5,
        human_cost_per_task=20.0,
        human_success_rate=0.97,
        cost_per_failure=100.0,
        hybrid_time_saving_factor=0.6,
    )
    routes = result["routes"]

    assert routes["AGENT"]["cost_risk"] == pytest.approx(0.5 * 100.0, abs=0.01)
    assert routes["HUMAN"]["cost_risk"] == pytest.approx(0.03 * 100.0, abs=0.01)

    hybrid_cost_exec = 0.5 + 20.0 * (1 - 0.6)
    assert routes["HYBRID"]["cost_exec"] == pytest.approx(hybrid_cost_exec, abs=0.01)
    assert routes["HYBRID"]["success_rate"] == 0.97  # hybrid inherits the human's success rate

    assert result["recommended_route"] == "HYBRID"
    assert result["savings_vs_human"] > 0


def test_compare_routes_recommends_human_when_agent_and_hybrid_both_lose():
    result = compare_routes(
        agent_cost_per_task=100.0,
        agent_success_rate=0.2,
        human_cost_per_task=10.0,
        human_success_rate=0.99,
        cost_per_failure=50.0,
        hybrid_time_saving_factor=0.1,
    )
    assert result["recommended_route"] == "HUMAN"
    assert result["savings_vs_human"] == 0


def test_compare_routes_recommends_agent_when_it_dominates_on_cost_and_reliability():
    result = compare_routes(
        agent_cost_per_task=0.05,
        agent_success_rate=0.99,
        human_cost_per_task=25.0,
        human_success_rate=0.97,
        cost_per_failure=10.0,
        hybrid_time_saving_factor=0.5,
    )
    assert result["recommended_route"] == "AGENT"
    assert result["savings_vs_human"] > 0
