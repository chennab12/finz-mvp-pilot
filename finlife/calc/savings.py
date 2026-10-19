"""Savings goals, compound growth (with fees and inflation), emergency fund and subscription costs.

Merged from finz-admin-pilot (validation), finance-faqs (fee + inflation view) and stocks-faqs
(fees applied multiplicatively). Returns are effective annual rates; see common.py.
"""

from __future__ import annotations

from .common import (FREQUENCY_PER_YEAR, MAX_MONTHS, InputError, check_number,
                     growth_monthly_rate)


def required_monthly_saving(target: float, current: float, annual_return_pct: float, months: int) -> float:
    """Monthly deposit (end of month) needed to reach `target` in `months`."""
    target = check_number("Goal amount", target, 0, allow_equal=False)
    current = check_number("Current savings", current, 0)
    rate = check_number("Annual return", annual_return_pct, 0, maximum=50)
    months = int(check_number("Months to goal", months, 1, maximum=MAX_MONTHS))
    r = growth_monthly_rate(rate)
    gap = target - current * (1 + r) ** months
    if gap <= 0:
        return 0.0
    if r == 0:
        return gap / months
    return gap * r / ((1 + r) ** months - 1)


def months_to_goal(target: float, current: float, monthly_deposit: float, annual_return_pct: float) -> int | None:
    """Months until `target` is reached, or None if not reached within 50 years."""
    target = check_number("Goal amount", target, 0, allow_equal=False)
    balance = check_number("Current savings", current, 0)
    deposit = check_number("Monthly deposit", monthly_deposit, 0)
    r = growth_monthly_rate(check_number("Annual return", annual_return_pct, 0, maximum=50))
    if balance >= target:
        return 0
    for month in range(1, MAX_MONTHS + 1):
        balance = balance * (1 + r) + deposit
        if balance >= target - 0.005:
            return month
    return None


def net_return_pct(gross_return_pct: float, annual_fee_pct: float) -> float:
    """Return after an annual fee charged on the balance: (1 + r)(1 − fee) − 1."""
    return ((1 + gross_return_pct / 100) * (1 - annual_fee_pct / 100) - 1) * 100


def compound_growth(initial: float, monthly_deposit: float, annual_return_pct: float, years: int,
                    annual_fee_pct: float = 0.0, inflation_pct: float = 0.0) -> list[dict]:
    """Year-end balances with end-of-month deposits.

    Columns: Year, Contributions, Balance (after fees), Growth (= Balance − Contributions),
    Without fees (same inputs, 0% fee) and Today's dollars (Balance ÷ (1 + inflation)^year).
    """
    balance = check_number("Starting amount", initial, 0)
    deposit = check_number("Monthly deposit", monthly_deposit, 0)
    rate = check_number("Annual return", annual_return_pct, -50, maximum=50)
    fee = check_number("Annual fee", annual_fee_pct, 0, maximum=10)
    inflation = check_number("Inflation", inflation_pct, 0, maximum=20)
    years = int(check_number("Years", years, 1, maximum=50))
    r_net = growth_monthly_rate(net_return_pct(rate, fee))
    r_gross = growth_monthly_rate(rate)
    no_fee = balance
    contributed = balance
    rows = [{"Year": 0, "Contributions": contributed, "Growth": 0.0, "Balance": balance,
             "Without fees": balance, "Today's dollars": balance}]
    for year in range(1, years + 1):
        for _ in range(12):
            balance = balance * (1 + r_net) + deposit
            no_fee = no_fee * (1 + r_gross) + deposit
            contributed += deposit
        rows.append({"Year": year, "Contributions": contributed, "Growth": balance - contributed, "Balance": balance,
                     "Without fees": no_fee, "Today's dollars": balance / (1 + inflation / 100) ** year})
    return rows


def emergency_fund(savings: float, monthly_essentials: float, target_months: float) -> dict:
    """Months of essential spending covered by emergency savings, and the gap to a target."""
    savings = check_number("Emergency savings", savings, 0)
    expenses = check_number("Monthly essential expenses", monthly_essentials, 0, allow_equal=False)
    target_months = check_number("Target months", target_months, 0, allow_equal=False, maximum=36)
    target_amount = expenses * target_months
    return {"months_covered": savings / expenses, "target_amount": target_amount,
            "gap": max(0.0, target_amount - savings), "surplus": max(0.0, savings - target_amount),
            "met": savings >= target_amount}


def subscription_costs(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Monthly and annual equivalents for each active (not cancelled) subscription."""
    out: list[dict] = []
    problems: list[str] = []
    for i, row in enumerate(rows, start=1):
        name = str(row.get("name") or "").strip()
        if not name and row.get("amount") in (None, ""):
            continue
        name = name or f"Subscription {i}"
        if row.get("cancelled") is True or row.get("active") is False:
            continue
        freq = row.get("billing") or "Monthly"
        if freq not in FREQUENCY_PER_YEAR:
            problems.append(f"{name}: unknown billing frequency '{freq}'.")
            continue
        try:
            amount = check_number(f"{name} amount", row.get("amount"), 0)
        except InputError as exc:
            problems.append(str(exc))
            continue
        annual = amount * FREQUENCY_PER_YEAR[freq]
        out.append({"Subscription": name, "Billing": freq, "Amount": amount, "Monthly": annual / 12, "Annual": annual})
    return out, problems
