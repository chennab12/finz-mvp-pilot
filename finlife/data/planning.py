"""Recurring bills, savings-goal status, cash-flow projection and reminders."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

import pandas as pd

from finlife.calc.common import FREQUENCY_PER_YEAR

BILL_FREQUENCIES = list(FREQUENCY_PER_YEAR)


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    if isinstance(value, date):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_occurrence(d: date, frequency: str) -> date:
    if frequency == "Weekly":
        return d + timedelta(days=7)
    if frequency == "Quarterly":
        return add_months(d, 3)
    if frequency == "Yearly":
        return add_months(d, 12)
    return add_months(d, 1)


def bill_occurrences(bills: list[dict], start: date, end: date) -> list[dict]:
    """Every due date of every active bill from `start` to `end` (inclusive).

    A bill's "next due" date may be in the past (not yet paid); it is listed
    once as overdue and then repeats from there.
    """
    out = []
    for bill in bills:
        if bill.get("active") is False:
            continue
        name = str(bill.get("name") or "").strip()
        amount = to_float(bill.get("amount"))
        due = parse_date(bill.get("next_due"))
        freq = bill.get("frequency") or "Monthly"
        if not name or amount is None or amount < 0 or due is None or freq not in FREQUENCY_PER_YEAR:
            continue
        guard = 0
        while due <= end and guard < 1000:
            if due >= start or (guard == 0 and due < start):
                out.append({"name": name, "amount": amount, "due": due, "category": bill.get("category") or "",
                            "overdue": due < start, "autopay": bool(bill.get("autopay"))})
            due = next_occurrence(due, freq)
            guard += 1
    return sorted(out, key=lambda r: r["due"])


def monthly_equivalent(bills: list[dict]) -> float:
    total = 0.0
    for bill in bills:
        if bill.get("active") is False:
            continue
        amount = to_float(bill.get("amount"))
        freq = bill.get("frequency") or "Monthly"
        if amount is not None and amount >= 0 and freq in FREQUENCY_PER_YEAR:
            total += amount * FREQUENCY_PER_YEAR[freq] / 12
    return total


def months_between(start: date, end: date) -> float:
    return (end - start).days / (365.25 / 12)


def goal_status(goal: dict, today: date) -> dict | None:
    """Progress, deadline indicator and the monthly amount needed (no investment growth assumed)."""
    name = str(goal.get("name") or "").strip()
    target = to_float(goal.get("target"))
    if not name or target is None or target <= 0:
        return None
    saved = max(0.0, to_float(goal.get("saved")) or 0.0)
    planned = max(0.0, to_float(goal.get("monthly_contribution")) or 0.0)
    deadline = parse_date(goal.get("deadline"))
    remaining = max(0.0, target - saved)
    progress = min(1.0, saved / target)
    result = {"name": name, "target": target, "saved": saved, "remaining": remaining, "progress": progress,
              "planned": planned, "deadline": deadline, "days_left": None, "required": None,
              "projected_date": None, "status": "", "icon": ""}
    if planned > 0 and remaining > 0:
        months_needed = -(-remaining // planned)  # ceiling
        result["projected_date"] = add_months(today, int(months_needed))
    if remaining == 0:
        result.update(status="Reached", icon="✅")
        return result
    if deadline is None:
        result.update(status="No deadline", icon="🗓️")
        return result
    result["days_left"] = (deadline - today).days
    if deadline <= today:
        result.update(status="Deadline passed", icon="⛔")
        return result
    months_left = max(months_between(today, deadline), 1 / 30)
    result["required"] = remaining / max(1.0, months_left) if months_left >= 1 else remaining
    if planned >= result["required"] - 0.005:
        result.update(status="On track", icon="🟢")
    elif planned > 0:
        result.update(status="Behind", icon="🟠")
    else:
        result.update(status="No contribution set", icon="⚪")
    return result


def cash_flow_projection(*, today: date, months: int, starting_balance: float, monthly_income: float,
                         monthly_variable_spending: float, bills: list[dict], goal_contributions: float) -> pd.DataFrame:
    """Project month-end balances for the next `months` calendar months.

    Month 1 is the calendar month after today. Income, variable spending and
    goal contributions are flat monthly assumptions; bills are placed in the
    month they fall due.
    """
    first = add_months(date(today.year, today.month, 1), 1)
    rows = []
    balance = starting_balance
    for i in range(months):
        start = add_months(first, i)
        end = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        due = [b for b in bill_occurrences(bills, start, end) if not b["overdue"]]
        bills_total = sum(b["amount"] for b in due)
        opening = balance
        balance = opening + monthly_income - monthly_variable_spending - bills_total - goal_contributions
        rows.append({"Month": start.strftime("%b %Y"), "Opening": opening, "Income": monthly_income,
                     "Variable spending": monthly_variable_spending, "Bills": bills_total,
                     "Goal savings": goal_contributions, "Closing": balance})
    return pd.DataFrame(rows).round(2)


# ---------------------------------------------------------------------------
# Dated items: what is due soon across bills, debts, insurance, subscriptions, documents and tasks
# ---------------------------------------------------------------------------

DATED_SECTIONS = {
    "debts": {"label": "Debt payment", "icon": "💳", "title": "name", "date": "next_due", "amount": "min_payment"},
    "insurance": {"label": "Insurance renewal", "icon": "🛡️", "title": "policy", "date": "renewal_date",
                  "amount": "premium"},
    "subscriptions": {"label": "Subscription renewal", "icon": "🔁", "title": "name", "date": "renewal_date",
                      "amount": "amount"},
    "documents": {"label": "Document", "icon": "📁", "title": "document", "date": "due_date", "amount": None},
    "tasks": {"label": "Task", "icon": "✅", "title": "task", "date": "due_date", "amount": None},
}


def is_complete(section: str, item: dict) -> bool:
    if section == "debts":
        return (to_float(item.get("balance")) or 0) <= 0
    if section == "subscriptions":
        return bool(item.get("cancelled"))
    return bool(item.get("done"))


def upcoming_items(data: dict, today: date, horizon_days: int) -> list[dict]:
    """Open dated items and bill due dates up to `horizon_days` ahead. Overdue items are included."""
    end = today + timedelta(days=horizon_days)
    out = []
    for section, meta in DATED_SECTIONS.items():
        for idx, item in enumerate(data.get(section, [])):
            if is_complete(section, item):
                continue
            when = parse_date(item.get(meta["date"]))
            title = str(item.get(meta["title"]) or "").strip()
            if when is None or not title or when > end:
                continue
            amount = to_float(item.get(meta["amount"])) if meta["amount"] else None
            out.append({"section": section, "index": idx, "icon": meta["icon"], "type": meta["label"],
                        "title": title, "date": when, "days": (when - today).days, "amount": amount,
                        "priority": item.get("priority") if section == "tasks" else None})
    bills = data.get("bills", [])
    for b in bill_occurrences(bills, today, end):
        idx = next((i for i, x in enumerate(bills) if str(x.get("name") or "").strip() == b["name"]), None)
        if idx is None:
            continue
        # Only the bill's current "next due" can be marked paid; later repeats are informational.
        current = parse_date(bills[idx].get("next_due")) == b["due"]
        out.append({"section": "bills" if current else "bills-future", "index": idx, "icon": "💵", "type": "Bill",
                    "title": b["name"], "date": b["due"], "days": (b["due"] - today).days, "amount": b["amount"],
                    "priority": None})
    return sorted(out, key=lambda r: r["date"])


def complete_item(data: dict, section: str, index: int) -> str:
    """Mark one item done. Recurring items (bills, debt payments, subscriptions) move to their next date."""
    item = data[section][index]
    if section == "bills":
        due = parse_date(item.get("next_due"))
        if due:
            item["next_due"] = next_occurrence(due, item.get("frequency") or "Monthly").isoformat()
        return f"Marked {item.get('name')} paid; next due {item.get('next_due')}."
    if section == "debts":
        due = parse_date(item.get("next_due"))
        if due:
            item["next_due"] = add_months(due, 1).isoformat()
        return f"Logged the {item.get('name')} payment; next payment {item.get('next_due')}."
    if section == "subscriptions":
        due = parse_date(item.get("renewal_date"))
        if due:
            item["renewal_date"] = next_occurrence(due, item.get("billing") or "Monthly").isoformat()
        return f"{item.get('name')} renewal noted; next renewal {item.get('renewal_date')}."
    if section == "insurance":
        due = parse_date(item.get("renewal_date"))
        if due:
            term = int(to_float(item.get("term_months")) or 12)
            item["renewal_date"] = add_months(due, max(1, term)).isoformat()
        return f"{item.get('policy')} renewal reviewed; next renewal {item.get('renewal_date')}."
    item["done"] = True
    return "Marked complete."
