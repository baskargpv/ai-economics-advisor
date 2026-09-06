"""
Compares AGENT, HUMAN, and HYBRID as alternative ways to get one task done,
instead of assuming the task should be fully automated. Each route's
expected total cost is its direct execution cost plus its expected risk
cost (the probability-weighted cost of the failure path) — the same
building blocks as the rest of the engine, just applied per-route rather
than to a single assumed-automated pipeline.

Pure functions throughout: success rates and the hybrid time-saving factor
are estimates the caller supplies (from use-case defaults, history, or a
judgment call) — this module only does the arithmetic over them.
"""

from engine.cost_engine import calculate_risk_cost


def _route_result(cost_exec, success_rate, cost_per_failure):
    risk_cost = calculate_risk_cost(1 - success_rate, cost_per_failure)
    expected_total_cost = cost_exec + risk_cost
    cost_per_successful_outcome = expected_total_cost / success_rate if success_rate > 0 else None
    return {
        "cost_exec": cost_exec,
        "cost_risk": risk_cost,
        "expected_total_cost": expected_total_cost,
        "success_rate": success_rate,
        "cost_per_successful_outcome": cost_per_successful_outcome,
    }


def compare_routes(
    agent_cost_per_task,
    agent_success_rate,
    human_cost_per_task,
    human_success_rate,
    cost_per_failure,
    hybrid_time_saving_factor,
):
    """
    agent_cost_per_task: AI cost (inference + any per-task TCO) for one task.
    human_cost_per_task: fully-loaded human cost for one task (time x hourly rate).
    cost_per_failure: rework/escalation cost when an attempt fails. Applied
      uniformly across routes — a simplification; a failed agent attempt and
      a failed human attempt may cost different amounts to recover from in
      reality, but modelling that split isn't worth the extra inputs here.
    hybrid_time_saving_factor: fraction (0-1) of the human's task time an
      agent pre-processing pass removes. The human still makes the final
      call in this route, so HYBRID uses the human's success rate, not the
      agent's.
    """
    agent = _route_result(agent_cost_per_task, agent_success_rate, cost_per_failure)
    human = _route_result(human_cost_per_task, human_success_rate, cost_per_failure)

    hybrid_cost_exec = agent_cost_per_task + human_cost_per_task * (1 - hybrid_time_saving_factor)
    hybrid = _route_result(hybrid_cost_exec, human_success_rate, cost_per_failure)

    routes = {"AGENT": agent, "HUMAN": human, "HYBRID": hybrid}
    recommended_route = min(routes, key=lambda r: routes[r]["expected_total_cost"])

    return {
        "routes": routes,
        "recommended_route": recommended_route,
        "savings_vs_human": human["expected_total_cost"] - routes[recommended_route]["expected_total_cost"],
    }
