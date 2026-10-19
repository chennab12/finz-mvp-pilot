"""Rule-based insights. Plain Python if-statements over your own numbers; no AI.

Each insight carries the rule that produced it so the app can show it.
"""

from __future__ import annotations

import pandas as pd

from finlife.data import transactions as tx

# Large but expected payments that should not be reported as "large purchases".
FIXED_COST_CATEGORIES = ["Housing", "Education", "Debt payments"]


def build_insights(df: pd.DataFrame, month: str, budgets: list[dict], fmt, flags: pd.DataFrame | None = None,
                   upcoming_bills_total: float | None = None) -> list[dict]:
    """Return a list of {icon, title, detail, rule, level} dicts for one month."""
    out: list[dict] = []
    if df.empty or not month:
        return out
    summary = tx.monthly_summary(df).set_index("month")
    if month not in summary.index:
        return out
    row = summary.loc[month]
    income, spending, surplus = float(row["income"]), float(row["spending"]), float(row["surplus"])

    if surplus < 0:
        out.append({"icon": "🔻", "level": "warn", "title": f"Spending exceeded income by {fmt(-surplus)}",
                    "detail": f"Income {fmt(income)} vs spending {fmt(spending)} in {month}.",
                    "rule": "Shown when income minus spending is below zero."})
    elif income > 0:
        rate = surplus / income * 100
        out.append({"icon": "💪" if rate >= 20 else "🙂", "level": "good" if rate >= 20 else "info",
                    "title": f"You kept {rate:.0f}% of income ({fmt(surplus)})",
                    "detail": "Savings rate = (income − spending) ÷ income.",
                    "rule": "Shown when income is above zero and surplus is not negative; 20%+ is marked strong."})

    for _, b in tx.budget_vs_actual(df, budgets, month).iterrows():
        if b["budget"] > 0 and b["actual"] > b["budget"]:
            over = b["actual"] - b["budget"]
            out.append({"icon": "⚠️", "level": "warn", "title": f"{b['category']} is {fmt(over)} over budget",
                        "detail": f"Spent {fmt(b['actual'])} of a {fmt(b['budget'])} budget ({b['used_pct']:.0f}%).",
                        "rule": "Shown when a category's net spending is above its monthly budget."})

    cats = tx.category_spending(df, month)
    positive = cats[cats["spent"] > 0]
    if spending > 0 and not positive.empty:
        top = positive.iloc[0]
        share = top["spent"] / spending * 100
        if share >= 30:
            out.append({"icon": "🥧", "level": "info", "title": f"{top['category']} is {share:.0f}% of spending",
                        "detail": f"{fmt(top['spent'])} of {fmt(spending)} this month.",
                        "rule": "Shown when one category is 30% or more of the month's spending."})

    months = list(summary.index)
    pos = months.index(month)
    if pos > 0:
        prev = tx.category_spending(df, months[pos - 1]).set_index("category")["spent"]
        for _, c in positive.iterrows():
            before = float(prev.get(c["category"], 0.0))
            change = c["spent"] - before
            if before > 0 and change >= 50 and change / before >= 0.25:
                out.append({"icon": "📈", "level": "info",
                            "title": f"{c['category']} up {change / before * 100:.0f}% vs {months[pos - 1]}",
                            "detail": f"{fmt(before)} → {fmt(c['spent'])}.",
                            "rule": "Shown when a category rose by at least 25% and at least 50 vs the previous month."})

    subs = cats.set_index("category")["spent"].get("Subscriptions") if not cats.empty else None
    if subs and subs > 0:
        out.append({"icon": "🔁", "level": "info", "title": f"Subscriptions cost {fmt(subs)} this month",
                    "detail": f"About {fmt(subs * 12)} a year if every month looks like this one.",
                    "rule": "Shown when the Subscriptions category has spending; annual = month × 12."})

    month_rows = tx.counted(df)
    month_rows = month_rows[(month_rows["month"] == month) & (month_rows["group"] == "spending") & (month_rows["amount"] < 0)]
    if len(month_rows) >= 5:
        median = float((-month_rows["amount"]).median())
        transfer_like = set(flags.loc[flags["flags"].str.contains("transfer"), "id"]) if flags is not None else set()
        big = month_rows[(-month_rows["amount"] >= max(200.0, 3 * median)) & ~month_rows["category"].isin(FIXED_COST_CATEGORIES)
                         & ~month_rows["id"].isin(transfer_like)]
        if not big.empty:
            largest = big.loc[big["amount"].idxmin()]
            out.append({"icon": "🔍", "level": "info", "title": f"Large purchase: {largest['description']}",
                        "detail": f"{fmt(-largest['amount'])} on {largest['date']}, typical purchase {fmt(median)}.",
                        "rule": "Shown when a purchase is at least 3× the month's median purchase and at least 200 (housing, tuition, debt payments and transfer-like rows excluded)."})

    uncategorized = month_rows[month_rows["category"].isin(["", "Uncategorized"])]
    if not uncategorized.empty:
        out.append({"icon": "🏷️", "level": "info", "title": f"{len(uncategorized)} uncategorized purchase(s)",
                    "detail": "Fix them in Transactions or add a keyword rule.",
                    "rule": "Shown when spending rows have no category."})

    if flags is not None and not flags.empty:
        n_dup = int(flags["flags"].str.contains("duplicate").sum())
        n_tr = int(flags["flags"].str.contains("transfer").sum())
        if n_dup:
            out.append({"icon": "👯", "level": "warn", "title": f"{n_dup} possible duplicate(s) to review",
                        "detail": "Tick Exclude on the copy in Transactions if it is a real duplicate.",
                        "rule": "Same date, amount and description as an earlier row."})
        if n_tr:
            out.append({"icon": "🔄", "level": "warn", "title": f"{n_tr} row(s) look like transfers",
                        "detail": "They count as spending/income until you set them to Transfer or Credit card payment.",
                        "rule": "Matching opposite amounts across accounts within 3 days, or transfer keywords."})

    if upcoming_bills_total:
        out.append({"icon": "📅", "level": "info", "title": f"{fmt(upcoming_bills_total)} of bills due in the next 14 days",
                    "detail": "From your recurring bills list.",
                    "rule": "Sum of recurring bills with a due date in the next 14 days, overdue included."})
    return out
