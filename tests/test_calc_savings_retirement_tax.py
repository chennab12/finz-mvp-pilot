import pytest

from finlife.calc import retirement, savings, tax
from finlife.calc.common import InputError, growth_monthly_rate


def test_growth_rate_is_effective_annual():
    # 12 monthly steps of the converted rate give exactly the yearly rate.
    assert (1 + growth_monthly_rate(7)) ** 12 == pytest.approx(1.07)


def test_compound_growth_zero_rate_is_just_contributions():
    rows = savings.compound_growth(1000, 100, 0, 2)
    assert rows[-1]["Balance"] == pytest.approx(3400)
    assert rows[-1]["Growth"] == pytest.approx(0)


def test_compound_growth_lump_sum_matches_annual_rate():
    rows = savings.compound_growth(10_000, 0, 8, 10)
    assert rows[-1]["Balance"] == pytest.approx(10_000 * 1.08 ** 10)


def test_compound_growth_documented_reference_value():
    """Locks the convention chosen in the audit: $10k + $500/mo at 7% for 20 years."""
    rows = savings.compound_growth(10_000, 500, 7, 20)
    assert rows[-1]["Balance"] == pytest.approx(292_465.03, abs=1)


def test_fees_are_multiplicative_and_inflation_discounts():
    rows = savings.compound_growth(10_000, 0, 6, 10, annual_fee_pct=1, inflation_pct=2)
    assert savings.net_return_pct(6, 1) == pytest.approx(4.94)
    assert rows[-1]["Balance"] == pytest.approx(10_000 * 1.0494 ** 10, rel=1e-6)
    assert rows[-1]["Without fees"] == pytest.approx(10_000 * 1.06 ** 10)
    assert rows[-1]["Today's dollars"] == pytest.approx(rows[-1]["Balance"] / 1.02 ** 10)


def test_required_monthly_saving():
    assert savings.required_monthly_saving(12_000, 0, 0, 12) == pytest.approx(1000)
    assert savings.required_monthly_saving(12_000, 0, 5, 12) < 1000
    assert savings.required_monthly_saving(1000, 1000, 5, 12) == 0


def test_required_saving_reaches_target_when_simulated():
    need = savings.required_monthly_saving(20_000, 2_000, 4, 36)
    assert savings.months_to_goal(20_000, 2_000, need + 0.01, 4) == 36


def test_months_to_goal():
    assert savings.months_to_goal(1200, 0, 100, 0) == 12
    assert savings.months_to_goal(1000, 1000, 0, 0) == 0
    assert savings.months_to_goal(1000, 0, 0, 0) is None


def test_emergency_fund():
    ef = savings.emergency_fund(9000, 3000, 6)
    assert ef["months_covered"] == pytest.approx(3)
    assert ef["gap"] == pytest.approx(9000) and not ef["met"]
    with pytest.raises(InputError):
        savings.emergency_fund(1000, 0, 6)


def test_subscription_costs():
    rows, problems = savings.subscription_costs([
        {"name": "A", "amount": 10, "billing": "Monthly"},
        {"name": "B", "amount": 120, "billing": "Yearly"},
        {"name": "C", "amount": 5, "billing": "Weekly"},
        {"name": "Off", "amount": 50, "billing": "Monthly", "cancelled": True},
        {"name": "Bad", "amount": -1, "billing": "Monthly"},
        {"name": "Odd", "amount": 1, "billing": "Daily"},
    ])
    assert {r["Subscription"]: r["Annual"] for r in rows} == {"A": 120, "B": 120, "C": 260}
    assert len(problems) == 2


def test_fi_number():
    assert retirement.fi_number(80_000, 30_000, 4) == pytest.approx(1_250_000)
    assert retirement.fi_number(20_000, 30_000, 4) == 0
    with pytest.raises(InputError):
        retirement.fi_number(80_000, 0, 0)


def test_money_lasts_runs_out_when_withdrawals_exceed_balance():
    rows = retirement.money_lasts(100_000, 25_000, 0, 60)
    assert retirement.run_out_year(rows) == 4
    assert retirement.run_out_year(retirement.money_lasts(1_000_000, 30_000, 4, 60)) is None


def test_retirement_age_validation():
    assert retirement.check_retirement_inputs(40, 65) == 25
    with pytest.raises(InputError):
        retirement.check_retirement_inputs(65, 60)


def test_progressive_tax_bracket_edges():
    b = tax.FED_BRACKETS["Married filing jointly"]
    assert tax.progressive_tax(24_800, b) == pytest.approx(2_480)
    assert tax.progressive_tax(100_800, b) == pytest.approx(2_480 + 76_000 * 0.12)
    assert tax.marginal_rate(100_800, b) == 0.12
    assert tax.marginal_rate(100_801, b) == 0.22
    assert tax.progressive_tax(0, b) == 0


def test_single_brackets_and_ca_single_is_half_of_joint():
    assert tax.progressive_tax(12_400, tax.FED_BRACKETS["Single"]) == pytest.approx(1_240)
    assert tax.CA_BRACKETS["Single"][0] == (11_079, 0.01)


def test_child_tax_credit_phase_out():
    assert tax.child_tax_credit(2, 300_000, "Married filing jointly") == 4_400
    assert tax.child_tax_credit(1, 410_000, "Married filing jointly") == 2_200 - 500
    assert tax.child_tax_credit(1, 400_001, "Married filing jointly") == 2_150  # any part of $1,000 counts
    assert tax.child_tax_credit(1, 500_000, "Married filing jointly") == 0


def test_take_home_simple_single_no_state():
    r = tax.take_home(100_000, "Single", california=False)
    taxable = 100_000 - 16_100
    expected_fed = 1_240 + (50_400 - 12_400) * 0.12 + (taxable - 50_400) * 0.22
    assert r["Federal income tax"] == pytest.approx(expected_fed)
    assert r["Social Security"] == pytest.approx(6_200)
    assert r["Medicare"] == pytest.approx(1_450)
    assert r["Take-home pay"] == pytest.approx(100_000 - expected_fed - 7_650)


def test_take_home_payroll_treatment():
    base = tax.take_home(150_000, "Married filing jointly", california=True)
    with401k = tax.take_home(150_000, "Married filing jointly", pretax_401k=10_000, california=True)
    withhsa = tax.take_home(150_000, "Married filing jointly", hsa=10_000, california=True)
    # 401(k) lowers income tax but not FICA; HSA lowers both, but California still taxes it.
    assert with401k["Social Security"] == base["Social Security"]
    assert withhsa["Social Security"] < base["Social Security"]
    assert withhsa["California taxable income"] == base["California taxable income"]
    assert with401k["California taxable income"] == base["California taxable income"] - 10_000


def test_social_security_is_capped_per_earner():
    one = tax.take_home(300_000, "Married filing jointly", california=False)
    two = tax.take_home(150_000, "Married filing jointly", spouse_gross=150_000, california=False)
    assert one["Social Security"] == pytest.approx(tax.SS_RATE * tax.SS_WAGE_BASE)
    assert two["Social Security"] == pytest.approx(tax.SS_RATE * 300_000)


def test_take_home_validation():
    with pytest.raises(InputError):
        tax.take_home(100_000, "Head of household")
    with pytest.raises(InputError):
        tax.take_home(100_000, "Single", spouse_gross=10)
    with pytest.raises(InputError):
        tax.take_home(10_000, pretax_401k=20_000)
