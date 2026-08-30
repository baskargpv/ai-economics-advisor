import streamlit as st

from engine.use_case_defaults import resolve_assumptions

_COMPLEXITY_TIERS = ["simple", "simple-moderate", "moderate", "moderate-complex", "complex"]
_MODEL_TIERS = ["cheap", "mid", "frontier", "frontier-extended"]
_PRIORITY_LABELS = {
    "lowestCost": "Lowest cost",
    "highestQuality": "Highest quality",
    "lowestLatency": "Lowest latency",
    "balanced": "Balanced",
}


def render_use_case_picker(use_cases):
    """Outside the form so picking a use case immediately updates the defaults shown below."""
    labels = [uc["label"] for uc in use_cases]
    index = st.selectbox("What's the use case?", range(len(use_cases)), format_func=lambda i: labels[i])
    return use_cases[index]


def render_assumptions_form(use_case, priority_profiles):
    """Returns a dict of raw inputs once submitted, else None."""
    assumptions = resolve_assumptions(use_case)
    is_custom = use_case["id"] == "custom"

    with st.form("assumptions_form"):
        st.subheader("Volume")
        col1, col2 = st.columns(2)
        with col1:
            population = st.number_input("Population (people who could use this)", min_value=1, value=1000, step=100)
            requests_per_user_per_day = st.number_input(
                "Requests per active user per day", min_value=0.0, value=2.0, step=0.5
            )
        with col2:
            working_days_per_year = st.number_input("Working days per year", min_value=1, value=250, step=5)

        st.subheader("Task shape")
        col3, col4 = st.columns(2)
        with col3:
            input_tokens = st.number_input(
                "Input tokens per request",
                min_value=1,
                value=int(assumptions["input_tokens"]["value"]) if assumptions["input_tokens"]["value"] else 500,
            )
            success_rate = st.slider(
                "Success rate (fraction of requests that succeed without human fallback)",
                0.0,
                1.0,
                value=float(assumptions["success_rate"]["value"]) if assumptions["success_rate"]["value"] else 0.75,
            )
        with col4:
            output_tokens = st.number_input(
                "Output tokens per request",
                min_value=1,
                value=int(assumptions["output_tokens"]["value"]) if assumptions["output_tokens"]["value"] else 300,
            )

        if is_custom:
            col5, col6 = st.columns(2)
            with col5:
                complexity_tier = st.selectbox("Task complexity", _COMPLEXITY_TIERS, index=1)
            with col6:
                min_model_tier = st.selectbox("Minimum model tier required", _MODEL_TIERS, index=0)
        else:
            complexity_tier = assumptions["complexity_tier"]
            min_model_tier = assumptions["min_model_tier"]
            st.caption(f"Complexity: **{complexity_tier}** · Minimum model tier: **{min_model_tier}** (from use case defaults)")

        st.subheader("Priority")
        priority_key = st.selectbox(
            "What matters most when choosing a model?",
            list(priority_profiles.keys()),
            format_func=lambda k: _PRIORITY_LABELS.get(k, k),
            index=list(priority_profiles.keys()).index("balanced") if "balanced" in priority_profiles else 0,
        )

        with st.expander("Advanced: caching & batching"):
            cache_hit_rate = st.slider("Cache hit rate (fraction of input tokens served from cache)", 0.0, 1.0, 0.0)
            use_batch = st.checkbox("Use batch processing (if latency isn't a constraint)", value=False)

        with st.expander("Advanced: total cost of ownership (annual, beyond inference)"):
            col7, col8 = st.columns(2)
            with col7:
                data_preparation = st.number_input("Data preparation", min_value=0.0, value=0.0, step=1000.0)
                security = st.number_input("Security", min_value=0.0, value=0.0, step=1000.0)
                maintenance = st.number_input("Maintenance", min_value=0.0, value=0.0, step=1000.0)
                infrastructure = st.number_input("Infrastructure (self-hosted only)", min_value=0.0, value=0.0, step=1000.0)
            with col8:
                integration = st.number_input("Integration", min_value=0.0, value=0.0, step=1000.0)
                monitoring = st.number_input("Monitoring", min_value=0.0, value=0.0, step=1000.0)
                human_review = st.number_input("Human review", min_value=0.0, value=0.0, step=1000.0)
                change_management = st.number_input("Change management", min_value=0.0, value=0.0, step=1000.0)

        with st.expander("Advanced: business value & ROI (optional)"):
            include_business_value = st.checkbox("Estimate ROI against a human/manual baseline", value=False)
            col9, col10 = st.columns(2)
            with col9:
                human_time_per_task_minutes = st.number_input("Human time per task (minutes)", min_value=0.0, value=10.0)
                productive_value_realisation_rate = st.slider("Time-saved realisation rate", 0.0, 1.0, 0.7)
                initial_investment = st.number_input("One-time initial investment ($)", min_value=0.0, value=0.0, step=1000.0)
            with col10:
                loaded_hourly_cost = st.number_input("Loaded hourly cost of that human time ($)", min_value=0.0, value=50.0)
                soft_benefit_annual = st.number_input(
                    "Additional soft/strategic benefit (annual $)", min_value=0.0, value=0.0, step=1000.0
                )
                human_cost_per_request = st.number_input(
                    "Human cost per request today ($, for comparison — leave 0 to skip)", min_value=0.0, value=0.0
                )

        submitted = st.form_submit_button("Calculate", type="primary")

    if not submitted:
        return None

    return {
        "population": population,
        "requests_per_user_per_day": requests_per_user_per_day,
        "working_days_per_year": working_days_per_year,
        "input_tokens_per_request": input_tokens,
        "output_tokens_per_request": output_tokens,
        "success_rate": success_rate,
        "complexity_tier": complexity_tier,
        "min_model_tier": min_model_tier,
        "priority_key": priority_key,
        "cache_hit_rate": cache_hit_rate,
        "use_batch": use_batch,
        "tco_components": {
            "data_preparation": data_preparation,
            "integration": integration,
            "security": security,
            "monitoring": monitoring,
            "human_review": human_review,
            "maintenance": maintenance,
            "change_management": change_management,
            "infrastructure": infrastructure,
        },
        "business_value_inputs": {
            "human_time_per_task_minutes": human_time_per_task_minutes,
            "loaded_hourly_cost": loaded_hourly_cost,
            "productive_value_realisation_rate": productive_value_realisation_rate,
            "soft_benefit_annual": soft_benefit_annual,
        }
        if include_business_value
        else None,
        "initial_investment": initial_investment,
        "human_cost_per_request": human_cost_per_request if human_cost_per_request > 0 else None,
    }
