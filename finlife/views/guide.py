"""Guide & Assumptions: what each page does and every assumption behind the numbers, in plain English."""

from __future__ import annotations

import streamlit as st

from finlife.calc import tax
from finlife.data import transactions as tx
from finlife.metrics import ESSENTIAL_CATEGORIES


def render() -> None:
    st.title("📘 Guide & Assumptions")
    st.caption("FinLife 360 is a personal organizer and education tool, **not financial, tax or legal advice.**")

    st.markdown("""
#### Getting started in 5 steps
1. **Accounts & Net Worth**: type in your account balances and debts. Tick *Emergency fund* on your cash cushion.
2. **Income & Expenses**: import a CSV from your bank or card (or add transactions by hand). Fix any categories.
3. **Budget & Goals**: set a monthly budget per category, add savings goals and recurring bills.
4. **Action Center**: work through the list from the top. Press *Done* as you go.
5. Once a month: update balances, press **Record snapshot**, and glance at the **Dashboard**.
""")

    st.markdown("#### What each page does")
    st.table({
        "Page": ["Dashboard", "Action Center", "Income & Expenses", "Budget & Goals", "Accounts & Net Worth",
                 "Calculator Center", "Import & Export"],
        "Use it to…": [
            "See income, spending, savings rate, net worth, emergency fund, budget and top actions at a glance.",
            "Work a prioritized to-do list; manage tasks, subscriptions, insurance renewals and documents.",
            "Add, import, categorize and correct transactions; find duplicates and transfers.",
            "Set budgets, track goals and bills, and project your balance forward.",
            "Track what you own and owe, and net worth over time.",
            "Loan, refinance, debt payoff, savings goal, investment growth, emergency fund, retirement, take-home pay "
            "and subscription calculators.",
            "Export or import any table as CSV, or everything as JSON.",
        ]})

    st.markdown("#### Assumptions behind the numbers")
    st.markdown(f"""
- **Signs:** negative amounts are money out, positive are money in.
- **Not double counted:** {', '.join(tx.EXCLUDED_CATEGORIES)} rows are left out of income and spending. Refunds reduce
  their category's spending.
- **Averages** use complete past months only, so a half-finished month does not drag them down.
- **Essential spending** (for the emergency fund) = {', '.join(ESSENTIAL_CATEGORIES)}.
- **Loans and cards:** interest is APR ÷ 12, charged monthly. Simulations stop at 50 years.
- **Savings and investments:** the yearly return is converted to an equivalent monthly rate; deposits are made at the
  end of each month; fees come off the balance each year; returns are assumptions, never promises.
- **Retirement:** uses a return *after inflation*, so every amount is in today's dollars. The withdrawal-rate rule
  (often 4%) is a rule of thumb, not a guarantee.
- **Take-home pay:** federal {tax.TAX_YEAR} brackets and standard deduction, Social Security (6.2% up to
  ${tax.SS_WAGE_BASE:,}), Medicare (1.45% + 0.9% above the threshold), California {tax.CA_YEAR} brackets and SDI
  ({tax.CA_SDI_RATE:.1%}). Leaves out itemized deductions, most credits, AMT, capital-gains rates and local taxes.
- **Goals:** progress assumes the same deposit each month and no interest.
- **Sample data** is invented for a fictional household.
""".replace("$", r"\$"))

    st.markdown("#### Privacy")
    st.markdown("""
- No bank logins, no API keys, no AI services, no tracking. Nothing is sent anywhere.
- On your own computer, data is saved to a local JSON file. On a shared server, data stays in your browser tab until you
  close it; download a backup to keep it.
- Never type account numbers, passwords or Social Security numbers into any field.
""")
    st.markdown("#### Check the official sources")
    st.markdown("""
- [IRS Tax Withholding Estimator](https://www.irs.gov/individuals/tax-withholding-estimator)
- [California FTB tax rates](https://www.ftb.ca.gov/file/personal/tax-calculator-tables-rates.html)
- [Consumer Financial Protection Bureau](https://www.consumerfinance.gov/)
- [SEC Investor.gov compound interest calculator](https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator)
- [Social Security retirement estimate](https://www.ssa.gov/myaccount/)
- [Free credit reports](https://www.annualcreditreport.com/)
""")
