"""Loan payment, amortization schedule with extra payments, and refinance break-even.

Sources: amortization schedule from finz-admin-pilot (tested); refinance comparison from
home-admin-faqs, rewritten with input validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .common import MAX_MONTHS, InputError, check_number, loan_monthly_rate


def loan_payment(principal: float, apr_pct: float, months: int) -> float:
    """Fixed monthly payment that repays `principal` over `months` (0% handled exactly)."""
    principal = check_number("Loan amount", principal, 0, allow_equal=False)
    rate = check_number("Interest rate", apr_pct, 0, maximum=100)
    months = int(check_number("Term (months)", months, 1))
    if months > MAX_MONTHS:
        raise InputError(f"Term must be {MAX_MONTHS} months or less.")
    r = loan_monthly_rate(rate)
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


@dataclass
class AmortizationResult:
    payment: float
    rows: list[dict]
    total_interest: float
    total_paid: float
    months: int
    months_saved: int = 0
    interest_saved: float = 0.0


def amortization_schedule(principal: float, apr_pct: float, months: int,
                          extra_payment: float = 0.0) -> AmortizationResult:
    """Month-by-month schedule. The final payment is trimmed so the balance ends at exactly 0."""
    payment = loan_payment(principal, apr_pct, months)
    extra = check_number("Extra monthly payment", extra_payment, 0)
    r = loan_monthly_rate(apr_pct)
    balance = float(principal)
    rows: list[dict] = []
    total_interest = 0.0
    month = 0
    while balance > 0.005 and month < MAX_MONTHS:
        month += 1
        interest = balance * r
        due = balance + interest
        paid = min(payment + extra, due)
        balance = due - paid
        if balance < 0.005:
            balance = 0.0
        total_interest += interest
        rows.append({"Month": month, "Payment": paid, "Principal": paid - interest, "Interest": interest,
                     "Balance": balance})
    total_paid = sum(row["Payment"] for row in rows)
    result = AmortizationResult(payment, rows, total_interest, total_paid, month)
    if extra > 0:
        base = amortization_schedule(principal, apr_pct, months, 0.0)
        result.months_saved = base.months - month
        result.interest_saved = base.total_interest - total_interest
    return result


def refinance(balance: float, current_apr: float, months_left: int, new_apr: float, new_months: int,
              closing_costs: float) -> dict:
    """Compare keeping a loan with refinancing the same balance.

    Returns current and new payments, monthly savings, the break-even month (closing costs ÷ monthly
    savings, rounded up; None when the new payment is not lower) and the lifetime cost difference
    (new interest + closing costs − remaining current interest). Negative lifetime change = refinancing
    costs less over the life of the loans.
    """
    closing = check_number("Closing costs", closing_costs, 0)
    old = loan_payment(balance, current_apr, months_left)
    new = loan_payment(balance, new_apr, new_months)
    savings = old - new
    breakeven = None if savings <= 0.005 else int(-(-closing // savings)) if closing > 0 else 0
    old_interest = old * int(months_left) - balance
    new_interest = new * int(new_months) - balance
    return {"current_payment": old, "new_payment": new, "monthly_savings": savings, "breakeven_months": breakeven,
            "current_interest": old_interest, "new_interest": new_interest,
            "lifetime_change": new_interest + closing - old_interest}
