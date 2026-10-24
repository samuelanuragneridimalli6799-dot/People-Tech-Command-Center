import pandas as pd
import plotly.express as px
import streamlit as st

import utils

utils.setup("Roadmap and WBR")
today = utils.as_of()

st.title("Roadmap and Weekly Business Review")
st.caption("One view across People Technology and People Analytics. Edit status in the table and the review below updates.")

base = utils.get_initiatives()
raid = utils.load_csv("raid.csv", ("due",))
decisions = utils.load_csv("decisions.csv", ("date",))

tab_roadmap, tab_wbr, tab_decisions = st.tabs(["Roadmap", "Weekly Business Review", "Decision log"])

with tab_roadmap:
    enriched = utils.enrich_initiatives(base, today)
    active = enriched[enriched["rag"] != "Done"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active", len(active))
    c2.metric("Red", int((active["rag"] == "Red").sum()))
    c3.metric("Milestones overdue", int(enriched["milestone_overdue"].sum()))
    c4.metric("Past end date, not finished", int(enriched["slipped"].sum()))

    projects = sorted(enriched["project"].unique())
    chosen = st.multiselect("Projects", projects, default=projects)
    view = enriched[enriched["project"].isin(chosen)].sort_values(["project", "start"])

    fig = px.timeline(
        view,
        x_start="start",
        x_end="end",
        y="initiative",
        color="rag",
        color_discrete_map=utils.RAG_COLORS,
        category_orders={"rag": ["Red", "Amber", "Green", "Done"]},
        hover_data={"project": True, "pct_complete": True, "next_milestone": True, "start": False, "end": False},
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(title=None)
    marker = str(today.date())
    fig.add_shape(type="line", x0=marker, x1=marker, y0=0, y1=1, xref="x", yref="paper", line=dict(dash="dash", color="#555"))
    fig.add_annotation(x=marker, y=1, xref="x", yref="paper", text="As-of date", showarrow=False, yanchor="bottom")
    fig.update_layout(height=max(380, 34 * len(view) + 120), legend_title_text="Status", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Status table (editable)**")
    edited = st.data_editor(
        base,
        key="initiative_editor",
        hide_index=True,
        width="stretch",
        disabled=["id", "initiative", "project", "function", "owner", "start", "end", "depends_on"],
        column_config={
            "rag": st.column_config.SelectboxColumn("Status", options=["Green", "Amber", "Red", "Done"], required=True),
            "pct_complete": st.column_config.NumberColumn("% complete", min_value=0, max_value=100, step=5),
            "start": st.column_config.DateColumn("Start"),
            "end": st.column_config.DateColumn("End"),
            "next_milestone_date": st.column_config.DateColumn("Next milestone date"),
        },
    )
    for col in ("start", "end", "next_milestone_date"):
        edited[col] = pd.to_datetime(edited[col])
    st.session_state["initiatives"] = edited

    st.markdown("**Dependencies at risk**")
    deps = utils.dependency_risks(utils.enrich_initiatives(edited, today))
    if deps.empty:
        st.write("No open initiative depends on something red, amber or late.")
    else:
        st.dataframe(deps, hide_index=True, width="stretch")

with tab_wbr:
    current = utils.enrich_initiatives(edited, today)
    wbr = utils.build_wbr(current, raid, today)
    st.markdown(wbr)
    st.download_button("Download as Markdown", wbr, file_name=f"wbr_{today:%Y-%m-%d}.md", mime="text/markdown")
    st.caption("Generated from the roadmap and RAID data using fixed rules. No external AI call.")

with tab_decisions:
    st.markdown("Decisions and commitments are recorded with who decided and which initiative they affect.")
    st.dataframe(
        decisions.sort_values("date", ascending=False),
        hide_index=True,
        width="stretch",
        column_config={"date": st.column_config.DateColumn("Date")},
    )
