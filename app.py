import streamlit as st

from engine.use_case_defaults import get_all_use_cases, get_priority_weight_profiles, get_adoption_scenarios
from engine.pricing_data import get_all_models
from engine.pipeline import run_assessment
from ui.form import render_use_case_picker, render_assumptions_form
from ui.results import render_results

st.set_page_config(page_title="AI Economics Advisor", page_icon="📊", layout="centered")

st.title("AI Economics Advisor")
st.write(
    "Right-size an AI/LLM use case before you build it. Answer a few questions about "
    "the use case and expected volume — this estimates inference cost, total cost of "
    "ownership, ROI, and cost per successful outcome, and recommends the simplest "
    "model that meets the requirement."
)

use_cases = get_all_use_cases()
models = get_all_models()
adoption_scenarios = get_adoption_scenarios()
priority_profiles = get_priority_weight_profiles()

use_case = render_use_case_picker(use_cases)
if use_case.get("description"):
    st.caption(use_case["description"])

inputs = render_assumptions_form(use_case, priority_profiles)

if inputs is not None:
    weights = priority_profiles[inputs["priority_key"]]
    assessment = run_assessment(
        models=models,
        population=inputs["population"],
        requests_per_user_per_day=inputs["requests_per_user_per_day"],
        working_days_per_year=inputs["working_days_per_year"],
        input_tokens_per_request=inputs["input_tokens_per_request"],
        output_tokens_per_request=inputs["output_tokens_per_request"],
        complexity_tier=inputs["complexity_tier"],
        min_model_tier=inputs["min_model_tier"],
        weights=weights,
        adoption_scenarios=adoption_scenarios,
        success_rate=inputs["success_rate"],
        cache_hit_rate=inputs["cache_hit_rate"],
        use_batch=inputs["use_batch"],
        tco_components=inputs["tco_components"],
        business_value_inputs=inputs["business_value_inputs"],
        initial_investment=inputs["initial_investment"],
        human_cost_per_request=inputs["human_cost_per_request"],
        route_comparison_inputs=inputs["route_comparison_inputs"],
    )
    render_results(assessment, models)
