"""Rough 2026 paycheck estimate: federal income tax, FICA, California income tax and CA SDI.

Merged from intel-myben (payroll treatment of 401(k), HSA, FSA and premiums; child tax credit)
and stocks-retire-faqs (two earners, so Social Security is capped per person), with filing status
support and the child-tax-credit income phase-out from taxes-faqs.

What it ignores (shown to the user): itemized deductions, other credits (including California
exemption credits), AMT, capital gains rates, local taxes, and state taxes other than California.
"""

from __future__ import annotations

from .common import InputError, check_number

TAX_YEAR = 2026
FILING_STATUSES = ("Married filing jointly", "Single")

# Federal 2026 (IRS Rev. Proc. 2025-32): (upper bound of bracket, rate).
FED_BRACKETS = {
    "Married filing jointly": [(24_800, 0.10), (100_800, 0.12), (211_400, 0.22), (403_550, 0.24),
                               (512_450, 0.32), (768_700, 0.35), (float("inf"), 0.37)],
    "Single": [(12_400, 0.10), (50_400, 0.12), (105_700, 0.22), (201_775, 0.24), (256_225, 0.32),
               (640_600, 0.35), (float("inf"), 0.37)],
}
FED_STANDARD_DEDUCTION = {"Married filing jointly": 32_200, "Single": 16_100}
CHILD_TAX_CREDIT = 2_200
CTC_PHASEOUT_START = {"Married filing jointly": 400_000, "Single": 200_000}  # $50 less per $1,000 above
SS_RATE, SS_WAGE_BASE = 0.062, 184_500
MEDICARE_RATE, ADDL_MEDICARE_RATE = 0.0145, 0.009
ADDL_MEDICARE_THRESHOLD = {"Married filing jointly": 250_000, "Single": 200_000}

# California: latest published FTB schedule when written (tax year 2025). Single = half of joint.
CA_YEAR = 2025
_CA_JOINT = [(22_158, 0.01), (52_528, 0.02), (82_904, 0.04), (115_084, 0.06), (145_448, 0.08),
             (742_958, 0.093), (891_542, 0.103), (1_485_906, 0.113), (float("inf"), 0.123)]
CA_BRACKETS = {
    "Married filing jointly": _CA_JOINT,
    "Single": [(b / 2 if b != float("inf") else b, r) for b, r in _CA_JOINT],
}
CA_STANDARD_DEDUCTION = {"Married filing jointly": 11_412, "Single": 5_706}
CA_MENTAL_HEALTH_RATE, CA_MENTAL_HEALTH_THRESHOLD = 0.01, 1_000_000
CA_SDI_RATE = 0.013  # 2026, no wage cap


def progressive_tax(taxable: float, brackets: list[tuple[float, float]]) -> float:
    """Tax on `taxable` income using (upper bound, rate) brackets."""
    tax, lower = 0.0, 0.0
    for upper, rate in brackets:
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
        lower = upper
    return tax


def marginal_rate(taxable: float, brackets: list[tuple[float, float]]) -> float:
    for upper, rate in brackets:
        if taxable <= upper:
            return rate
    return brackets[-1][1]


def child_tax_credit(children: int, magi: float, status: str) -> float:
    """$2,200 per child, reduced by $50 for each $1,000 (or part) of income above the phase-out start."""
    full = CHILD_TAX_CREDIT * children
    over = max(0.0, magi - CTC_PHASEOUT_START[status])
    reduction = 50 * -(-over // 1000)
    return max(0.0, full - reduction)


def take_home(gross: float, status: str = "Married filing jointly", spouse_gross: float = 0.0,
              pretax_401k: float = 0.0, hsa: float = 0.0, fsa: float = 0.0, premiums: float = 0.0,
              children: int = 0, california: bool = True) -> dict:
    """Annual paycheck estimate for one household.

    * 401(k) deferrals reduce income tax but not Social Security/Medicare.
    * HSA, FSA and health premiums paid through payroll (cafeteria plan) reduce income tax and
      Social Security/Medicare; California still taxes HSA contributions.
    * Payroll deductions are entered for the household and taken from the first earner's FICA wages.
    """
    if status not in FILING_STATUSES:
        raise InputError(f"Filing status must be one of: {', '.join(FILING_STATUSES)}.")
    gross = check_number("Salary and bonus", gross, 0)
    spouse = check_number("Spouse salary and bonus", spouse_gross, 0)
    if status == "Single" and spouse > 0:
        raise InputError("Spouse income only applies when filing jointly.")
    k401 = check_number("401(k) pre-tax contributions", pretax_401k, 0)
    hsa = check_number("HSA payroll contributions", hsa, 0)
    fsa = check_number("FSA contributions", fsa, 0)
    premiums = check_number("Health premiums", premiums, 0)
    children = int(check_number("Children under 17", children, 0, maximum=15))
    total_gross = gross + spouse
    cafeteria = hsa + fsa + premiums
    if k401 + cafeteria > total_gross:
        raise InputError("Pre-tax deductions are larger than total pay.")

    fed_taxable = max(0.0, total_gross - k401 - cafeteria - FED_STANDARD_DEDUCTION[status])
    fed_before_credits = progressive_tax(fed_taxable, FED_BRACKETS[status])
    ctc = child_tax_credit(children, total_gross - k401 - cafeteria, status)
    federal = max(0.0, fed_before_credits - ctc)

    fica_wages = [max(0.0, gross - cafeteria), spouse]
    social_security = sum(SS_RATE * min(w, SS_WAGE_BASE) for w in fica_wages)
    medicare_wages = sum(fica_wages)
    medicare = (MEDICARE_RATE * medicare_wages
                + ADDL_MEDICARE_RATE * max(0.0, medicare_wages - ADDL_MEDICARE_THRESHOLD[status]))

    ca = sdi = 0.0
    ca_taxable = 0.0
    if california:
        ca_taxable = max(0.0, total_gross - k401 - (cafeteria - hsa) - CA_STANDARD_DEDUCTION[status])
        ca = progressive_tax(ca_taxable, CA_BRACKETS[status])
        ca += CA_MENTAL_HEALTH_RATE * max(0.0, ca_taxable - CA_MENTAL_HEALTH_THRESHOLD)
        sdi = CA_SDI_RATE * medicare_wages

    taxes = federal + social_security + medicare + ca + sdi
    net = total_gross - k401 - cafeteria - taxes
    return {
        "Gross pay": total_gross,
        "Pre-tax deductions": k401 + cafeteria,
        "Federal income tax": federal,
        "Child tax credit used": min(ctc, fed_before_credits),
        "Social Security": social_security,
        "Medicare": medicare,
        "California income tax": ca,
        "CA SDI": sdi,
        "Total taxes": taxes,
        "Take-home pay": net,
        "Federal taxable income": fed_taxable,
        "California taxable income": ca_taxable,
        "Federal marginal rate": marginal_rate(fed_taxable, FED_BRACKETS[status]),
        "California marginal rate": marginal_rate(ca_taxable, CA_BRACKETS[status]) if california else 0.0,
        "Effective tax rate": taxes / total_gross if total_gross > 0 else 0.0,
    }
