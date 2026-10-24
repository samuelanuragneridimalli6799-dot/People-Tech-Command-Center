from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import utils

utils.setup("HRIS Implementation Plan")
today = utils.as_of()

st.title("HRIS Implementation Plan")
st.warning(
    "Illustrative plan based on general HRIS implementation practice, not on hands-on use of any specific product. "
    "Product names, terms and limits should be checked against the chosen vendor's documentation."
)

kickoff = st.date_input("Kickoff date", value=date(2026, 11, 2), key="kickoff")
kickoff = pd.Timestamp(kickoff)

plan = utils.load_csv("hris_plan.csv").copy()
plan["start"] = kickoff + pd.to_timedelta(plan["start_week"] * 7, unit="D")
plan["end"] = plan["start"] + pd.to_timedelta(plan["duration_weeks"] * 7, unit="D")
go_live_row = plan[plan["activity"] == "Go-live and hypercare"].iloc[0]
go_live = go_live_row["start"]

tab_gov, tab_plan, tab_raid, tab_map, tab_cut = st.tabs(
    ["Governance", "Workstream plan", "RAID log", "Data migration mapping", "Cutover checklist"]
)

with tab_gov:
    st.markdown(
        """
**Structure**
- **Steering committee** (monthly): Head of People Technology and Analytics, People, Technology, Finance and Legal leads. Owns scope, budget and go or no-go.
- **Delivery group** (weekly): workstream leads. Reviews plan, RAID log, dependencies and decisions needed.
- **Change control**: any change to scope, date or cost needs a one-page request with impact and a named approver.

**Cadence**
- Monday: RAID and dependency review; status colours updated by owners.
- Wednesday: Weekly Business Review draft circulated.
- Friday: decisions and vendor commitments recorded in the decision log.

**Principles**
- Every workstream has one accountable owner, even when several functions contribute.
- Risks are raised with a date, owner and mitigation; blockers are escalated within two working days.
- Go-live depends on exit criteria, not on the calendar.
"""
    )

with tab_plan:
    fn = st.multiselect("Function", sorted(plan["function"].unique()), default=sorted(plan["function"].unique()))
    view = plan[plan["function"].isin(fn)]
    fig = px.timeline(view, x_start="start", x_end="end", y="activity", color="workstream", hover_data=["function", "duration_weeks"])
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(title=None)
    marker = str(today.date())
    fig.add_shape(type="line", x0=marker, x1=marker, y0=0, y1=1, xref="x", yref="paper", line=dict(dash="dash", color="#555"))
    fig.update_layout(height=max(420, 30 * len(view) + 120), legend_title_text="Workstream", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, width="stretch")
    st.markdown(f"Planned go-live: **{go_live:%d %b %Y}**, followed by {int(go_live_row['duration_weeks'])} weeks of hypercare.")
    st.dataframe(
        plan[["workstream", "activity", "function", "start", "end", "duration_weeks"]],
        hide_index=True,
        width="stretch",
        column_config={"start": st.column_config.DateColumn("Start"), "end": st.column_config.DateColumn("End")},
    )

with tab_raid:
    raid = utils.score_raid(utils.load_csv("raid.csv", ("due",)))
    c1, c2 = st.columns(2)
    types = c1.multiselect("Type", sorted(raid["type"].unique()), default=sorted(raid["type"].unique()))
    status = c2.multiselect("Status", sorted(raid["status"].unique()), default=["Open"])
    view = raid[raid["type"].isin(types) & raid["status"].isin(status)].sort_values("score", ascending=False)
    st.dataframe(
        view[["id", "type", "description", "project", "owner", "probability", "impact", "score", "status", "mitigation", "due"]],
        hide_index=True,
        width="stretch",
        column_config={"due": st.column_config.DateColumn("Due"), "score": st.column_config.NumberColumn("Score (P x I)")},
    )
    grid = (
        raid[raid["type"] == "Risk"]
        .groupby(["impact", "probability"]).size().reset_index(name="count")
        .pivot(index="impact", columns="probability", values="count")
        .reindex(index=[5, 4, 3, 2, 1], columns=[1, 2, 3, 4, 5])
        .fillna(0)
    )
    fig = px.imshow(grid, text_auto=True, color_continuous_scale="Reds", labels=dict(x="Probability", y="Impact", color="Risks"), aspect="auto")
    fig.update_layout(title="Risk heat map", height=360, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, width="stretch")

with tab_map:
    mapping = utils.load_csv("migration_mapping.csv")
    done = int(mapping["status"].isin(["Mapped"]).sum())
    st.progress(done / len(mapping), text=f"{done} of {len(mapping)} field mappings agreed")
    st.dataframe(mapping, hide_index=True, width="stretch")
    blocked = mapping[mapping["status"] == "Blocked"]
    if len(blocked):
        st.error("Blocked: " + "; ".join(f"{r['source_field']} ({r['owner']})" for _, r in blocked.iterrows()))
    st.caption("Each mapping has a transformation rule, a quality rule that can be tested in each trial load, and a named owner.")

with tab_cut:
    cut = utils.load_csv("cutover_checklist.csv").copy()
    cut["target_date"] = go_live - pd.to_timedelta(cut["t_minus_days"], unit="D")
    cut = cut.sort_values("t_minus_days", ascending=False).reset_index(drop=True)
    edited = st.data_editor(
        cut[["phase", "task", "function", "target_date", "done"]],
        key="cutover_editor",
        hide_index=True,
        width="stretch",
        disabled=["phase", "task", "function", "target_date"],
        column_config={"target_date": st.column_config.DateColumn("Target date"), "done": st.column_config.CheckboxColumn("Done")},
    )
    st.progress(float(edited["done"].mean()), text=f"{int(edited['done'].sum())} of {len(edited)} cutover tasks complete")
    st.markdown(
        """
**Go or no-go exit criteria (example)**
- Zero open critical or high defects; medium defects have an owner and a date.
- Headcount, cost-centre and leave balances reconcile with Finance and payroll.
- Access and permissions verified by role for each user group.
- Support model, communications and rollback plan approved by the steering committee.
"""
    )
