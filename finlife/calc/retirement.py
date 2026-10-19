"""Retirement number (FI number) and how long savings last. Ported from stocks-retire-faqs with validation."""

from __future__ import annotations

from .common import InputError, check_number


def fi_number(yearly_spending: float, guaranteed_income: float = 0.0, withdrawal_rate_pct: float = 4.0) -> float:
    """Savings needed so that withdrawal_rate × savings covers spending not met by pensions/Social Security."""
    spending = check_number("Yearly spending", yearly_spending, 0)
    income = check_number("Guaranteed yearly income", guaranteed_income, 0)
    rate = check_number("Withdrawal rate", withdrawal_rate_pct, 0, allow_equal=False, maximum=20)
    return max(0.0, spending - income) / (rate / 100)


def money_lasts(balance: float, yearly_withdrawal: float, real_return_pct: float, max_years: int = 60) -> list[dict]:
    """Year-by-year balance when withdrawing a fixed inflation-adjusted amount at the start of each year.

    Uses a *real* return (after inflation), so every amount is in today's dollars. The list stops at
    the year the money runs out or at max_years.
    """
    balance = check_number("Starting savings", balance, 0)
    withdrawal = check_number("Yearly withdrawal", yearly_withdrawal, 0)
    rate = check_number("Real return", real_return_pct, -20, maximum=20) / 100
    max_years = int(check_number("Years to show", max_years, 1, maximum=100))
    rows = [{"Year": 0, "Balance": balance}]
    for year in range(1, max_years + 1):
        balance = (balance - withdrawal) * (1 + rate)
        if balance <= 0:
            rows.append({"Year": year, "Balance": 0.0})
            break
        rows.append({"Year": year, "Balance": balance})
    return rows


def run_out_year(rows: list[dict]) -> int | None:
    """The year in which the money runs out (from money_lasts rows), or None if it lasts the whole period."""
    if len(rows) > 1 and rows[-1]["Balance"] <= 0:
        return rows[-1]["Year"]
    return None


def check_retirement_inputs(current_age: int, retire_age: int) -> int:
    current = int(check_number("Current age", current_age, 18, maximum=100))
    retire = int(check_number("Retirement age", retire_age, 18, maximum=100))
    if retire <= current:
        raise InputError("Retirement age must be after your current age.")
    return retire - current
