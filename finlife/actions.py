"""Financial Action Center: turns your numbers into a short, prioritized to-do list.

Every action comes from a visible rule (no AI). Each one says why it matters, what to do next and
which rule produced it. Rule-based actions can be snoozed; dated items are completed where they live.
"""

from __future__ import annotations

from datetime import date, timedelta

from finlife.data import planning
from finlife.data import transactions as tx

PRIORITY_BASE = {"High": 300, "Medium": 200, "Low": 100}


def _action(key, priority, icon, title, why, how, rule, page, *, urgency=0.0, impact=0.0, kind="rule",
            section=None, index=None):
    score = PRIORITY_BASE[priority] + urgency + min(impact / 100.0, 60.0)
    return {"key": key, "priority": priority, "icon": icon, "title": title, "why": why, "how": how, "rule": rule,
            "page": page, "score": round(score, 2), "kind": kind, "section": section, "index": index}


def build_actions(data: dict, m: dict, today: date, fmt) -> list[dict]:
    """All open actions, highest priority first. `m` is finlife.metrics.compute(data, today)."""
    acts: list[dict] = []

    # 1. Dated items: overdue, or due within 7 days and needing you (autopay bills and plain
    #    subscription renewals are left to the "Coming up" list).
    for u in m["upcoming"]:
        if u["section"] in ("bills-future", "tasks") or u["days"] > 7:
            continue
        item = data[u["section"]][u["index"]]
        amount = f" ({fmt(u['amount'])})" if u.get("amount") else ""
        if u["section"] == "subscriptions" and item.get("decision") != "Review":
            continue
        if u["days"] < 0:
            pr, when, urg = "High", f"{-u['days']} day(s) overdue", 60
        else:
            if u["section"] == "bills" and item.get("autopay"):
                continue
            pr = "High" if u["section"] in ("bills", "debts") else "Medium"
            when, urg = ("due today" if u["days"] == 0 else f"due in {u['days']} day(s)"), 30
        verb = "Review before it renews" if u["section"] == "subscriptions" else "Pay or review it"
        acts.append(_action(f"due:{u['section']}:{u['index']}:{u['date']}", pr, u["icon"],
                            f"{u['type']}: {u['title']}{amount}, {when}",
                            "Late payments can bring fees, interest and credit-score damage; renewals are the best "
                            "moment to compare prices or cancel.",
                            f"{verb}, then press Done. Recurring items move to their next date.",
                            "Shown for open items that are overdue, or due within 7 days and not on autopay.",
                            "actions", urgency=urg, impact=u.get("amount") or 0, kind="due",
                            section=u["section"], index=u["index"]))

    # 2. Your own tasks.
    for i, t in enumerate(data.get("tasks", [])):
        name = str(t.get("task") or "").strip()
        if not name or t.get("done"):
            continue
        pr = t.get("priority") if t.get("priority") in PRIORITY_BASE else "Medium"
        due = planning.parse_date(t.get("due_date"))
        urg, when = 0, ""
        if due:
            days = (due - today).days
            when = f" (overdue {-days} day(s))" if days < 0 else f" (due in {days} day(s))"
            urg = 60 if days < 0 else 30 if days <= 7 else 0
            if days < 0 and pr == "Low":
                pr = "Medium"
        acts.append(_action(f"task:{i}", pr, "📝", f"{name}{when}", t.get("notes") or "A task you added.",
                            "Do it, then press Done.", "Your task, with the priority you chose (overdue Low → Medium).",
                            "actions", urgency=urg, kind="task", section="tasks", index=i))

    # 3. Cash flow.
    lf = m["last_full"]
    if lf and lf["surplus"] < 0:
        acts.append(_action(f"cashflow:{lf['month']}", "High", "🔻",
                            f"You spent {fmt(-lf['surplus'])} more than you earned in {lf['month']}",
                            "Spending more than income drains savings or adds debt.",
                            "Open Budget and pick one or two categories to cut next month.",
                            "Shown when the last complete month's income minus spending is below zero.", "budget",
                            urgency=20, impact=-lf["surplus"]))
    if m["savings_rate"] is not None and 0 <= m["savings_rate"] < 0.10:
        acts.append(_action("savings-rate", "Medium", "🐷",
                            f"Average savings rate is {m['savings_rate']:.0%}",
                            "Keeping at least 10–20% of income builds an emergency fund and long-term savings.",
                            "Set a monthly transfer to savings right after payday.",
                            "Shown when (income − spending) ÷ income over complete months is below 10%.", "budget"))

    # 4. Emergency fund.
    months, target = m["emergency_months"], m["emergency_target_months"]
    if months is not None and months < target:
        gap = (target - months) * m["essentials"]
        pr = "High" if months < 1 else "Medium"
        acts.append(_action("emergency", pr, "🛟",
                            f"Emergency fund covers {months:.1f} of {target:g} months of essentials",
                            f"Essential spending is about {fmt(m['essentials'])}/month ({m['essentials_basis']}). "
                            "A cash cushion keeps a job loss or repair from becoming debt.",
                            f"Add about {fmt(gap)} to accounts marked as emergency fund. Use the Emergency fund "
                            "calculator to plan it.",
                            "Shown when emergency-fund accounts ÷ essential monthly spending is below your target "
                            "(below 1 month = High).", "calculators", impact=gap))
    elif months is None and m["essentials"] > 0:
        acts.append(_action("emergency-none", "Medium", "🛟", "Mark your emergency savings account",
                            "The app can't tell which account is your emergency fund.",
                            "Open Accounts and tick 'Emergency fund' on that account.",
                            "Shown when no account is marked as emergency fund.", "accounts"))

    # 5. High-interest debt.
    for d in m["high_apr_debts"]:
        acts.append(_action(f"debt:{d['name']}", "High" if d["apr"] >= 15 else "Medium", "💳",
                            f"Pay down {d['name']} ({d['apr']:.1f}% APR, {fmt(d['balance'])})",
                            f"It costs about {fmt(d['monthly_interest'])} in interest each month. Paying it off is a "
                            f"guaranteed {d['apr']:.1f}% return.",
                            "Put any extra money here first (Avalanche). Compare plans in the Debt payoff calculator.",
                            "Shown for debts with an APR of 10% or more (15%+ = High).", "calculators",
                            impact=d["monthly_interest"] * 12))

    # 6. Budgets this month.
    over = m["budget_current"]
    over = over[(over["budget"] > 0) & (over["actual"] > over["budget"])] if not over.empty else over
    for _, b in over.iterrows():
        acts.append(_action(f"budget:{m['current_month']}:{b['category']}", "Medium", "⚠️",
                            f"{b['category']} is {fmt(b['actual'] - b['budget'])} over budget this month",
                            f"Spent {fmt(b['actual'])} of {fmt(b['budget'])}.",
                            "Slow down in this category for the rest of the month, or raise the budget if it was "
                            "unrealistic.", "Shown when a category's spending this month is above its budget.",
                            "budget", impact=b["actual"] - b["budget"]))

    # 7. Goals.
    for g in m["goals"]:
        if g["status"] == "Behind":
            acts.append(_action(f"goal:{g['name']}", "Medium", "🎯",
                                f"Goal '{g['name']}' is behind: needs {fmt(g['required'])}/month, plan is "
                                f"{fmt(g['planned'])}",
                                "At the current contribution the goal will miss its deadline.",
                                "Raise the monthly contribution or move the deadline in Budget & Goals.",
                                "Shown when the planned monthly contribution is below remaining ÷ months left.",
                                "budget", impact=(g["required"] or 0) - g["planned"]))
        elif g["status"] == "Deadline passed":
            acts.append(_action(f"goal-late:{g['name']}", "Low", "⏰", f"Goal '{g['name']}' passed its deadline",
                                "The deadline is in the past but the goal is not reached.",
                                "Set a new deadline or close the goal.", "Shown when a goal's deadline has passed.",
                                "budget"))

    # 8. Subscriptions.
    for i, s in enumerate(data.get("subscriptions", [])):
        if s.get("cancelled") or not str(s.get("name") or "").strip():
            continue
        if s.get("decision") == "Cancel":
            acts.append(_action(f"sub-cancel:{s['name']}", "Medium", "✂️", f"Cancel {s['name']}",
                                "You marked it to cancel, and it still renews.",
                                "Cancel with the provider, then tick Cancelled in Subscriptions.",
                                "Shown for subscriptions marked Cancel but not cancelled.", "actions",
                                impact=(planning.to_float(s.get("amount")) or 0) * 12))

    # 9. Data clean-up.
    df = data["transactions"]
    if not df.empty:
        flags = tx.flag_table(df)
        live = flags.merge(df[["id", "exclude"]], on="id")
        live = live[(live["flags"] != "") & ~live["exclude"]]
        if not live.empty:
            acts.append(_action("clean:flags", "Low", "🚩", f"Review {len(live)} flagged transaction(s)",
                                "Possible duplicates or transfers can make spending look higher than it is.",
                                "Open Transactions → Needs review and use the one-click fixes.",
                                "Shown when duplicate or transfer flags are not resolved.", "transactions"))
        uncategorized = tx.counted(df)
        uncategorized = uncategorized[uncategorized["category"].isin(["", "Uncategorized"])]
        if not uncategorized.empty:
            acts.append(_action("clean:uncat", "Low", "🏷️", f"Categorize {len(uncategorized)} transaction(s)",
                                "Uncategorized spending hides where money goes.",
                                "Pick a category in Transactions, or add a keyword rule.",
                                "Shown when counted transactions have no category.", "transactions"))
    log_dates = [planning.parse_date(e.get("date")) for e in data.get("net_worth_log", [])]
    log_dates = [d for d in log_dates if d]
    if data.get("accounts") and (not log_dates or (today - max(log_dates)).days > 35):
        acts.append(_action("networth-snapshot", "Low", "📸", "Record this month's net worth",
                            "A monthly snapshot shows whether you are moving forward.",
                            "Update balances in Accounts, then press 'Record snapshot'.",
                            "Shown when the last net-worth snapshot is more than 35 days old.", "accounts"))

    dismissed = data["settings"].get("dismissed", {})
    out = []
    for a in acts:
        until = planning.parse_date(dismissed.get(a["key"]))
        if a["kind"] == "rule" and until and until > today:
            continue
        out.append(a)
    return sorted(out, key=lambda a: -a["score"])


