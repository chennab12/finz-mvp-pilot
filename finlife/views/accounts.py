"""Accounts & Net Worth: what you own, what you owe, and how it changes over time."""

from __future__ import annotations

import streamlit as st

from finlife import metrics
from finlife.data import networth, storage
from finlife.ui import charts
from finlife.ui import common as ui

ss = st.session_state


def _snapshot() -> None:
    ss.data["net_worth_log"] = networth.record_snapshot(ss.data["net_worth_log"], ss.data["accounts"],
                                                        ss.data["debts"], ui.today(), ss.get("snap_note", ""))
    ui.commit("Recorded today's net worth.")


def render() -> None:
    data, today = ui.data(), ui.today()
    st.title("🏦 Accounts & Net Worth")
    st.caption("Type in current balances. Net worth = everything you own − everything you owe.")
    ui.sample_banner()

    left, right = st.columns(2)
    with left:
        st.markdown("#### What you own")
        ui.edit_records("accounts", {
            "name": st.column_config.TextColumn("Account", required=True),
            "type": st.column_config.SelectboxColumn("Type", options=storage.ACCOUNT_TYPES, required=True),
            "balance": ui.money_col("Balance", min_value=0.0),
            "emergency_fund": st.column_config.CheckboxColumn("Emergency fund",
                                                              help="Tick cash you keep for emergencies."),
        })
    with right:
        st.markdown("#### What you owe")
        ui.edit_records("debts", {
            "name": st.column_config.TextColumn("Debt", required=True),
            "type": st.column_config.SelectboxColumn("Type", options=storage.DEBT_TYPES, required=True),
            "balance": ui.money_col("Balance", min_value=0.0),
            "apr": st.column_config.NumberColumn("APR %", min_value=0.0, max_value=100.0, format="%.2f"),
            "min_payment": ui.money_col("Minimum payment", min_value=0.0),
            "next_due": ui.date_col("Next payment due"),
        })

    t = networth.totals(data["accounts"], data["debts"])
    m = metrics.compute(data, today)
    c = st.columns(4)
    c[0].metric("Assets", ui.fmt0(t["assets"]))
    c[1].metric("Debts", ui.fmt0(t["liabilities"]))
    c[2].metric("Net worth", ui.fmt0(t["net_worth"]))
    monthly_interest = sum(d["monthly_interest"] for d in m["debts"])
    c[3].metric("Debt interest per month", ui.fmt0(monthly_interest), help="Balance × APR ÷ 12 for each debt.")

    left, right = st.columns(2)
    with left:
        own = networth.by_type(data["accounts"])
        if not own.empty:
            ui.show_fig(charts.horizontal_totals(own, "type", "balance", "Assets by type", ui.AQUA))
    with right:
        owe = networth.by_type(data["debts"])
        if not owe.empty:
            ui.show_fig(charts.horizontal_totals(owe, "type", "balance", "Debts by type", ui.ORANGE))

    st.markdown("#### Net-worth history")
    hist = networth.history(data["net_worth_log"])
    c = st.columns([3, 1])
    c[0].text_input("Note for this snapshot (optional)", key="snap_note", placeholder="e.g. after bonus")
    c[1].button("📸 Record snapshot", on_click=_snapshot, type="primary", width="stretch",
                help="Saves today's totals. Recording again today replaces today's entry.")
    if len(hist) >= 2:
        ui.show_fig(charts.net_worth_trend(hist))
        change = hist["net_worth"].iloc[-1] - hist["net_worth"].iloc[0]
        st.caption(ui.md(f"Change since {hist['date'].iloc[0]:%b %d, %Y}: **{ui.fmt0(change)}**."))
    with st.expander("Edit history"):
        ui.edit_records("net_worth_log", {
            "date": ui.date_col("Date", required=True),
            "assets": ui.money_col("Assets", min_value=0.0),
            "liabilities": ui.money_col("Debts", min_value=0.0),
            "note": st.column_config.TextColumn("Note"),
        })
    ui.explain("Why track net worth?", """
Net worth is the simplest scorecard of financial progress: if it rises month after month, you are moving forward,
even when a single month's spending looks messy. Update balances about once a month (statement day is easy), then
press **Record snapshot**. Home and car values are your own estimates.

Tick **Emergency fund** on the cash accounts you would use in an emergency; the Dashboard divides that cash by your
essential monthly spending to show how many months it would last.
""")
