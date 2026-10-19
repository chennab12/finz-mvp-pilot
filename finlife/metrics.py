"""Household numbers shared by the Dashboard and the Action Center. Pure Python, recomputed on demand."""

from __future__ import annotations

from datetime import date

import pandas as pd

from finlife.data import networth, planning
from finlife.data import transactions as tx

# Spending that must continue even in a tight month; used for the emergency-fund estimate.
ESSENTIAL_CATEGORIES = ["Housing", "Groceries", "Utilities", "Insurance", "Healthcare", "Transport",
                        "Education", "Debt payments"]
HIGH_APR = 10.0


def essential_monthly(df: pd.DataFrame, months: list[str], budgets: list[dict]) -> tuple[float, str]:
    """Average essential spending over complete months; falls back to the essential budgets."""
    if months:
        work = tx.counted(df)
        work = work[(work["group"] == "spending") & work["category"].isin(ESSENTIAL_CATEGORIES)
                    & work["month"].isin(months)]
        if not work.empty:
            return float(-work["amount"].sum() / len(months)), f"average of {len(months)} complete month(s)"
    total = 0.0
    for b in budgets:
        if b.get("category") in ESSENTIAL_CATEGORIES:
            total += planning.to_float(b.get("monthly_budget")) or 0.0
    return total, "your essential budgets"


def compute(data: dict, today: date) -> dict:
    df = data["transactions"]
    summary = tx.monthly_summary(df)
    full = [m for m in tx.full_months(df, today) if m in set(summary["month"])]
    s_full = summary[summary["month"].isin(full)]
    last_full = s_full.iloc[-1].to_dict() if not s_full.empty else None
    avg_income = float(s_full["income"].mean()) if not s_full.empty else 0.0
    avg_spending = float(s_full["spending"].mean()) if not s_full.empty else 0.0
    savings_rate = (avg_income - avg_spending) / avg_income if avg_income > 0 else None

    essentials, essentials_basis = essential_monthly(df, full, data.get("budgets", []))
    nw = networth.totals(data.get("accounts", []), data.get("debts", []))
    target_months = float(data["settings"].get("emergency_months") or 6)
    has_emergency = any(a.get("emergency_fund") for a in data.get("accounts", []))
    emergency_months = nw["emergency_savings"] / essentials if essentials > 0 and has_emergency else None

    debts = []
    for d in data.get("debts", []):
        bal, apr = planning.to_float(d.get("balance")), planning.to_float(d.get("apr"))
        if bal and bal > 0 and str(d.get("name") or "").strip():
            debts.append({"name": d["name"], "balance": bal, "apr": apr or 0.0,
                          "monthly_interest": bal * (apr or 0.0) / 1200})
    high_apr = sorted([d for d in debts if d["apr"] >= HIGH_APR], key=lambda d: -d["apr"])

    goals = [g for g in (planning.goal_status(g, today) for g in data.get("goals", [])) if g]
    upcoming = planning.upcoming_items(data, today, 30)
    current_month = pd.Period(today, "M").strftime("%Y-%m")
    return {
        "summary": summary, "full_months": full, "last_full": last_full,
        "avg_income": avg_income, "avg_spending": avg_spending, "savings_rate": savings_rate,
        "essentials": essentials, "essentials_basis": essentials_basis,
        "emergency_savings": nw["emergency_savings"], "emergency_months": emergency_months,
        "emergency_target_months": target_months,
        "assets": nw["assets"], "liabilities": nw["liabilities"], "net_worth": nw["net_worth"],
        "debts": debts, "high_apr_debts": high_apr,
        "goals": goals, "upcoming": upcoming,
        "overdue": [u for u in upcoming if u["days"] < 0 and u["section"] != "bills-future"],
        "current_month": current_month,
        "budget_current": tx.budget_vs_actual(df, data.get("budgets", []), current_month),
    }
