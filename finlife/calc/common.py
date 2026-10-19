"""Shared validation and constants for every calculator.

Conventions used across FinLife 360 (chosen in docs/FEATURE_COMPARISON.md):
* Loans and debts: the APR is divided by 12 and charged monthly (how lenders quote payments).
* Savings and investments: the annual return is an *effective* annual rate, converted to the
  equivalent monthly rate (1 + r) ** (1/12) - 1, with deposits at the end of each month.
* Every month-by-month simulation stops after MAX_MONTHS (50 years) instead of looping forever.
"""

from __future__ import annotations

import math

MAX_MONTHS = 600

FREQUENCY_PER_YEAR = {"Weekly": 52, "Monthly": 12, "Quarterly": 4, "Yearly": 1}


class InputError(ValueError):
    """Raised when calculator inputs cannot produce a meaningful answer. The message is shown to the user."""


def check_number(name: str, value, minimum: float | None = 0.0, allow_equal: bool = True,
                 maximum: float | None = None) -> float:
    """Return `value` as a float, or raise InputError with a plain-English message."""
    if isinstance(value, bool):
        raise InputError(f"{name} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise InputError(f"{name} must be a number.") from None
    if math.isnan(number) or math.isinf(number):
        raise InputError(f"{name} must be a finite number.")
    if minimum is not None and (number < minimum or (not allow_equal and number == minimum)):
        relation = "at least" if allow_equal else "more than"
        raise InputError(f"{name} must be {relation} {minimum:g}.")
    if maximum is not None and number > maximum:
        raise InputError(f"{name} must be {maximum:g} or less.")
    return number


def loan_monthly_rate(apr_pct: float) -> float:
    """APR in percent -> monthly rate used for loans and credit cards."""
    return apr_pct / 100.0 / 12.0


def growth_monthly_rate(annual_return_pct: float) -> float:
    """Effective annual return in percent -> equivalent monthly rate used for savings and investing."""
    return (1 + annual_return_pct / 100.0) ** (1 / 12) - 1
