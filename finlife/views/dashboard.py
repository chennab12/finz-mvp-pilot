"""Financial Dashboard: the whole picture on one page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finlife import actions, insights, metrics
from finlife.data import networth
from finlife.data import transactions as tx
from finlife.ui import charts
from finlife.ui import common as ui


def render() -> None:
    data, today = ui.data(), ui.today()
    st.title("📊 Financial Dashboard")
    st.caption("Your money at a glance. Totals leave out transfers between your own accounts and credit-card "
               "repayments, so nothing is counted twice.")
    ui.sample_banner()
    m = metrics.compute(data, today)
    summary = m["summary"]

    months = list(summary["month"])
    if months:
        default = m["full_months"][-1] if m["full_months"] else months[-1]
        if st.session_state.get("dash_month") not in months:
            st.session_state.dash_month = default
        month = st.selectbox("Month", months, key="dash_month",
                             format_func=lambda x: pd.Period(x).strftime("%B %Y") + (" (so far)" if x == m["current_month"] else ""))
        row = summary.set_index("month").loc[month]
        rate = row["surplus"] / row["income"] if row["income"] > 0 else None
    else:
        month, row, rate = None, None, None

    c = st.columns(4)
    c[0].metric("💵 Income", ui.fmt0(row["income"]) if row is not None else "—")
    c[1].metric("🛒 Spending", ui.fmt0(row["spending"]) if row is not None else "—")
    c[2].metric("📈 Left over", ui.fmt0(row["surplus"]) if row is not None else "—",
                delta=f"{rate:.0%} savings rate" if rate is not None else None,
                delta_color="normal" if (rate or 0) >= 0 else "inverse")
    c[3].metric("🏦 Net worth", ui.fmt0(m["net_worth"]),
                help="Account balances minus debts, from Accounts & Net Worth.")
    c = st.columns(4)
    em = m["emergency_months"]
    c[0].metric("🛟 Emergency fund", f"{em:.1f} months" if em is not None else "—",
                help=f"Emergency savings ÷ essential spending of {ui.fmt0(m['essentials'])}/month "
                     f"({m['essentials_basis']}). Target: {m['emergency_target_months']:g} months.")
    c[1].metric("💳 Total debt", ui.fmt0(m["liabilities"]))
    due30 = sum(u["amount"] or 0 for u in m["upcoming"] if u["section"] in ("bills", "bills-future", "debts"))
    c[2].metric("📅 Due next 30 days", ui.fmt0(due30), help="Recurring bills and debt minimum payments.")
    acts = actions.build_actions(data, m, today, ui.fmt0)
    high = sum(a["priority"] == "High" for a in acts)
    c[3].metric("✅ Open actions", f"{len(acts)}", delta=f"{high} high priority" if high else "none urgent",
                delta_color="inverse" if high else "off")

    if not months:
        st.info("No transactions yet. Add or import them in **Income & Expenses**, or load the sample household "
                "from the sidebar.")
    else:
        left, right = st.columns([3, 2])
        with left:
            ui.show_fig(charts.income_vs_spending(summary.tail(12)))
        with right:
            cats = tx.category_spending(data["transactions"], month)
            if cats.empty or not (cats["spent"] > 0).any():
                st.info("No spending recorded for this month.")
            else:
                ui.show_fig(charts.category_donut(cats, f"Where the money went, {pd.Period(month).strftime('%b %Y')}"))

        left, right = st.columns([3, 2])
        with left:
            bva = tx.budget_vs_actual(data["transactions"], data["budgets"], month)
            bva = bva[bva["budget"] > 0]
            if bva.empty:
                st.info("Set monthly budgets in **Budget & Goals** to compare plan vs actual here.")
            else:
                ui.show_fig(charts.budget_bars(bva, "Budget vs spent"))
        with right:
            st.markdown("#### 🔎 What stands out")
            flags = tx.flag_table(data["transactions"])
            found = insights.build_insights(data["transactions"], month, data["budgets"], ui.fmt0, flags)
            if not found:
                st.caption("Nothing unusual this month.")
            for item in found[:4]:
                with st.container(border=True):
                    st.markdown(f"{item['icon']} **{ui.md(item['title'])}**  \n{ui.md(item['detail'])}")
                    st.caption(f"Rule: {item['rule']}")

    left, right = st.columns([3, 2])
    with left:
        hist = networth.history(data.get("net_worth_log", []))
        if len(hist) >= 2:
            ui.show_fig(charts.net_worth_trend(hist))
        else:
            st.info("Record net-worth snapshots in **Accounts & Net Worth** to see a trend here.")
    with right:
        st.markdown("#### 🔥 Top actions")
        for a in acts[:5]:
            st.markdown(f'<span class="fl-pill fl-{a["priority"]}">{a["priority"]}</span> {a["icon"]} '
                        f'{ui.md(a["title"])}', unsafe_allow_html=True)
        if not acts:
            st.success("Nothing needs attention right now.")
        ui.page_link("actions", "Open the Action Center", icon="➡️")

    ui.explain("How the dashboard numbers are calculated", f"""
- **Income** is money in, in income categories (Salary, Interest, Other income). **Spending** is money out in every
  other category, minus refunds. **Transfer** and **Credit card payment** rows are left out on both sides, so a card
  purchase is counted once.
- **Left over** = income − spending. **Savings rate** = left over ÷ income.
- **Net worth** = the balances in Accounts − the balances in Debts. It is only as current as those balances.
- **Emergency fund** = balances of accounts ticked *Emergency fund* ÷ average essential spending
  ({", ".join(metrics.ESSENTIAL_CATEGORIES)}) over complete months.
- **What stands out** comes from fixed rules shown under each item; there is no AI guessing.
""")
