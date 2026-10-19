import pytest

from finlife.calc import debt, loans
from finlife.calc.common import MAX_MONTHS, InputError


def test_loan_payment_matches_textbook_value():
    # 200,000 at 6% for 30 years is a textbook 1,199.10 per month.
    assert loans.loan_payment(200_000, 6, 360) == pytest.approx(1199.10, abs=0.01)


def test_zero_interest_loan_is_principal_over_months():
    assert loans.loan_payment(12_000, 0, 24) == pytest.approx(500.0)
    res = loans.amortization_schedule(12_000, 0, 24)
    assert res.months == 24 and res.total_interest == 0 and res.rows[-1]["Balance"] == 0


def test_amortization_ends_at_zero_and_totals_add_up():
    res = loans.amortization_schedule(25_000, 6.5, 60)
    assert res.months == 60
    assert res.rows[-1]["Balance"] == 0
    assert res.total_paid == pytest.approx(25_000 + res.total_interest, abs=0.01)
    assert sum(r["Principal"] for r in res.rows) == pytest.approx(25_000, abs=0.01)


def test_extra_payment_shortens_loan_and_saves_interest():
    res = loans.amortization_schedule(25_000, 6.5, 60, extra_payment=200)
    assert res.months < 60
    assert res.months_saved == 60 - res.months
    assert res.interest_saved > 0


@pytest.mark.parametrize("args", [(0, 5, 12), (-1, 5, 12), (1000, -1, 12), (1000, 5, 0), (1000, 5, 601),
                                  ("abc", 5, 12), (float("nan"), 5, 12), (1000, 101, 12), (True, 5, 12)])
def test_invalid_loan_inputs_raise(args):
    with pytest.raises(InputError):
        loans.loan_payment(*args)


def test_refinance_break_even_and_lifetime_cost():
    r = loans.refinance(300_000, 7.0, 360, 6.0, 360, 6_000)
    assert r["current_payment"] == pytest.approx(1995.91, abs=0.01)
    assert r["new_payment"] == pytest.approx(1798.65, abs=0.01)
    assert r["breakeven_months"] == 31  # 6,000 / 197.26 = 30.4 -> 31
    assert r["lifetime_change"] < 0


def test_refinance_to_higher_payment_never_breaks_even():
    r = loans.refinance(100_000, 5.0, 120, 6.0, 120, 2_000)
    assert r["monthly_savings"] < 0 and r["breakeven_months"] is None


def test_debt_avalanche_beats_snowball_on_interest():
    debts = [debt.Debt("Card", 3000, 24, 90), debt.Debt("Car", 8000, 5, 250)]
    av = debt.payoff_plan(debts, 600, "Avalanche")
    sn = debt.payoff_plan(debts, 600, "Snowball")
    assert av.paid_off and sn.paid_off
    assert av.total_interest <= sn.total_interest
    assert av.total_paid == pytest.approx(3000 + 8000 + av.total_interest, abs=0.05)


def test_debts_with_the_same_name_are_not_merged():
    """Regression for the finz-admin-pilot bug found in the audit."""
    same = [debt.Debt("Card", 1000, 20, 50), debt.Debt("Card", 5000, 10, 100)]
    renamed = [debt.Debt("Card A", 1000, 20, 50), debt.Debt("Card B", 5000, 10, 100)]
    a, b = debt.payoff_plan(same, 300), debt.payoff_plan(renamed, 300)
    assert a.months == b.months == 23
    assert a.total_interest == pytest.approx(b.total_interest)
    assert set(a.payoff_month) == {"Card", "Card (2)"}


def test_debt_payment_below_interest_never_pays_off_and_warns():
    res = debt.payoff_plan([debt.Debt("Card", 10_000, 24, 150)], 150)
    assert not res.paid_off and res.months == MAX_MONTHS
    assert any("does not cover" in w for w in res.warnings)
    assert any("Not paid off" in w for w in res.warnings)


def test_debt_budget_below_minimums_is_rejected():
    with pytest.raises(InputError):
        debt.payoff_plan([debt.Debt("A", 1000, 10, 50), debt.Debt("B", 1000, 10, 50)], 80)


def test_unknown_strategy_rejected():
    with pytest.raises(InputError):
        debt.payoff_plan([debt.Debt("A", 1000, 10, 50)], 100, "Random")


def test_zero_interest_debt_pays_off_exactly():
    res = debt.payoff_plan([debt.Debt("Family loan", 1200, 0, 100)], 100)
    assert res.paid_off and res.months == 12 and res.total_interest == 0


def test_clean_debts_skips_bad_rows():
    debts, problems = debt.clean_debts([
        {"name": "Ok", "balance": 100, "apr": 5, "min_payment": 10},
        {"name": "Bad", "balance": "x", "apr": 5, "min_payment": 10},
        {"name": "Zero", "balance": 0, "apr": 5, "min_payment": 10},
        {"name": "Typo", "balance": 100, "apr": 250, "min_payment": 10},
        {"name": None, "balance": None},
    ])
    assert [d.name for d in debts] == ["Ok"]
    assert len(problems) == 2
