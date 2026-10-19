"""Calculator Center: one place for the best calculator of each kind found in the audit.

Every calculator validates its inputs, shows a chart and a table, and states its assumptions.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finlife import metrics
from finlife.calc import debt as debt_calc
from finlife.calc import loans, retirement, savings, tax
from finlife.calc.common import InputError
from finlife.ui import charts
from finlife.ui import common as ui

ss = st.session_state

CALCS = {
    "🏠 Loan & mortgage": "loan",
    "🔁 Refinance": "refi",
    "💳 Debt payoff": "debt",
    "🎯 Savings goal": "goal",
    "📈 Investment growth": "growth",
    "🛟 Emergency fund": "emergency",
    "🏖️ Retirement": "retire",
    "🧾 Take-home pay": "tax",
    "📺 Subscriptions": "subs",
}


def _error(exc: Exception) -> None:
    st.error(f"Check the inputs: {exc}", icon="⚠️")


def loan_calc() -> None:
    st.markdown("How much a fixed-rate loan costs each month and in total, and what extra payments save.")
    c = st.columns(4)
    amount = c[0].number_input("Loan amount", min_value=0.0, value=400_000.0, step=5_000.0, key="ln_amt")
    apr = c[1].number_input("Interest rate (APR %)", min_value=0.0, max_value=100.0, value=6.5, step=0.125, key="ln_apr")
    years = c[2].number_input("Term (years)", min_value=1, max_value=50, value=30, key="ln_yrs")
    extra = c[3].number_input("Extra per month", min_value=0.0, value=200.0, step=50.0, key="ln_extra")
    try:
        res = loans.amortization_schedule(amount, apr, int(years) * 12, extra)
        base = loans.amortization_schedule(amount, apr, int(years) * 12, 0) if extra else res
    except InputError as exc:
        return _error(exc)
    c = st.columns(4)
    c[0].metric("Monthly payment", ui.fmt(res.payment), help="Principal and interest only.")
    c[1].metric("Total interest (no extra)", ui.fmt0(base.total_interest))
    c[2].metric("Paid off in", f"{res.months // 12} y {res.months % 12} m")
    c[3].metric("Saved by paying extra", ui.fmt0(res.interest_saved),
                delta=f"{res.months_saved} months sooner" if res.months_saved else None)
    frame = pd.DataFrame(res.rows)
    base_frame = pd.DataFrame(base.rows)
    fig = go.Figure()
    fig.add_scatter(x=base_frame["Month"] / 12, y=base_frame["Balance"], name="Regular payments",
                    line=dict(color=ui.ORANGE, width=2, dash="dot"))
    fig.add_scatter(x=frame["Month"] / 12, y=frame["Balance"], name=f"With {ui.fmt0(extra)} extra",
                    line=dict(color=ui.BLUE, width=3))
    fig.update_layout(title="Remaining balance", xaxis_title="Years")
    ui.show_fig(ui.style_fig(fig))
    yearly = frame.assign(Year=(frame["Month"] - 1) // 12 + 1).groupby("Year").agg(
        Paid=("Payment", "sum"), Principal=("Principal", "sum"), Interest=("Interest", "sum"),
        Balance=("Balance", "last")).reset_index()
    with st.expander("Year-by-year schedule"):
        st.dataframe(yearly, hide_index=True, width="stretch",
                     column_config={k: ui.money_col(k) for k in ["Paid", "Principal", "Interest", "Balance"]})
    ui.estimate_note("Fixed rate, interest charged monthly at APR ÷ 12. Excludes property tax, insurance, PMI and fees.")


def refi_calc() -> None:
    st.markdown("Does refinancing pay off? Compares your current loan with a new one for the same balance.")
    c = st.columns(3)
    bal = c[0].number_input("Current balance", min_value=0.0, value=350_000.0, step=5_000.0, key="rf_bal")
    cur = c[1].number_input("Current APR %", min_value=0.0, max_value=100.0, value=7.25, step=0.125, key="rf_cur")
    left = c[2].number_input("Months left on current loan", min_value=1, max_value=600, value=324, key="rf_left")
    c = st.columns(3)
    new = c[0].number_input("New APR %", min_value=0.0, max_value=100.0, value=6.0, step=0.125, key="rf_new")
    term = c[1].number_input("New term (months)", min_value=1, max_value=600, value=360, key="rf_term")
    cost = c[2].number_input("Closing costs", min_value=0.0, value=6_000.0, step=500.0, key="rf_cost")
    try:
        r = loans.refinance(bal, cur, int(left), new, int(term), cost)
    except InputError as exc:
        return _error(exc)
    c = st.columns(4)
    c[0].metric("Current payment", ui.fmt(r["current_payment"]))
    c[1].metric("New payment", ui.fmt(r["new_payment"]), delta=ui.fmt(-r["monthly_savings"]), delta_color="inverse")
    c[2].metric("Break-even", f"{r['breakeven_months']} months" if r["breakeven_months"] is not None else "Never",
                help="Closing costs ÷ monthly savings.")
    c[3].metric("Lifetime cost change", ui.fmt0(r["lifetime_change"]),
                help="New interest + closing costs − remaining interest on the current loan. Negative = cheaper.")
    if r["lifetime_change"] > 0 and r["monthly_savings"] > 0:
        st.warning("Lower monthly payment, but more total cost: the longer term adds interest.")
    fig = go.Figure(go.Bar(x=["Keep current loan", "Refinance"],
                           y=[r["current_interest"], r["new_interest"] + cost],
                           marker_color=[ui.ORANGE, ui.BLUE], text=[ui.fmt0(r["current_interest"]),
                                                                     ui.fmt0(r["new_interest"] + cost)]))
    fig.update_layout(title="Remaining interest (+ closing costs)")
    ui.show_fig(ui.style_fig(fig, height=300))
    ui.estimate_note("Same balance on both loans; ignores taxes, points and how long you keep the home.")


def debt_calc_view(data: dict) -> None:
    st.markdown("Pay several debts with one monthly budget. **Avalanche** pays the highest rate first (least "
                "interest); **Snowball** pays the smallest balance first (quick wins).")
    rows = [{"name": d.get("name"), "balance": d.get("balance"), "apr": d.get("apr"),
             "min_payment": d.get("min_payment")} for d in data["debts"]]
    if not rows:
        rows = [{"name": "Credit card", "balance": 3000.0, "apr": 22.9, "min_payment": 90.0}]
    st.caption("Starts from your debts in Accounts & Net Worth; edits here are only for this calculation.")
    edited = st.data_editor(pd.DataFrame(rows, columns=["name", "balance", "apr", "min_payment"]),
                            key=f"calc_debts_{ss.ver}", num_rows="dynamic", hide_index=True, width="stretch",
                            column_config={"name": "Debt", "balance": ui.money_col("Balance"),
                                           "apr": st.column_config.NumberColumn("APR %", format="%.2f"),
                                           "min_payment": ui.money_col("Minimum")})
    debts, problems = debt_calc.clean_debts(edited.to_dict("records"))
    for p in problems:
        st.warning(p)
    minimum = sum(d.min_payment for d in debts)
    budget = st.number_input("Total you can pay each month", min_value=0.0, value=float(round(minimum + 300, -1)),
                             step=25.0, key=f"debt_budget_{ss.ver}", help=f"Minimums add up to {ui.fmt(minimum)}.")
    try:
        av = debt_calc.payoff_plan(debts, budget, "Avalanche")
        sn = debt_calc.payoff_plan(debts, budget, "Snowball")
    except InputError as exc:
        return _error(exc)
    for w in dict.fromkeys(av.warnings + sn.warnings):
        st.warning(w)
    c = st.columns(4)
    c[0].metric("Avalanche: debt-free in", f"{av.months} months" if av.paid_off else "50+ years")
    c[1].metric("Avalanche interest", ui.fmt0(av.total_interest))
    c[2].metric("Snowball: debt-free in", f"{sn.months} months" if sn.paid_off else "50+ years")
    c[3].metric("Snowball interest", ui.fmt0(sn.total_interest),
                delta=ui.fmt0(sn.total_interest - av.total_interest) + " more" if sn.total_interest > av.total_interest + 0.5 else None,
                delta_color="inverse")
    pick = st.radio("Show the plan for", debt_calc.STRATEGIES, horizontal=True, key="debt_pick")
    plan = av if pick == "Avalanche" else sn
    hist = pd.DataFrame(plan.history)
    fig = go.Figure()
    for i, (name, part) in enumerate(hist.groupby("Debt", sort=False)):
        fig.add_scatter(x=part["Month"], y=part["Balance"], name=name, stackgroup="one", mode="lines",
                        line=dict(width=0.5, color=ui.SERIES[i % len(ui.SERIES)]))
    fig.update_layout(title=f"{pick}: balances over time", xaxis_title="Month")
    ui.show_fig(ui.style_fig(fig))
    st.dataframe(pd.DataFrame([{"Debt": k, "Paid off in month": v if v is not None else "not within 50 years"}
                               for k, v in plan.payoff_month.items()]), hide_index=True, width="stretch")
    ui.estimate_note("Fixed APRs, interest charged monthly, no new charges or fees, the same total payment every month.")


def goal_calc(data: dict) -> None:
    st.markdown("How much to save each month to reach a target, or how long it takes at a set amount.")
    c = st.columns(4)
    target = c[0].number_input("Goal amount", min_value=0.0, value=20_000.0, step=500.0, key="g_target")
    have = c[1].number_input("Saved so far", min_value=0.0, value=2_000.0, step=500.0, key="g_have")
    months = c[2].number_input("Months to goal", min_value=1, max_value=600, value=36, key="g_months")
    rate = c[3].number_input("Interest / return % per year", min_value=0.0, max_value=50.0, value=4.0, step=0.25,
                             key="g_rate", help="A high-yield savings rate for short goals.")
    deposit = st.number_input("…or if I save this much per month", min_value=0.0, value=400.0, step=50.0, key="g_dep")
    try:
        need = savings.required_monthly_saving(target, have, rate, int(months))
        took = savings.months_to_goal(target, have, deposit, rate)
    except InputError as exc:
        return _error(exc)
    c = st.columns(2)
    c[0].metric("Save per month", ui.fmt(need), help="Deposited at the end of each month.")
    c[1].metric(f"Time at {ui.fmt0(deposit)}/month",
                f"{took // 12} y {took % 12} m" if took is not None else "50+ years")
    years = max(1, -(-int(months) // 12))
    try:
        rows = pd.DataFrame(savings.compound_growth(have, need, rate, years))
    except InputError as exc:
        return _error(exc)
    ui.show_fig(charts.stacked_growth(rows))
    ui.estimate_note("Constant return, compounded monthly; deposits at month-end; taxes on interest ignored.")


def growth_calc() -> None:
    st.markdown("How regular investing could grow, what fees cost, and what it's worth in today's money.")
    c = st.columns(3)
    start = c[0].number_input("Starting amount", min_value=0.0, value=10_000.0, step=1_000.0, key="gr_start")
    monthly = c[1].number_input("Added each month", min_value=0.0, value=500.0, step=50.0, key="gr_month")
    years = c[2].slider("Years", 1, 50, 25, key="gr_years")
    c = st.columns(3)
    ret = c[0].slider("Average yearly return % (assumption)", -5.0, 15.0, 6.0, 0.5, key="gr_ret")
    fee = c[1].slider("Yearly fees % (fund expense ratio + advice)", 0.0, 3.0, 0.5, 0.05, key="gr_fee")
    infl = c[2].slider("Inflation %", 0.0, 8.0, 2.5, 0.1, key="gr_infl")
    try:
        rows = pd.DataFrame(savings.compound_growth(start, monthly, ret, years, fee, infl))
    except InputError as exc:
        return _error(exc)
    last = rows.iloc[-1]
    c = st.columns(4)
    c[0].metric("Projected balance", ui.fmt0(last["Balance"]))
    c[1].metric("You put in", ui.fmt0(last["Contributions"]))
    c[2].metric("Lost to fees", ui.fmt0(last["Without fees"] - last["Balance"]))
    c[3].metric("In today's dollars", ui.fmt0(last["Today's dollars"]))
    ui.show_fig(charts.stacked_growth(rows))
    with st.expander("Year-by-year table"):
        st.dataframe(rows, hide_index=True, width="stretch",
                     column_config={k: ui.money_col(k) for k in rows.columns if k != "Year"})
    ui.estimate_note("Returns are an assumption, not a prediction: real returns vary year to year and can be negative. "
                     "Fees are taken from the balance each year; taxes are ignored.")


def emergency_calc(data: dict, m: dict) -> None:
    st.markdown("How many months your emergency cash would cover essential bills.")
    c = st.columns(3)
    have = c[0].number_input("Emergency savings", min_value=0.0, value=float(round(m["emergency_savings"])),
                             step=500.0, key=f"em_have_{ss.ver}", help="Default: accounts ticked Emergency fund.")
    need = c[1].number_input("Essential spending per month", min_value=0.0,
                             value=float(round(m["essentials"])) or 3_000.0, step=100.0, key=f"em_need_{ss.ver}",
                             help=f"Default: {m['essentials_basis']}.")
    target = c[2].slider("Target months", 1, 12, int(data["settings"].get("emergency_months") or 6), key="em_target")
    if st.button("Use this target everywhere", help="Updates the Dashboard and Action Center target."):
        data["settings"]["emergency_months"] = float(target)
        ui.commit(f"Emergency-fund target set to {target} months.")
        st.rerun()
    try:
        r = savings.emergency_fund(have, need, target)
    except InputError as exc:
        return _error(exc)
    c = st.columns(3)
    c[0].metric("Months covered", f"{r['months_covered']:.1f}")
    c[1].metric("Target amount", ui.fmt0(r["target_amount"]))
    c[2].metric("Still to save" if not r["met"] else "Above target", ui.fmt0(r["gap"] or r["surplus"]))
    ui.show_fig(charts.gauge(r["months_covered"], target, "Months of essentials covered", " mo"))
    if not r["met"]:
        for monthly in (250, 500, 1000):
            st.caption(ui.md(f"Saving {ui.fmt0(monthly)}/month closes the gap in about "
                             f"{-(-r['gap'] // monthly):.0f} months."))
    ui.estimate_note("There is no universal right number; 3–6 months is a common guide. Single-income households, "
                     "self-employment or health needs call for more.")


def retire_calc(data: dict) -> None:
    st.markdown("A rough retirement check: the savings you might need (the *FI number*) and whether your savings "
                "plan gets there.")
    c = st.columns(4)
    age = c[0].number_input("Your age", min_value=18, max_value=100, value=40, key="rt_age")
    retire_at = c[1].number_input("Retire at", min_value=19, max_value=100, value=65, key="rt_at")
    spend = c[2].number_input("Yearly spending in retirement (today's dollars)", min_value=0.0, value=80_000.0,
                              step=1_000.0, key="rt_spend")
    other = c[3].number_input("Social Security / pension per year", min_value=0.0, value=30_000.0, step=1_000.0,
                              key="rt_other", help="Check your estimate at ssa.gov/myaccount.")
    c = st.columns(4)
    invested = sum(float(a.get("balance") or 0) for a in data["accounts"] if a.get("type") in ("Retirement", "Investment"))
    saved = c[0].number_input("Retirement savings now", min_value=0.0, value=float(round(invested)) or 150_000.0,
                              step=5_000.0, key=f"rt_saved_{ss.ver}", help="Default: your Retirement and Investment accounts.")
    monthly = c[1].number_input("Saving per month", min_value=0.0, value=1_500.0, step=100.0, key="rt_monthly")
    real = c[2].slider("Return after inflation %", 0.0, 8.0, 4.0, 0.25, key="rt_real",
                       help="Using an after-inflation return keeps every number in today's dollars.")
    wr = c[3].slider("Safe withdrawal rate %", 2.5, 6.0, 4.0, 0.25, key="rt_wr",
                     help="The 4% rule of thumb: withdraw 4% in year one, then adjust for inflation.")
    try:
        years = retirement.check_retirement_inputs(int(age), int(retire_at))
        target = retirement.fi_number(spend, other, wr)
        growth = pd.DataFrame(savings.compound_growth(saved, monthly, real, years))
        at_retire = float(growth.iloc[-1]["Balance"])
        drawdown = retirement.money_lasts(at_retire, max(0.0, spend - other), real, 60)
        last = pd.DataFrame(drawdown)
    except InputError as exc:
        return _error(exc)
    c = st.columns(3)
    c[0].metric("Target (FI number)", ui.fmt0(target), help="(Spending − guaranteed income) ÷ withdrawal rate.")
    c[1].metric(f"Projected at {int(retire_at)}", ui.fmt0(at_retire),
                delta=f"{at_retire / target:.0%} of target" if target else None)
    out = retirement.run_out_year(drawdown)
    c[2].metric("Money lasts", f"about {out} years" if out else "60+ years",
                help="Withdrawing the spending gap each year at the same after-inflation return.")
    fig = go.Figure()
    fig.add_scatter(x=growth["Year"] + int(age), y=growth["Balance"], name="Saving", line=dict(color=ui.BLUE, width=3))
    fig.add_scatter(x=last["Year"] + int(retire_at), y=last["Balance"], name="Spending down",
                    line=dict(color=ui.ORANGE, width=3))
    fig.add_hline(y=target, line_dash="dot", line_color=ui.GREEN, annotation_text="Target")
    fig.update_layout(title="Savings over your lifetime (today's dollars)", xaxis_title="Age")
    ui.show_fig(ui.style_fig(fig))
    ui.estimate_note("Constant after-inflation return; ignores taxes on withdrawals, market ups and downs, and "
                     "required minimum distributions. Use it to see direction, then plan with a professional.")


def tax_calc() -> None:
    st.markdown(f"A rough **{tax.TAX_YEAR}** paycheck estimate: federal income tax, Social Security, Medicare and "
                "(optionally) California income tax and SDI.")
    c = st.columns(3)
    status = c[0].selectbox("Filing status", tax.FILING_STATUSES, key="tx_status")
    gross = c[1].number_input("Your salary + bonus per year", min_value=0.0, value=180_000.0, step=5_000.0, key="tx_gross")
    spouse = c[2].number_input("Spouse salary + bonus", min_value=0.0, value=95_000.0 if status != "Single" else 0.0,
                               step=5_000.0, key=f"tx_spouse_{status}", disabled=status == "Single")
    c = st.columns(5)
    k401 = c[0].number_input("401(k) pre-tax", min_value=0.0, value=24_500.0, step=500.0, key="tx_401k")
    hsa = c[1].number_input("HSA (payroll)", min_value=0.0, value=8_750.0, step=250.0, key="tx_hsa")
    fsa = c[2].number_input("FSA", min_value=0.0, value=0.0, step=250.0, key="tx_fsa")
    prem = c[3].number_input("Health premiums (pre-tax)", min_value=0.0, value=3_600.0, step=100.0, key="tx_prem")
    kids = c[4].number_input("Children under 17", min_value=0, max_value=15, value=1, key="tx_kids")
    ca = st.toggle("I live in California", value=True, key="tx_ca")
    try:
        r = tax.take_home(gross, status, spouse if status != "Single" else 0.0, k401, hsa, fsa, prem, int(kids), ca)
    except InputError as exc:
        return _error(exc)
    c = st.columns(4)
    c[0].metric("Take-home per year", ui.fmt0(r["Take-home pay"]))
    c[1].metric("Take-home per month", ui.fmt0(r["Take-home pay"] / 12))
    c[2].metric("Total taxes", ui.fmt0(r["Total taxes"]), delta=f"{r['Effective tax rate']:.1%} of pay",
                delta_color="off")
    c[3].metric("Next-dollar tax rate", f"{r['Federal marginal rate'] + r['California marginal rate']:.1%}",
                help="Federal + California income-tax rate on your next dollar (Social Security/Medicare not included).")
    parts = {k: r[k] for k in ["Take-home pay", "Pre-tax deductions", "Federal income tax", "Social Security",
                               "Medicare", "California income tax", "CA SDI"] if r[k] > 0}
    fig = go.Figure(go.Pie(labels=list(parts), values=list(parts.values()), hole=0.55,
                           marker=dict(colors=ui.SERIES[: len(parts)]), sort=False,
                           hovertemplate="%{label}: %{value:,.0f} (%{percent})<extra></extra>"))
    fig.update_layout(title="Where each paycheck dollar goes")
    left, right = st.columns([3, 2])
    with left:
        ui.show_fig(ui.style_fig(fig, height=340, money_axis=None))
    with right:
        st.dataframe(pd.DataFrame([{"Item": k, "Per year": v, "Per month": v / 12} for k, v in r.items()
                                   if "rate" not in k]), hide_index=True, width="stretch",
                     column_config={"Per year": ui.money_col("Per year"), "Per month": ui.money_col("Per month")})
    ui.estimate_note(f"Federal {tax.TAX_YEAR} brackets and standard deduction; California uses the {tax.CA_YEAR} FTB "
                     "schedule (latest published when written). Ignores itemized deductions, other credits "
                     "(including California exemption credits and the refundable part of the child tax credit), "
                     "AMT, capital-gains rates and local taxes. Check with the IRS Tax Withholding Estimator.")


def subs_calc(data: dict) -> None:
    st.markdown("What your subscriptions really cost per year. Edit them in the **Action Center → Subscriptions**.")
    rows, problems = savings.subscription_costs(data["subscriptions"])
    for p in problems:
        st.warning(p)
    if not rows:
        st.info("No active subscriptions. Add them in the Action Center.")
        return
    frame = pd.DataFrame(rows)
    c = st.columns(3)
    c[0].metric("Per month", ui.fmt(frame["Monthly"].sum()))
    c[1].metric("Per year", ui.fmt0(frame["Annual"].sum()))
    review = [s for s in data["subscriptions"] if s.get("decision") in ("Review", "Cancel") and not s.get("cancelled")]
    c[2].metric("Marked review/cancel", str(len(review)))
    ui.show_fig(charts.horizontal_totals(frame, "Subscription", "Annual", "Yearly cost of each subscription"))
    st.dataframe(frame, hide_index=True, width="stretch",
                 column_config={k: ui.money_col(k) for k in ["Amount", "Monthly", "Annual"]})


def render() -> None:
    data, today = ui.data(), ui.today()
    st.title("🧮 Calculator Center")
    st.caption("Plain-English calculators. Results are **estimates** from the assumptions shown under each one.")
    m = metrics.compute(data, today)
    pick = st.pills("Choose a calculator", list(CALCS), default=list(CALCS)[0], key="calc_pick")
    pick = pick or list(CALCS)[0]
    st.subheader(pick)
    which = CALCS[pick]
    if which == "loan":
        loan_calc()
    elif which == "refi":
        refi_calc()
    elif which == "debt":
        debt_calc_view(data)
    elif which == "goal":
        goal_calc(data)
    elif which == "growth":
        growth_calc()
    elif which == "emergency":
        emergency_calc(data, m)
    elif which == "retire":
        retire_calc(data)
    elif which == "tax":
        tax_calc()
    else:
        subs_calc(data)
