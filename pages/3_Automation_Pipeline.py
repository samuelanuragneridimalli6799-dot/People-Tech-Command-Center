import pandas as pd
import plotly.express as px
import streamlit as st

import utils

utils.setup("Automation Pipeline")

st.title("Automation and AI Opportunity Pipeline")
st.caption("Requests are scoped into briefs, sized by effort and impact, and ranked. A capacity line shows what fits this quarter.")

with st.sidebar:
    st.markdown("**Scoring assumptions**")
    s_days = st.number_input("Effort S (person-days)", 1, 20, utils.DEFAULT_EFFORT_DAYS["S"])
    m_days = st.number_input("Effort M (person-days)", 1, 40, utils.DEFAULT_EFFORT_DAYS["M"])
    l_days = st.number_input("Effort L (person-days)", 1, 90, utils.DEFAULT_EFFORT_DAYS["L"])
    capacity = st.slider("Team capacity this quarter (person-days)", 10, 120, 40, step=5)

effort_days = {"S": s_days, "M": m_days, "L": l_days}
raw = utils.get_state_df("pipeline", "pipeline.csv")


def add_request() -> None:
    ss = st.session_state
    df = ss["pipeline"]
    new_id = f"P{len(df) + 1:02d}"
    row = {
        "id": new_id,
        "title": ss["f_title"],
        "requester": ss["f_requester"],
        "problem": ss["f_problem"],
        "volume_per_month": ss["f_volume"],
        "minutes_per_case": ss["f_minutes"],
        "effort": ss["f_effort"],
        "automation_rate": ss["f_rate"] / 100,
        "ai_candidate": "Yes" if ss["f_ai"] else "No",
        "self_serve_candidate": "Yes" if ss["f_self"] else "No",
        "status": "New",
    }
    ss["pipeline"] = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    ss["last_request_id"] = new_id


