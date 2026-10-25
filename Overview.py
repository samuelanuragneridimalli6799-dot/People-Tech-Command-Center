import pandas as pd
import streamlit as st

import utils

utils.setup("Overview")
today = utils.as_of()

st.title("People Tech Command Centre")
st.caption(
    "A working demo of how one person can keep People Technology and People Analytics delivery visible: "
    "roadmap, vendors, automation demand and an HRIS implementation plan in one place. "
    "Synthetic data, fictional company."
)

initiatives = utils.enrich_initiatives(utils.get_initiatives(), today)
vendors = utils.enrich_vendors(utils.load_csv("vendors.csv", ("renewal_date",)), today)
pipeline = utils.plan_capacity(
    utils.score_pipeline(utils.get_state_df("pipeline", "pipeline.csv"), utils.DEFAULT_EFFORT_DAYS), 40
)

active = initiatives[initiatives["rag"] != "Done"]
red = int((active["rag"] == "Red").sum())
amber = int((active["rag"] == "Amber").sum())
due_soon = vendors[(vendors["days_to_notice"] >= 0) & (vendors["days_to_notice"] <= 90)]
queue = pipeline[pipeline["lane"] != "Parked"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active initiatives", len(active), f"{red} red, {amber} amber", delta_color="off")
c2.metric("Milestones overdue", int(initiatives["milestone_overdue"].sum()))
c3.metric("Vendor decisions due in 90 days", len(due_soon), f"EUR {due_soon['annual_value_eur'].sum():,.0f} in scope", delta_color="off")
c4.metric("Hours/year in automation backlog", f"{queue['hours_saved_year'].sum():,.0f}")

st.subheader("What needs attention this week")
left, right = st.columns(2)

with left:
    st.markdown("**Delivery**")
    attention = initiatives[(initiatives["rag"] == "Red") | initiatives["milestone_overdue"]]
    if attention.empty:
        st.write("Nothing red or overdue.")
    for _, r in attention.iterrows():
        late = f" Milestone {int(r['days_overdue'])} days late." if r["milestone_overdue"] else ""
        blocker = f" Blocker: {r['blocker']}." if isinstance(r["blocker"], str) and r["blocker"] else ""
        st.markdown(f"- **{r['id']} {r['initiative']}** ({r['rag']}).{late}{blocker}")

with right:
    st.markdown("**Vendors**")
    urgent = vendors[vendors["flag"].isin(["Critical (30 days or less)", "Decision overdue"])].sort_values("days_to_notice")
    if urgent.empty:
        st.write("No vendor deadline inside 30 days.")
    for _, r in urgent.iterrows():
        st.markdown(
            f"- **{r['vendor']}** ({r['category']}): notice deadline {r['notice_deadline']:%d %b %Y}, "
            f"{int(r['days_to_notice'])} days, EUR {r['annual_value_eur']:,.0f}/year."
        )
    st.markdown("**Automation backlog: top 3 by hours saved per effort day**")
    for _, r in queue.head(3).iterrows():
        st.markdown(f"- **{r['title']}**: about {r['hours_saved_year']:,.0f} hours/year, effort {r['effort']} ({r['lane'].lower()}).")

st.divider()
st.subheader("Pages")
st.markdown(
    """
1. **Roadmap and WBR**: one roadmap across projects, editable status, dependency checks, and a Weekly Business Review generated from the data.
2. **Vendor Register**: single source of truth for contracts and renewals, notice deadlines and a dated review plan for each vendor.
3. **Automation Pipeline**: intake form that writes a scoped brief, ranking by hours saved per effort day, and a capacity line for managing expectations.
4. **HRIS Implementation Plan**: illustrative plan with workstreams, RAID log, data migration mapping and cutover checklist.
"""
)

with st.expander("How this was built and what is simplified"):
    st.markdown(
        """
- Built with Python, Streamlit, pandas and Plotly. Built with AI assistance; the structure, rules and content decisions are the author's.
- All numbers, vendors and people are synthetic. Nothing here comes from a real employer.
- The review text is rule-based: every sentence maps to a row in the data, so it can be audited.
- The scoring model is deliberately simple (hours saved per year divided by effort in person-days). Change the effort assumptions on the Automation Pipeline page and watch the ranking move.
- Edits made in the app live in the session only. A production version would write to a database or a Jira and Confluence integration.
"""
    )
