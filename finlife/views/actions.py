"""Financial Action Center: a prioritized to-do list built from your numbers, plus your own tasks and renewals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finlife import actions as act
from finlife import metrics
from finlife.data import planning, storage
from finlife.ui import common as ui

ss = st.session_state
PAGE_LABELS = {"budget": "Budget & Goals", "calculators": "Calculator Center", "transactions": "Income & Expenses",
               "accounts": "Accounts & Net Worth"}


def _done(section: str, index: int) -> None:
    try:
        msg = planning.complete_item(ss.data, section, index)
    except (IndexError, KeyError):
        ss.flash_error = "That item changed before it could be completed. Try again."
        return
    ui.commit(msg)


def _snooze(key: str) -> None:
    act.snooze(ss.data, key, ui.today())
    ui.commit("Snoozed for 30 days. It comes back if the rule still applies.")


def _ladder(m: dict) -> None:
    steps = act.checkup_ladder(m)
    st.markdown("#### 🪜 Money checkup: what to fix first")
    cols = st.columns(3) + st.columns(3)
    for col, (i, s) in zip(cols, enumerate(steps, start=1)):
        icon = {"done": "✅", "current": "👉", "todo": "⬜"}[s["status"]]
        with col.container(border=True):
            st.markdown(f"{icon} **{i}. {s['title']}**")
            st.caption(s["why"])
    current = next((s for s in steps if s["status"] == "current"), None)
    if current:
        st.caption(f"Your next step is **{current['title'].lower()}**. Steps build on each other: a later one "
                   "matters less until the earlier ones are done.")
    else:
        st.success("All checkup steps are done. Next: invest for long-term goals (see the Retirement calculator).")


def render() -> None:
    data, today = ui.data(), ui.today()
    st.title("✅ Financial Action Center")
    st.caption("Everything that needs your attention, most important first. Each item says why it matters, what to "
               "do, and the rule that raised it.")
    ui.sample_banner()
    m = metrics.compute(data, today)
    _ladder(m)

    items = act.build_actions(data, m, today, ui.fmt0)
    c = st.columns([2, 1, 1, 1])
    c[0].markdown("#### 🔥 Prioritized actions")
    for col, p in zip(c[1:], storage.PRIORITIES):
        col.metric(p, sum(a["priority"] == p for a in items))
    show = st.segmented_control("Show", ["All", "High", "Medium", "Low"], default="All", key="act_filter") or "All"
    shown = [a for a in items if show == "All" or a["priority"] == show]
    if not shown:
        st.success("Nothing here. Nice work!", icon="🎉")
    for a in shown:
        with st.container(border=True):
            left, right = st.columns([5, 1.4])
            left.markdown(f'<span class="fl-pill fl-{a["priority"]}">{a["priority"]}</span> {a["icon"]} '
                          f'**{ui.md(a["title"])}**', unsafe_allow_html=True)
            left.markdown(ui.md(f"{a['why']}  \n**Next step:** {a['how']}"))
            left.caption(f"Rule: {a['rule']}")
            if a["kind"] in ("due", "task"):
                right.button("✔️ Done", key=f"done_{a['key']}_{ss.ver}", on_click=_done,
                             args=(a["section"], a["index"]), width="stretch")
            else:
                right.button("💤 Snooze 30 days", key=f"snooze_{a['key']}_{ss.ver}", on_click=_snooze,
                             args=(a["key"],), width="stretch")
            if a["page"] in PAGE_LABELS and a["page"] in ui.PAGES:
                with right:
                    ui.page_link(a["page"], PAGE_LABELS[a["page"]], icon="➡️")
    snoozed = {k: v for k, v in data["settings"].get("dismissed", {}).items()
               if (planning.parse_date(v) or today) > today}
    if snoozed and st.button(f"Bring back {len(snoozed)} snoozed item(s)"):
        data["settings"]["dismissed"] = {}
        ui.commit("Snoozed items are back.")
        st.rerun()

    st.markdown("#### 📅 Coming up in the next 30 days")
    upcoming = [u for u in m["upcoming"]]
    if not upcoming:
        st.caption("Nothing dated in the next 30 days.")
    else:
        frame = pd.DataFrame([{"When": u["date"], "In": ("overdue " if u["days"] < 0 else "") + f"{abs(u['days'])} d",
                               "What": f"{u['icon']} {u['type']}", "Item": u["title"], "Amount": u["amount"]}
                              for u in upcoming])
        st.dataframe(frame, hide_index=True, width="stretch",
                     column_config={"When": ui.date_col("When"), "Amount": ui.money_col("Amount")})
        st.caption(ui.md(f"Total amounts due: **{ui.fmt0(frame['Amount'].fillna(0).sum())}**."))

    st.markdown("#### 🗂️ Your lists")
    t1, t2, t3, t4 = st.tabs(["📝 Tasks", "🔁 Subscriptions", "🛡️ Insurance", "📁 Documents"])
    with t1:
        ui.edit_records("tasks", {
            "task": st.column_config.TextColumn("Task", required=True),
            "priority": st.column_config.SelectboxColumn("Priority", options=storage.PRIORITIES, default="Medium"),
            "due_date": ui.date_col("Due"),
            "done": st.column_config.CheckboxColumn("Done"),
            "notes": st.column_config.TextColumn("Notes"),
        })
    with t2:
        ui.edit_records("subscriptions", {
            "name": st.column_config.TextColumn("Subscription", required=True),
            "amount": ui.money_col("Amount", min_value=0.0),
            "billing": st.column_config.SelectboxColumn("Billing", options=storage.BILLING, default="Monthly"),
            "renewal_date": ui.date_col("Renews"),
            "decision": st.column_config.SelectboxColumn("Decision", options=storage.SUB_DECISIONS, default="Keep"),
            "cancelled": st.column_config.CheckboxColumn("Cancelled"),
        })
        st.caption("Mark a subscription **Review** or **Cancel** and the Action Center reminds you before it renews.")
    with t3:
        ui.edit_records("insurance", {
            "policy": st.column_config.TextColumn("Policy", required=True),
            "provider": st.column_config.TextColumn("Provider"),
            "premium": ui.money_col("Premium per term", min_value=0.0),
            "term_months": st.column_config.NumberColumn("Term (months)", min_value=1, max_value=60, format="%d"),
            "renewal_date": ui.date_col("Renews"),
            "notes": st.column_config.TextColumn("Notes"),
        })
        st.caption("Pressing Done on a renewal moves it forward by the policy term.")
    with t4:
        ui.edit_records("documents", {
            "document": st.column_config.TextColumn("Document", required=True),
            "category": st.column_config.TextColumn("Category"),
            "due_date": ui.date_col("Due"),
            "done": st.column_config.CheckboxColumn("Done"),
            "notes": st.column_config.TextColumn("Notes"),
        })

    ui.explain("How priorities are set", """
- **High**: overdue items, bills or debt payments due within 7 days that are not on autopay, debt at 15%+ APR,
  spending more than you earn, an emergency fund under one month, and your own High tasks.
- **Medium**: emergency fund below your target, debt at 10–15% APR, categories over budget, goals behind schedule,
  subscriptions you marked to cancel, and your Medium tasks.
- **Low**: data clean-up (duplicates, uncategorized rows), a stale net-worth snapshot, and your Low tasks.

Within a level, items that are overdue, due sooner or involve more money come first. **Done** completes an item
(recurring bills, debt payments and renewals move to their next date). **Snooze** hides a rule-based item for 30 days.
""")
