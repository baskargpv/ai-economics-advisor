import streamlit as st


def render_results(assessment, models):
    if assessment["recommended_model"] is None:
        st.error(assessment["ranking"]["note"])
        return

    model = assessment["recommended_model"]
    outcome = assessment["outcome"]
    tco = assessment["tco"]

    st.header("Recommendation")
    st.subheader(f"{model['displayName']} — {model['provider']}, {model['tier']} tier")
    if model.get("promotional"):
        st.warning(f"Promotional pricing (through {model.get('promoEndDate', 'an unstated date')}): {model.get('notes', '')}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Annual requests", f"{assessment['annual_requests']:,.0f}")
    col2.metric("Annual TCO", f"${tco['total_tco']:,.0f}")
    col3.metric(
        "Cost / successful outcome",
        f"${outcome['cost_per_successful_outcome']:.4f}" if outcome["cost_per_successful_outcome"] is not None else "n/a",
    )

    with st.expander("Cost breakdown", expanded=False):
        nonzero_components = {k: v for k, v in tco["components"].items() if v}
        st.table({k.replace("_", " ").title(): f"${v:,.2f}" for k, v in nonzero_components.items()})
        st.write(
            f"Cost per request: ${assessment['cost_per_request']:.4f}"
            if assessment["cost_per_request"] is not None
            else "Cost per request: n/a"
        )
        st.write(
            f"Cost per active user: ${assessment['cost_per_user']:.2f}"
            if assessment["cost_per_user"] is not None
            else "Cost per active user: n/a"
        )

    if assessment["business_value"]:
        st.header("ROI")
        bv = assessment["business_value"]
        col4, col5, col6 = st.columns(3)
        col4.metric("Conservative annual benefit", f"${bv['conservative_total']:,.0f}")
        col5.metric("ROI", f"{assessment['roi']:.0f}%" if assessment["roi"] is not None else "n/a")
        col6.metric(
            "Payback period",
            f"{assessment['payback_months']:.1f} months" if assessment["payback_months"] is not None else "n/a",
        )
        if bv["soft_benefit"]:
            st.caption(f"Plus ${bv['soft_benefit']:,.0f}/year in unmodeled soft/strategic benefit, not included above.")

    st.header("Adoption sensitivity")
    st.caption("Same assumptions run across low/base/high adoption scenarios instead of one false-precise number.")
    rows = []
    for name, r in assessment["adoption_sensitivity"].items():
        rows.append(
            {
                "Scenario": name.capitalize(),
                "Adoption": f"{r['adoption_rate']:.0%}",
                "Active users": f"{r['active_users']:,.0f}",
                "Annual requests": f"{r['annual_requests']:,.0f}",
                "Annual cost": f"${r['total_cost']:,.0f}",
                "Cost / outcome": f"${r['cost_per_successful_outcome']:.4f}"
                if r["cost_per_successful_outcome"] is not None
                else "n/a",
            }
        )
    st.table(rows)

    st.header("Model comparison")
    st.caption("Candidates that met the minimum tier requirement, ranked by fit to your stated priority.")
    models_by_id = {m["id"]: m for m in models}
    comp_rows = []
    for c in assessment["ranking"]["candidates"]:
        m = models_by_id[c["model_id"]]
        comp_rows.append(
            {
                "Model": m["displayName"],
                "Tier": m["tier"],
                "Score": f"{c['score']:.2f}",
                "Capability fit": f"{c['breakdown']['capability_fit']:.2f}",
                "Cost efficiency": f"{c['breakdown']['cost_efficiency']:.2f}",
            }
        )
    st.table(comp_rows)
