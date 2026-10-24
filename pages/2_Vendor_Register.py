import pandas as pd
import plotly.express as px
import streamlit as st

import utils

utils.setup("Vendor Register")
today = utils.as_of()

st.title("Vendor and Contract Register")
st.caption("Single source of truth for People SaaS contracts. Notice deadline = renewal date minus notice period.")

v = utils.enrich_vendors(utils.load_csv("vendors.csv", ("renewal_date",)), today)

upcoming = v[(v["days_to_notice"] >= 0) & (v["days_to_notice"] <= 90)]
locked = v[v["flag"] == "Locked in (auto-renewed)"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annual spend", f"EUR {v['annual_value_eur'].sum():,.0f}")
c2.metric("Decisions due in 90 days", len(upcoming), f"EUR {upcoming['annual_value_eur'].sum():,.0f}", delta_color="off")
c3.metric("Already locked in", len(locked), f"EUR {locked['annual_value_eur'].sum():,.0f}", delta_color="off")
c4.metric("Average satisfaction (1-5)", f"{v['satisfaction'].mean():.1f}")

cats = ["All"] + sorted(v["category"].unique())
cat = st.selectbox("Category", cats)
view = v if cat == "All" else v[v["category"] == cat]
view = view.sort_values("days_to_notice")

st.dataframe(
    view[["vendor", "category", "annual_value_eur", "renewal_date", "notice_days", "notice_deadline", "days_to_notice", "flag", "auto_renew", "owner", "status"]],
    hide_index=True,
    width="stretch",
    column_config={
        "vendor": "Vendor",
        "category": "Category",
        "annual_value_eur": st.column_config.NumberColumn("Annual EUR", format="%d"),
        "renewal_date": st.column_config.DateColumn("Renewal"),
        "notice_days": "Notice (days)",
        "notice_deadline": st.column_config.DateColumn("Notice deadline"),
        "days_to_notice": "Days left",
        "flag": "Flag",
        "auto_renew": "Auto-renew",
        "owner": "Owner",
        "status": "Status",
    },
)

left, right = st.columns(2)
with left:
    spend = v.groupby("category", as_index=False)["annual_value_eur"].sum().sort_values("annual_value_eur")
    fig = px.bar(spend, x="annual_value_eur", y="category", orientation="h", labels={"annual_value_eur": "Annual EUR", "category": ""})
    fig.update_layout(title="Spend by category", height=360, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, width="stretch")
with right:
    horizon = v[v["notice_deadline"] <= today + pd.Timedelta(days=365)].sort_values("notice_deadline")
    fig = px.scatter(
        horizon,
        x="notice_deadline",
        y="vendor",
        size="annual_value_eur",
        color="flag",
        color_discrete_map=utils.FLAG_COLORS,
        labels={"notice_deadline": "Notice deadline", "vendor": ""},
    )
    marker = str(today.date())
    fig.add_shape(type="line", x0=marker, x1=marker, y0=0, y1=1, xref="x", yref="paper", line=dict(dash="dash", color="#555"))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title="Notice deadlines, next 12 months", height=360, legend_title_text="", margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, width="stretch")

st.subheader("Review activity plan")
vendor_name = st.selectbox("Vendor", v.sort_values("days_to_notice")["vendor"].tolist())
row = v[v["vendor"] == vendor_name].iloc[0]
st.markdown(
    f"**{row['vendor']}** ({row['category']}), EUR {row['annual_value_eur']:,.0f}/year. "
    f"Renewal {row['renewal_date']:%d %b %Y}, notice deadline **{row['notice_deadline']:%d %b %Y}** "
    f"({int(row['days_to_notice'])} days). Flag: {row['flag']}."
)
st.markdown(f"Contract notes: {row['contract_notes']}. Alternatives on watch: {row['alternatives_watchlist']}.")

plan = utils.vendor_review_plan(row["notice_deadline"], today)
if row["flag"] == "Locked in (auto-renewed)":
    st.warning("The notice window has passed and the contract auto-renews. Plan the review for the next cycle and ask for a mid-term exit or downgrade option now.")
elif (plan["status"] == "Overdue").any():
    st.warning(f"{int((plan['status'] == 'Overdue').sum())} review steps are already past due. Compress the plan or request a short extension from the vendor.")
st.dataframe(
    plan,
    hide_index=True,
    width="stretch",
    column_config={
        "due": st.column_config.DateColumn("Due"),
        "days_before_deadline": "Days before deadline",
        "activity": "Activity",
        "owner": "Owner",
        "status": "Status",
    },
)
st.download_button("Download plan as CSV", plan.to_csv(index=False), file_name=f"review_plan_{vendor_name.split()[0].lower()}.csv", mime="text/csv")
