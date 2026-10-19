"""Budget & Goals: monthly budgets, recurring bills, savings goals and a cash-flow projection."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finlife import metrics
from finlife.data import planning, storage
from finlife.data import transactions as tx
from finlife.ui import charts
from finlife.ui import common as ui

ss = st.session_state


def _budgets(data: dict, m: dict) -> None:
    summary = m["summary"]
    months = list(summary["month"]) or [m["current_month"]]
    if ss.get("bud_month") not in months:
        ss.bud_month = m["current_month"] if m["current_month"] in months else months[-1]
    left, right = st.columns([2, 3])
    with left:
        st.markdown("#### Monthly budgets")
        st.caption("One row per spending category. Leave a category out if you don't want to track it.")
        ui.edit_records("budgets", {
            "category": st.column_config.SelectboxColumn("Category", options=tx.SPENDING_CATEGORIES, required=True),
            "monthly_budget": ui.money_col("Monthly budget", min_value=0.0, required=True),
        }, height=420)
        total = sum(planning.to_float(b.get("monthly_budget")) or 0 for b in data["budgets"])
        st.metric("Total monthly budget", ui.fmt0(total),
                  help="Compare with your average income on the Dashboard.")
        if m["avg_income"]:
            st.caption(f"Average monthly income over complete months: **{ui.md(ui.fmt0(m['avg_income']))}**.")
    with right:
        month = st.selectbox("Compare against", months, key="bud_month",
                             format_func=lambda x: pd.Period(x).strftime("%B %Y"))
        bva = tx.budget_vs_actual(data["transactions"], data["budgets"], month)
        bva = bva[bva["budget"] > 0]
        if bva.empty:
            st.info("Add budgets on the left to compare them with spending.")
            return
        ui.show_fig(charts.budget_bars(bva, "Budget vs spent"))
        a, b, c = st.columns(3)
        a.metric("Budgeted", ui.fmt0(bva["budget"].sum()))
        b.metric("Spent in these categories", ui.fmt0(bva["actual"].sum()))
        c.metric("Over budget", f"{int((bva['actual'] > bva['budget']).sum())} categories")
        st.dataframe(bva.assign(used=bva["used_pct"] / 100), hide_index=True, width="stretch",
                     column_order=["category", "budget", "actual", "remaining", "used"],
                     column_config={"category": "Category", "budget": ui.money_col("Budget"),
                                    "actual": ui.money_col("Spent"), "remaining": ui.money_col("Remaining"),
                                    "used": st.column_config.ProgressColumn("Used", min_value=0, max_value=1.5,
                                                                            format="percent")})
    unbudgeted = tx.category_spending(data["transactions"], month)
    budgeted = {b["category"] for b in data["budgets"]}
    unbudgeted = unbudgeted[(~unbudgeted["category"].isin(budgeted)) & (unbudgeted["spent"] > 0)]
    if not unbudgeted.empty:
        st.caption("Spending with no budget this month: " + ui.md(", ".join(
            f"{r.category} {ui.fmt0(r.spent)}" for r in unbudgeted.itertuples())))


def _goals(data: dict, today) -> None:
    st.markdown("#### Savings goals")
    st.caption("Enter what you want to save, what you have, what you add each month and when you need it.")
    ui.edit_records("goals", {
        "name": st.column_config.TextColumn("Goal", required=True),
        "target": ui.money_col("Target", min_value=0.0),
        "saved": ui.money_col("Saved so far", min_value=0.0),
        "monthly_contribution": ui.money_col("Adding per month", min_value=0.0),
        "deadline": ui.date_col("Deadline"),
    })
    statuses = [g for g in (planning.goal_status(g, today) for g in data["goals"]) if g]
    if not statuses:
        st.info("Add a goal above to track it.")
        return
    cols = st.columns(min(3, len(statuses)))
    for i, g in enumerate(statuses):
        with cols[i % len(cols)].container(border=True):
            st.markdown(f"**{g['icon']} {g['name']}** · {g['status']}")
            st.progress(g["progress"], text=ui.md(f"{ui.fmt0(g['saved'])} of {ui.fmt0(g['target'])} ({g['progress']:.0%})"))
            lines = []
            if g["remaining"] > 0 and g["required"] is not None:
                lines.append(f"Needs {ui.fmt0(g['required'])}/month to hit {g['deadline']:%b %Y}; plan is "
                             f"{ui.fmt0(g['planned'])}.")
            if g["projected_date"]:
                lines.append(f"At the current pace: reached around **{g['projected_date']:%b %Y}**.")
            elif g["remaining"] > 0 and g["planned"] == 0:
                lines.append("No monthly amount set, so no finish date.")
            st.caption(ui.md(" ".join(lines)) or "Done!")
    fig = go.Figure()
    names = [g["name"] for g in statuses]
    fig.add_bar(y=names, x=[g["saved"] for g in statuses], name="Saved", orientation="h", marker_color=ui.AQUA)
    fig.add_bar(y=names, x=[g["remaining"] for g in statuses], name="Still to save", orientation="h",
                marker_color="rgba(128,128,128,0.30)")
    fig.update_layout(title="Progress toward each goal", barmode="stack", hovermode="y unified")
    ui.show_fig(ui.style_fig(fig, height=max(220, 50 * len(statuses) + 100), money_axis="x"))
    ui.estimate_note("Goal dates assume you add the same amount every month and earn no interest.")


def _bills(data: dict, today) -> None:
    st.markdown("#### Recurring bills")
    st.caption("Bills that repeat. Mark one paid in the **Action Center** and its next due date moves forward.")
    ui.edit_records("bills", {
        "name": st.column_config.TextColumn("Bill", required=True),
        "amount": ui.money_col("Amount", min_value=0.0),
        "frequency": st.column_config.SelectboxColumn("Repeats", options=storage.BILLING, required=True),
        "next_due": ui.date_col("Next due"),
        "category": st.column_config.SelectboxColumn("Category", options=tx.SPENDING_CATEGORIES),
        "autopay": st.column_config.CheckboxColumn("Autopay"),
        "active": st.column_config.CheckboxColumn("Active", default=True),
    })
    a, b = st.columns(2)
    a.metric("Bills per month (average)", ui.fmt0(planning.monthly_equivalent(data["bills"])),
             help="Yearly bills ÷ 12, weekly × 52 ÷ 12, quarterly × 4 ÷ 12.")
    soon = planning.bill_occurrences(data["bills"], today, today + pd.Timedelta(days=30).to_pytimedelta())
    b.metric("Due in the next 30 days", ui.fmt0(sum(x["amount"] for x in soon)))


def _projection(data: dict, m: dict, today) -> None:
    st.markdown("#### Cash-flow projection")
    st.caption("Where your checking balance could be heading if the next months look like your average month.")
    bill_cats = {b.get("category") for b in data["bills"] if b.get("active") is not False}
    full = m["full_months"]
    work = tx.counted(data["transactions"])
    work = work[(work["group"] == "spending") & work["month"].isin(full) & ~work["category"].isin(bill_cats)]
    variable = float(-work["amount"].sum() / len(full)) if full else 0.0
    goal_total = sum(g["planned"] for g in m["goals"] if g["remaining"] > 0)
    c = st.columns(4)
    start = c[0].number_input("Starting balance", value=float(data["settings"].get("starting_balance") or 0.0),
                              step=100.0, key=f"proj_start_{ss.ver}")
    data["settings"]["starting_balance"] = start
    income = c[1].number_input("Monthly income", value=round(m["avg_income"], 2), min_value=0.0, step=100.0,
                               key=f"proj_inc_{ss.ver}")
    var = c[2].number_input("Other monthly spending", value=round(variable, 2), min_value=0.0, step=50.0,
                            key=f"proj_var_{ss.ver}", help="Average spending outside your bill categories.")
    months = c[3].slider("Months ahead", 3, 24, 12, key="proj_months")
    proj = planning.cash_flow_projection(today=today, months=months, starting_balance=start, monthly_income=income,
                                         monthly_variable_spending=var, bills=data["bills"],
                                         goal_contributions=goal_total)
    fig = go.Figure()
    fig.add_bar(x=proj["Month"], y=proj["Income"], name="Income", marker_color=ui.AQUA)
    fig.add_bar(x=proj["Month"], y=-(proj["Bills"] + proj["Variable spending"] + proj["Goal savings"]),
                name="Bills, spending and goal savings", marker_color=ui.ORANGE)
    fig.add_scatter(x=proj["Month"], y=proj["Closing"], name="Month-end balance", mode="lines+markers",
                    line=dict(color=ui.BLUE, width=3))
    fig.update_layout(title="Projected month-end balance", barmode="relative")
    ui.show_fig(ui.style_fig(fig))
    low = proj["Closing"].min()
    if low < 0:
        st.warning(ui.md(f"The balance dips below zero ({ui.fmt0(low)}) in {proj.loc[proj['Closing'].idxmin(), 'Month']}."))
    with st.expander("Projection table and assumptions"):
        st.dataframe(proj, hide_index=True, width="stretch",
                     column_config={k: ui.money_col(k) for k in proj.columns if k != "Month"})
        st.markdown(ui.md(f"""
