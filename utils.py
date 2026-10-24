"""Shared helpers for the People Tech Command Centre demo.

All data is synthetic. The fictional company is "Northwind Mobility".
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
DEMO_DATE = date(2026, 10, 26)

RAG_COLORS = {
    "Red": "#d64545",
    "Amber": "#e8a317",
    "Green": "#2e9e5b",
    "Done": "#8a8f98",
}

FLAG_COLORS = {
    "Critical (30 days or less)": "#d64545",
    "Act now (60 days or less)": "#e8a317",
    "Plan (90 days or less)": "#4c8bf5",
    "OK": "#2e9e5b",
    "Locked in (auto-renewed)": "#8a8f98",
    "Decision overdue": "#a02c2c",
}

DEFAULT_EFFORT_DAYS = {"S": 3, "M": 10, "L": 25}


# --------------------------------------------------------------------------
# Page setup and data loading
# --------------------------------------------------------------------------
def setup(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | People Tech Command Centre",
        page_icon=":compass:",
        layout="wide",
    )
    if "as_of" not in st.session_state:
        st.session_state["as_of"] = DEMO_DATE
    with st.sidebar:
        st.markdown("**People Tech Command Centre**")
        st.caption("Demo built on synthetic data. Fictional company: Northwind Mobility.")
        st.date_input(
            "As-of date",
            key="as_of",
            help="Change this to see flags, deadlines and the weekly review update.",
        )


def as_of() -> pd.Timestamp:
    return pd.Timestamp(st.session_state["as_of"])


@st.cache_data
def load_csv(name: str, date_cols: tuple = ()) -> pd.DataFrame:
    return pd.read_csv(DATA / name, parse_dates=list(date_cols))


def get_state_df(key: str, filename: str, date_cols: tuple = ()) -> pd.DataFrame:
    """Return a session-scoped copy of a CSV so edits survive page changes."""
    if key not in st.session_state:
        st.session_state[key] = load_csv(filename, tuple(date_cols)).copy()
    return st.session_state[key]


def get_initiatives() -> pd.DataFrame:
    df = get_state_df("initiatives", "initiatives.csv", ("start", "end", "next_milestone_date"))
    for col in ("start", "end", "next_milestone_date"):
        df[col] = pd.to_datetime(df[col])
    return df


# --------------------------------------------------------------------------
# Roadmap logic
# --------------------------------------------------------------------------
def _text(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


def enrich_initiatives(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    df = df.copy()
    is_open = df["rag"] != "Done"
    df["milestone_overdue"] = is_open & (df["next_milestone_date"] < today)
    df["days_overdue"] = (today - df["next_milestone_date"]).dt.days.where(df["milestone_overdue"], 0)
    df["slipped"] = is_open & (df["end"] < today) & (df["pct_complete"] < 100)
    return df


def dependency_risks(df: pd.DataFrame) -> pd.DataFrame:
    """Open initiatives that depend on something Red, Amber or overdue."""
    by_id = df.set_index("id")
    rows = []
    for _, row in df[df["rag"] != "Done"].iterrows():
        for dep_id in _text(row["depends_on"]).split(";"):
            dep_id = dep_id.strip()
            if not dep_id or dep_id not in by_id.index:
                continue
            dep = by_id.loc[dep_id]
            reasons = []
            if dep["rag"] in ("Red", "Amber"):
                reasons.append(f"{dep['rag']} status")
            if dep["milestone_overdue"]:
                reasons.append(f"milestone {int(dep['days_overdue'])} days late")
            if reasons:
                rows.append(
                    {
                        "at_risk": f"{row['id']} {row['initiative']}",
                        "depends_on": f"{dep_id} {dep['initiative']}",
                        "why": ", ".join(reasons),
                        "severity": "Red" if dep["rag"] == "Red" else "Amber",
                    }
                )
    return pd.DataFrame(rows, columns=["at_risk", "depends_on", "why", "severity"])


def score_raid(raid: pd.DataFrame) -> pd.DataFrame:
    raid = raid.copy()
    raid["score"] = raid["probability"] * raid["impact"]
    return raid


def build_wbr(df: pd.DataFrame, raid: pd.DataFrame, today: pd.Timestamp) -> str:
    """Rule-based Weekly Business Review. No AI call, every line traceable to data."""
    df = enrich_initiatives(df, today)
    active = df[df["rag"] != "Done"]
    counts = active["rag"].value_counts()
    red, amber, green = (int(counts.get(k, 0)) for k in ("Red", "Amber", "Green"))
    done = int((df["rag"] == "Done").sum())
    deps = dependency_risks(df)
    raid = score_raid(raid)
    open_raid = raid[raid["status"] == "Open"].sort_values("score", ascending=False)

    lines = [
        "# Weekly Business Review: People Technology and Analytics",
        f"Week of {today:%d %b %Y}",
        "",
        "## Headline",
        f"{len(active)} active initiatives: {green} green, {amber} amber, {red} red. {done} completed.",
    ]
    attention = df[(df["rag"] == "Red") | df["slipped"] | df["milestone_overdue"]]
    if attention.empty:
        lines.append("No initiatives are red, slipped or carrying overdue milestones.")
    else:
        lines.append(
            f"{len(attention)} need attention this week, led by "
            + ", ".join(f"{r['id']} {r['initiative']}" for _, r in attention.head(3).iterrows())
            + "."
        )

    lines += ["", "## Red and blocked"]
    blocked = active[(active["rag"] == "Red") | active["blocker"].notna() & (active["blocker"] != "")]
    if blocked.empty:
        lines.append("None.")
    for _, r in blocked.iterrows():
        line = f"- **{r['id']} {r['initiative']}** ({r['rag']}, {r['pct_complete']}% complete)."
        if _text(r["blocker"]):
            line += f" Blocker: {_text(r['blocker'])}."
        if r["milestone_overdue"]:
            line += f" Milestone '{r['next_milestone']}' is {int(r['days_overdue'])} days late."
        lines.append(line)

    lines += ["", "## Slipped or overdue"]
    slipped = df[df["slipped"] | df["milestone_overdue"]]
    if slipped.empty:
        lines.append("None.")
    for _, r in slipped.iterrows():
        parts = []
        if r["slipped"]:
            parts.append(f"end date {r['end']:%d %b} passed at {r['pct_complete']}% complete")
        if r["milestone_overdue"]:
            parts.append(f"'{r['next_milestone']}' due {r['next_milestone_date']:%d %b}")
        lines.append(f"- **{r['id']} {r['initiative']}**: " + "; ".join(parts) + ".")

    lines += ["", "## Decisions needed"]
    decisions = active[active["decision_needed"].notna() & (active["decision_needed"] != "")]
    if decisions.empty:
        lines.append("None.")
    for _, r in decisions.iterrows():
        lines.append(f"- **{r['id']}**: {_text(r['decision_needed'])}.")

    lines += ["", "## Cross-project dependencies at risk"]
    if deps.empty:
        lines.append("None.")
    for _, r in deps.iterrows():
        lines.append(f"- {r['at_risk']} depends on {r['depends_on']} ({r['why']}).")

    lines += ["", "## Top open risks and issues"]
    top = open_raid.head(4)
    if top.empty:
        lines.append("None.")
    for _, r in top.iterrows():
        lines.append(f"- {r['id']} ({r['type']}, score {int(r['score'])}): {r['description']}. Next step: {r['mitigation']}.")

    lines += ["", "## Next 14 days"]
    soon = active[
        (active["next_milestone_date"] >= today)
        & (active["next_milestone_date"] <= today + pd.Timedelta(days=14))
    ].sort_values("next_milestone_date")
    if soon.empty:
        lines.append("No milestones due.")
    for _, r in soon.iterrows():
        lines.append(f"- {r['next_milestone_date']:%d %b}: {r['next_milestone']} ({r['id']}).")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Vendor logic
# --------------------------------------------------------------------------
def enrich_vendors(v: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    v = v.copy()
    v["notice_deadline"] = v["renewal_date"] - pd.to_timedelta(v["notice_days"], unit="D")
    v["days_to_notice"] = (v["notice_deadline"] - today).dt.days

    def flag(row) -> str:
        d = row["days_to_notice"]
        if d < 0:
            return "Locked in (auto-renewed)" if row["auto_renew"] == "Yes" else "Decision overdue"
        if d <= 30:
            return "Critical (30 days or less)"
        if d <= 60:
            return "Act now (60 days or less)"
        if d <= 90:
            return "Plan (90 days or less)"
        return "OK"

    v["flag"] = v.apply(flag, axis=1)
    return v


VENDOR_REVIEW_STEPS = [
    (120, "Collect usage, cost and incident data", "Vendor Manager"),
    (105, "Gather stakeholder feedback and pain points", "People Partners"),
    (90, "Scan the market and update alternatives", "Vendor Manager"),
    (75, "Request pricing and product roadmap from incumbent and two alternatives", "Vendor Manager"),
    (60, "Legal and security review of renewal terms", "Legal"),
    (45, "Score options and draft recommendation", "Project Manager"),
    (30, "Decision at steering committee", "Steering Committee"),
    (14, "Negotiate and agree terms, or prepare notice", "Vendor Manager and Legal"),
    (0, "Notice deadline: send notice or sign renewal", "Vendor Manager"),
]


def vendor_review_plan(deadline: pd.Timestamp, today: pd.Timestamp) -> pd.DataFrame:
    rows = []
    next_marked = False
    for offset, activity, owner in VENDOR_REVIEW_STEPS:
        due = deadline - pd.Timedelta(days=offset)
        if due < today:
            status = "Overdue"
        elif not next_marked:
            status, next_marked = "Next", True
        else:
            status = "Upcoming"
        rows.append({"due": due, "days_before_deadline": offset, "activity": activity, "owner": owner, "status": status})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Automation pipeline logic
# --------------------------------------------------------------------------
def score_pipeline(df: pd.DataFrame, effort_days: dict[str, int]) -> pd.DataFrame:
    df = df.copy()
    df["effort_days"] = df["effort"].map(effort_days)
    df["hours_per_month"] = df["volume_per_month"] * df["minutes_per_case"] / 60
    df["hours_saved_year"] = df["hours_per_month"] * 12 * df["automation_rate"]
    df["score"] = df["hours_saved_year"] / df["effort_days"]
    return df.sort_values("score", ascending=False).reset_index(drop=True)


def plan_capacity(scored: pd.DataFrame, capacity_days: int) -> pd.DataFrame:
    scored = scored.copy()
    queue = scored["status"] != "Parked"
    scored["cum_effort_days"] = scored["effort_days"].where(queue, 0).cumsum()
    scored["lane"] = "Parked"
    scored.loc[queue & (scored["cum_effort_days"] <= capacity_days), "lane"] = "Fits this quarter"
    scored.loc[queue & (scored["cum_effort_days"] > capacity_days), "lane"] = "Waitlist"
    return scored