def snooze(data: dict, key: str, today: date, days: int = 30) -> None:
    data["settings"].setdefault("dismissed", {})[key] = (today + timedelta(days=days)).isoformat()


def checkup_ladder(m: dict) -> list[dict]:
    """The order to fix things in (idea from stocks-retire-faqs' money checkup). Each step: done, current or todo."""
    lf = m["last_full"]
    months = m["emergency_months"] or 0.0
    behind = [g for g in m["goals"] if g["status"] in ("Behind", "Deadline passed")]
    steps = [
        ("Bills and debt payments are current", not m["overdue"], "Nothing is overdue."),
        ("You spend less than you earn", bool(lf) and lf["surplus"] >= 0, "Last complete month had a surplus."),
        ("Starter emergency fund (1 month of essentials)", months >= 1, "Covers a surprise repair or bill."),
        ("No debt at 10%+ APR", not m["high_apr_debts"], "High-interest debt costs more than most investments earn."),
        (f"Full emergency fund ({m['emergency_target_months']:g} months)", months >= m["emergency_target_months"],
         "Protects against job loss."),
        ("Savings goals on track", not behind, "Every goal's plan meets its deadline."),
    ]
    out, current_found = [], False
    for title, done, why in steps:
        status = "done" if done else ("current" if not current_found else "todo")
        current_found = current_found or not done
        out.append({"title": title, "status": status, "why": why})
    return out