scored = utils.score_pipeline(raw, effort_days)
planned = utils.plan_capacity(scored, capacity)
queue = planned[planned["lane"] != "Parked"]
fits = planned[planned["lane"] == "Fits this quarter"]
wait = planned[planned["lane"] == "Waitlist"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Requests in queue", len(queue))
c2.metric("Fit this quarter", len(fits), f"{fits['effort_days'].sum()} of {capacity} days", delta_color="off")
c3.metric("On waitlist", len(wait), f"{wait['effort_days'].sum()} days", delta_color="off")
c4.metric("Hours saved per year if all done", f"{queue['hours_saved_year'].sum():,.0f}")

tab_rank, tab_chart, tab_new = st.tabs(["Ranked backlog", "Effort versus impact", "New request"])

with tab_rank:
    st.dataframe(
        planned[["id", "title", "requester", "volume_per_month", "minutes_per_case", "effort", "hours_saved_year", "score", "lane", "status", "ai_candidate", "self_serve_candidate"]],
        hide_index=True,
        width="stretch",
        column_config={
            "title": "Request",
            "requester": "Requester",
            "volume_per_month": "Cases/month",
            "minutes_per_case": "Minutes/case",
            "effort": "Effort",
            "hours_saved_year": st.column_config.NumberColumn("Hours saved/year", format="%d"),
            "score": st.column_config.NumberColumn("Score (hours per effort day)", format="%.1f"),
            "lane": "Lane",
            "status": "Status",
            "ai_candidate": "AI candidate",
            "self_serve_candidate": "Self-serve candidate",
        },
    )
    if len(wait):
        st.info(
            f"Demand exceeds capacity by {wait['effort_days'].sum()} person-days. "
            f"Suggested message to requesters on the waitlist: these {len(wait)} requests are scoped and ranked; "
            f"they start when capacity frees up or when the capacity assumption changes."
        )
    self_serve = planned[planned["self_serve_candidate"] == "Yes"]
    st.markdown(
        f"**Recurring requests that could be self-served:** {len(self_serve)} requests, "
        f"about {int(self_serve['volume_per_month'].sum())} cases per month. "
        f"Building a self-serve option removes this volume from the team queue entirely."
    )
    st.caption("Score = (cases per month x minutes per case / 60 x 12 x share automated) / effort in person-days.")

with tab_chart:
    plot = planned.copy()
    fig = px.scatter(
        plot,
        x="effort_days",
        y="hours_saved_year",
        size="volume_per_month",
        color="lane",
        text="id",
        hover_name="title",
        labels={"effort_days": "Effort (person-days)", "hours_saved_year": "Hours saved per year"},
        color_discrete_map={"Fits this quarter": "#2e9e5b", "Waitlist": "#e8a317", "Parked": "#8a8f98"},
    )
    fig.update_traces(textposition="top center")
    x_mid = plot["effort_days"].median()
    y_mid = plot["hours_saved_year"].median()
    fig.add_vline(x=x_mid, line_dash="dot", line_color="#888")
    fig.add_hline(y=y_mid, line_dash="dot", line_color="#888")
    fig.add_annotation(x=0, xref="paper", y=1, yref="paper", text="Quick wins", showarrow=False, xanchor="left", yanchor="top")
    fig.add_annotation(x=1, xref="paper", y=1, yref="paper", text="Big bets", showarrow=False, xanchor="right", yanchor="top")
    fig.add_annotation(x=0, xref="paper", y=0, yref="paper", text="Fill-ins", showarrow=False, xanchor="left", yanchor="bottom")
    fig.add_annotation(x=1, xref="paper", y=0, yref="paper", text="Avoid", showarrow=False, xanchor="right", yanchor="bottom")
    fig.update_layout(height=520, legend_title_text="", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Bubble size is cases per month. Dotted lines mark the median effort and median hours saved.")

with tab_new:
    st.markdown("Capture a stakeholder pain point as a scoped brief and add it to the backlog.")
    with st.form("new_request", clear_on_submit=True):
        st.text_input("Request title", key="f_title")
        st.text_input("Requester (team or function)", key="f_requester")
        st.text_area("Problem in one or two sentences", key="f_problem")
        a, b, c = st.columns(3)
        a.number_input("Cases per month", 1, 5000, 50, key="f_volume")
        b.number_input("Minutes per case", 1, 600, 15, key="f_minutes")
        c.selectbox("Effort", ["S", "M", "L"], index=1, key="f_effort")
        st.slider("Share of the work that can be automated (%)", 10, 100, 70, step=5, key="f_rate")
        d, e = st.columns(2)
        d.checkbox("AI could help", key="f_ai")
        e.checkbox("Could be self-served", key="f_self")
        st.form_submit_button("Add to backlog", on_click=add_request)

    new_id = st.session_state.get("last_request_id")
    if new_id:
        refreshed = utils.plan_capacity(utils.score_pipeline(st.session_state["pipeline"], effort_days), capacity)
        r = refreshed[refreshed["id"] == new_id].iloc[0]
        rank = int(refreshed.index[refreshed["id"] == new_id][0]) + 1
        brief = f"""## Brief: {r['title']}
**Request ID:** {r['id']}
**Requester:** {r['requester']}
**Problem:** {r['problem']}
**Volume:** {int(r['volume_per_month'])} cases per month at {int(r['minutes_per_case'])} minutes each, about {r['hours_per_month']:.0f} hours per month
**Proposed scope:** automate about {int(r['automation_rate'] * 100)}% of the work
**Estimated benefit:** about {r['hours_saved_year']:,.0f} hours per year
**Effort:** {r['effort']} (about {int(r['effort_days'])} person-days)
**Score:** {r['score']:.1f} hours per effort day, rank {rank} of {len(refreshed)}
**Capacity view:** {r['lane']}
**AI candidate:** {r['ai_candidate']}. **Self-serve candidate:** {r['self_serve_candidate']}.
**Open questions:** Who owns the process after launch? Which data is touched and how sensitive is it? How will success be measured?
"""
        st.success(f"Added as {new_id}. The brief is below and the ranking has updated.")
        st.markdown(brief)
        st.download_button("Download brief", brief, file_name=f"brief_{new_id}.md", mime="text/markdown")
