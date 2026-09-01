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
    index = st.selectbox(
        "What's the use case?",
        range(len(use_cases)),
        format_func=lambda i: labels[i],
        help="Pick a preset to pre-fill sensible defaults for task shape and complexity, or choose Custom to set every assumption yourself.",
    )
    return use_cases[index]


def render_assumptions_form(use_case, priority_profiles):
    """Returns a dict of raw inputs once submitted, else None."""
    assumptions = resolve_assumptions(use_case)
    is_custom = use_case["id"] == "custom"

    with st.form("assumptions_form"):
        st.subheader("Volume")
        col1, col2 = st.columns(2)
        with col1:
            population = st.number_input(
                "Population (people who could use this)",
                min_value=1,
                value=1000,
                step=100,
                help="Total number of people who could potentially use this AI feature — not just today's active users.",
            )
            requests_per_user_per_day = st.number_input(
                "Requests per active user per day",
                min_value=0.0,
                value=2.0,
                step=0.5,
                help="Average number of AI requests each active user makes on a typical working day.",
            )
        with col2:
            working_days_per_year = st.number_input(
                "Working days per year",
                min_value=1,
                value=250,
                step=5,
                help="Number of days per year this gets used — e.g. ~250 for a weekday-only internal tool, 365 for a consumer product used every day.",
            )

        st.subheader("Task shape")
        col3, col4 = st.columns(2)
        with col3:
            input_tokens = st.number_input(
                "Input tokens per request",
                min_value=1,
                value=int(assumptions["input_tokens"]["value"]) if assumptions["input_tokens"]["value"] else 500,
                help="Average tokens sent to the model per request, including the prompt, context, and any retrieved documents.",
            )
            success_rate = st.slider(
                "Success rate (fraction of requests that succeed without human fallback)",
                0.0,
                1.0,
                value=float(assumptions["success_rate"]["value"]) if assumptions["success_rate"]["value"] else 0.75,
                help="Share of requests where the AI's output can be used as-is, without a person needing to step in or redo it.",
            )
        with col4:
            output_tokens = st.number_input(
                "Output tokens per request",
                min_value=1,
                value=int(assumptions["output_tokens"]["value"]) if assumptions["output_tokens"]["value"] else 300,
                help="Average tokens the model generates per response.",
            )

        if is_custom:
            col5, col6 = st.columns(2)
            with col5:
                complexity_tier = st.selectbox(
                    "Task complexity",
                    _COMPLEXITY_TIERS,
                    index=1,
                    help="How demanding the task is (reasoning, ambiguity, domain knowledge required). Higher complexity tends to require a stronger model.",
                )
            with col6:
                min_model_tier = st.selectbox(
                    "Minimum model tier required",
                    _MODEL_TIERS,
                    index=0,
                    help="The weakest model tier you'd trust to handle this task reliably — the recommender won't suggest anything below it.",
                )
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
            help="The trade-off the model recommendation should optimize for once the minimum quality bar is met.",
        )

        with st.expander("Advanced: caching & batching"):
            cache_hit_rate = st.slider(
                "Cache hit rate (fraction of input tokens served from cache)",
                0.0,
                1.0,
                0.0,
                help="Share of input tokens (e.g. repeated system prompts or context) expected to hit a prompt cache instead of being billed at full input price.",
            )
            use_batch = st.checkbox(
                "Use batch processing (if latency isn't a constraint)",
                value=False,
                help="Batch APIs are typically ~50% cheaper but responses aren't returned in real time — only enable this if requests don't need an immediate reply.",
            )

        with st.expander("Advanced: total cost of ownership (annual, beyond inference)"):
            st.caption("Optional annual costs beyond raw model inference. Leave any at 0 if not applicable or unknown.")
            col7, col8 = st.columns(2)
            with col7:
                data_preparation = st.number_input(
                    "Data preparation",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of collecting, cleaning, and labeling data used to build or evaluate this use case.",
                )
                security = st.number_input(
                    "Security",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of security reviews, access controls, and safeguards specific to this AI feature.",
                )
                maintenance = st.number_input(
                    "Maintenance",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of ongoing upkeep — prompt tuning, bug fixes, dependency updates, re-evaluation.",
                )
                infrastructure = st.number_input(
                    "Infrastructure (self-hosted only)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of servers/GPUs you operate yourself, if self-hosting the model. Leave at 0 if using a hosted API.",
                )
            with col8:
                integration = st.number_input(
                    "Integration",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of connecting this AI feature to the surrounding systems and workflows it depends on.",
                )
                monitoring = st.number_input(
                    "Monitoring",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of tracking quality, cost, and reliability of the feature once it's live.",
                )
                human_review = st.number_input(
                    "Human review",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of people reviewing or spot-checking AI outputs, separate from the per-request human fallback captured by success rate.",
                )
                change_management = st.number_input(
                    "Change management",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Annual cost of training, communication, and process changes needed to get people using this well.",
                )

        with st.expander("Advanced: business value & ROI (optional)"):
            include_business_value = st.checkbox(
                "Estimate ROI against a human/manual baseline",
                value=False,
                help="Turn this on to compare the AI's total cost against the value of the human time or manual process it replaces.",
            )
            col9, col10 = st.columns(2)
            with col9:
                human_time_per_task_minutes = st.number_input(
                    "Human time per task (minutes)",
                    min_value=0.0,
                    value=10.0,
                    help="How long a person takes to do one task manually today, before any AI assistance.",
                )
                productive_value_realisation_rate = st.slider(
                    "Time-saved realisation rate",
                    0.0,
                    1.0,
                    0.7,
                    help="Not all time saved turns into real productivity — this discounts raw time saved to a more realistic value (e.g. 0.7 = 70% of saved time becomes usable output).",
                )
                initial_investment = st.number_input(
                    "One-time initial investment ($)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Upfront one-time cost to build and launch this (development, setup, initial training), amortised into the ROI calculation.",
                )
            with col10:
                loaded_hourly_cost = st.number_input(
                    "Loaded hourly cost of that human time ($)",
                    min_value=0.0,
                    value=50.0,
                    help="Fully-loaded hourly cost of the person doing this task — salary plus benefits and overhead, not just base pay.",
                )
                soft_benefit_annual = st.number_input(
                    "Additional soft/strategic benefit (annual $)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Any extra annual value that's real but hard to price precisely — e.g. faster response times, employee satisfaction, brand perception.",
                )
                human_cost_per_request = st.number_input(
                    "Human cost per request today ($, for comparison — leave 0 to skip)",
                    min_value=0.0,
                    value=0.0,
                    help="What it costs today to have a human fully handle one request, for a direct side-by-side comparison with the AI's cost per request.",
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
