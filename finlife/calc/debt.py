"""Debt payoff: Avalanche (highest APR first) vs Snowball (smallest balance first).

Ported from finz-admin-pilot and fixed: debts are tracked by position, not by name, so two debts
with the same name are no longer merged (bug found in the audit, see docs/APP_INVENTORY.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .common import MAX_MONTHS, InputError, check_number, loan_monthly_rate

STRATEGIES = ("Avalanche", "Snowball")


@dataclass
class Debt:
    name: str
    balance: float
    apr: float
    min_payment: float


@dataclass
class PayoffResult:
    strategy: str
    paid_off: bool
    months: int
    total_interest: float
    total_paid: float
    payoff_month: dict = field(default_factory=dict)   # display name -> month (None if never)
    history: list = field(default_factory=list)       # rows of {Month, Debt, Balance}
    warnings: list = field(default_factory=list)


def unique_names(names: list[str]) -> list[str]:
    """'Card', 'Card' -> 'Card', 'Card (2)' so every debt has its own label in charts and tables."""
    seen: dict[str, int] = {}
    out = []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return out


def clean_debts(raw: list[dict]) -> tuple[list[Debt], list[str]]:
    """Turn editor rows into Debt objects, skipping blank, paid-off or invalid rows (with a message)."""
    debts: list[Debt] = []
    problems: list[str] = []
    for i, row in enumerate(raw, start=1):
        name = str(row.get("name") or "").strip() or f"Debt {i}"
        if row.get("balance") in (None, "") and not str(row.get("name") or "").strip():
            continue
        try:
            balance = check_number(f"{name} balance", row.get("balance"), 0)
            apr = check_number(f"{name} APR", row.get("apr"), 0)
            min_payment = check_number(f"{name} minimum payment", row.get("min_payment") or 0, 0)
        except InputError as exc:
            problems.append(str(exc))
            continue
        if balance == 0:
            continue
        if apr > 100:
            problems.append(f"{name}: APR above 100% looks like a typo, so it was skipped.")
            continue
        debts.append(Debt(name, balance, apr, min_payment))
    return debts, problems


def payoff_plan(debts: list[Debt], monthly_budget: float, strategy: str = "Avalanche") -> PayoffResult:
    """Simulate paying several debts with one monthly budget.

    Each month: interest accrues, every debt gets its minimum (capped at its balance), and the rest goes
    to the target debt (highest APR for Avalanche, smallest balance for Snowball). Money freed by a
    paid-off debt rolls into the next target. Stops after 50 years and reports it.
    """
    if strategy not in STRATEGIES:
        raise InputError(f"Strategy must be one of {', '.join(STRATEGIES)}.")
    if not debts:
        raise InputError("Add at least one debt with a balance above zero.")
    budget = check_number("Monthly payment budget", monthly_budget, 0, allow_equal=False)
    minimums = sum(d.min_payment for d in debts)
    if budget + 1e-9 < minimums:
        raise InputError(f"Monthly budget ({budget:,.2f}) is below the total of minimum payments ({minimums:,.2f}).")

    labels = unique_names([d.name for d in debts])
    warnings: list[str] = []
    for label, d in zip(labels, debts):
        first_interest = d.balance * loan_monthly_rate(d.apr)
        if d.min_payment <= first_interest:
            warnings.append(f"{label}: the minimum payment ({d.min_payment:,.2f}) does not cover the first month's "
                            f"interest ({first_interest:,.2f}). On its own this balance would never shrink.")
    if budget <= sum(d.balance * loan_monthly_rate(d.apr) for d in debts):
        warnings.append("The whole budget does not cover the first month's interest, so total debt grows.")

    n = len(debts)
    balances = [d.balance for d in debts]
    rates = [loan_monthly_rate(d.apr) for d in debts]
    if strategy == "Avalanche":
        order_key = lambda i: (-debts[i].apr, balances[i], i)  # noqa: E731
    else:
        order_key = lambda i: (balances[i], -debts[i].apr, i)  # noqa: E731
    payoff: list[int | None] = [None] * n
    history = [{"Month": 0, "Debt": labels[i], "Balance": balances[i]} for i in range(n)]
    total_interest = total_paid = 0.0
    month = 0
    while any(b > 0.005 for b in balances) and month < MAX_MONTHS:
        month += 1
        for i in range(n):
            if balances[i] > 0:
                interest = balances[i] * rates[i]
                balances[i] += interest
                total_interest += interest
        remaining = budget
        for i in range(n):
            if balances[i] > 0:
                pay = min(debts[i].min_payment, balances[i], remaining)
                balances[i] -= pay
                remaining -= pay
                total_paid += pay
        for i in sorted([i for i in range(n) if balances[i] > 0.005], key=order_key):
            if remaining <= 0:
                break
            pay = min(remaining, balances[i])
            balances[i] -= pay
            remaining -= pay
            total_paid += pay
        for i in range(n):
            if balances[i] < 0.005:
                balances[i] = 0.0
                if payoff[i] is None:
                    payoff[i] = month
            history.append({"Month": month, "Debt": labels[i], "Balance": balances[i]})
    paid_off = all(b == 0 for b in balances)
    if not paid_off:
        warnings.append(f"Not paid off within {MAX_MONTHS // 12} years at this budget.")
    return PayoffResult(strategy, paid_off, month, total_interest, total_paid,
                        dict(zip(labels, payoff)), history, warnings)