- Income: {ui.fmt0(income)} every month (default: your average over complete months).
- Other spending: {ui.fmt0(var)} every month (default: average spending outside the categories your bills use).
- Bills: placed in the month they fall due, from your recurring bills.
- Goal savings: {ui.fmt0(goal_total)} every month (the monthly amounts of unfinished goals).
"""))
    ui.estimate_note("A projection from flat averages, not a forecast. Real months vary.")


def render() -> None:
    data, today = ui.data(), ui.today()
    st.title("🎯 Budget & Goals")
    st.caption("Plan the month, track what's coming and save toward what matters.")
    ui.sample_banner()
    m = metrics.compute(data, today)
    t1, t2, t3, t4 = st.tabs(["📒 Budgets", "🎯 Savings goals", "💵 Recurring bills", "🔮 Cash-flow projection"])
    with t1:
        _budgets(data, m)
    with t2:
        _goals(data, today)
    with t3:
        _bills(data, today)
    with t4:
        _projection(data, m, today)
    ui.explain("Budgeting in plain English", """
A **budget** is a spending limit per category per month. Compare it with what you actually spent; when a category
runs over, either spend less there for the rest of the month or set a more realistic number.

A **savings goal** needs three numbers: the target, what you have and what you add each month. The app shows
whether that monthly amount reaches the target by the deadline (*On track* or *Behind*).

**Recurring bills** feed the Action Center reminders and the cash-flow projection.
""")
