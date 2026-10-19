# FinLife 360 — Application Inventory

Audit date: 2026-10-19. Audit only: no existing app was changed and no new application code was written.

## How to read this document

| Tag | Meaning |
|---|---|
| **[V]** Verified | Read in the source code, and/or seen running in a Streamlit `AppTest` / pytest run during this audit. |
| **[A]** Assumed | Inferred (for example, which repo a live URL is built from). Not confirmed. |
| **[NI]** Not inspected | Could not be reached from the audit environment. Nothing about it is claimed. |

### What was accessible

| Source the user named | Result |
|---|---|
| https://finance-faqs.streamlit.app/ | Live site **blocked** by the audit sandbox's network proxy (connection rejected). Source repo `chennab12/finance-faqs` read instead. Repo-to-URL link **[V]** from project memory and the repo's own catalog entry. |
| https://taxes-faqs.streamlit.app/ | Live site **blocked**. Repo `chennab12/taxes-faqs` read. URL-to-repo link **[A]** (same name). |
| https://finz-app-pilot.streamlit.app/ | Live site **blocked**. **No repo named `finz-app-pilot` exists in the account.** The closest match is `chennab12/finz-admin-pilot` (Personal Money Admin Copilot) **[A]**. Also found: `chennab12/finz-mvp-pilot`, which is **empty** (no commits on any branch) as of this audit **[V]**. |
| https://github.com/chennab12/life-admin-pilot | Repo read **[V]**. |
| https://finz-learner.streamlit.app/ | Live site **blocked**. Repo `chennab12/finz-learner` is referenced in `master-aio-FAQs/catalog.json` but **is not accessible**: GitHub returns "not found or no access" **[V]**. **[NI]** |
| https://ai-finz-auditor.streamlit.app/ | Live site **blocked**. No repo by that name. Closest match `chennab12/ai-financial-auditor` read **[A]** for the URL link. |

Live sites could not be opened, so **no claim in these documents is based on a running deployment**. "Seen running" means run locally in the audit sandbox with Streamlit 1.66 `AppTest`.

### Other finance-relevant repos found in the account (and included)

`stocks-retire-faqs`, `stocks-faqs`, `intel-myben`, `home-admin-faqs`, `india-finz-faqs`, `home-mgmt-faqs`. Reviewed and **excluded** as not finance-core: `diary-faqs` (journal → tasks; reused only as a pattern for `.ics` export), `health-admin-pilot`, `seniors-news` (has a bills topic and scam checker, Hyderabad audience), `master-aio-FAQs` (a catalog/portal of other apps, no finance logic).

### Test and smoke-run results (run during this audit) [V]

| Repo | Automated tests | Result |
|---|---|---|
| finz-admin-pilot | 59 pytest (incl. AppTest) | 59 passed |
| stocks-retire-faqs | 29 pytest | 29 passed |
| home-admin-faqs | 32 pytest | 32 passed |
| intel-myben | 24 pytest | 24 passed |
| finance-faqs | 14 pytest | 14 passed |
| taxes-faqs, stocks-faqs, india-finz-faqs, life-admin-pilot, ai-financial-auditor, home-mgmt-faqs | none in repo | AppTest first render: 0 exceptions each |

---

## 1. Finz Admin Pilot — "Personal Money Admin Copilot"

Repo `chennab12/finz-admin-pilot` (1 commit, 9661e0a, 2026-10-18). Possibly the app at finz-app-pilot.streamlit.app **[A]**.

| Field | Finding |
|---|---|
| Main purpose | Day-to-day money admin: import transactions, categorize, budget, bills, goals, calculators, financial organizer. **[V]** |
| Modules | `app.py` (UI, 5 tabs), `finance.py` (loan/debt/savings math with `InputError` validation), `transactions.py` (CSV mapping, rules, duplicate/transfer flags, summaries), `planning.py` (bills, goals, cash-flow projection, upcoming items), `insights.py` (rule-based insights), `storage.py` (schema, coercion, JSON backup, sample data). **[V]** |
| Calculators | Loan payment + amortization with extra payment (months/interest saved); multi-debt payoff **Avalanche vs Snowball**; savings goal (required monthly / months to goal); compound growth; emergency-fund coverage; subscription annual cost. Handles 0% interest exactly, caps at 50 years. **[V]** |
| Charts | 12 Plotly figures: spending by category, income vs spending by month, budget vs actual, cash-flow projection, amortization, payoff by debt, growth, subscriptions (horizontal bar). Shared `style_fig` theme. **[V]** |
| Tables | Editable `data_editor` tables for transactions, rules, budgets, bills, goals, loans, insurance, reimbursements, subscriptions, documents, tasks; each chart has a matching table. **[V]** |
| Productivity | CSV import with column mapping (single amount or debit/credit, flip sign, day-first dates), keyword category rules, duplicate & transfer-pair flags with one-click fix, bills with **Paid** roll-forward, goals with deadline status, Upcoming/Overdue list, CSV export, sample-data loader with banner. **[V]** |
| AI/ML | None. Explicitly "rule-based, no live AI"; insights show the rule that fired. **[V]** |
| Storage | Streamlit session state only; versioned JSON backup/restore with per-field coercion; transactions CSV export. No DB, no keys. **[V]** |
| Missing | No persistence beyond manual JSON; no recurring-charge detection from transactions; no net-worth over time; no tax, investing, retirement or insurance-adequacy features; single currency. **[V]** (absence confirmed by reading code) |
| Defect found | `payoff_plan` keys debts by name, so **two debts with the same name are merged** (e.g., two rows named "Card": 19 months/$406 interest reported vs 23 months/$622 when renamed). **[V]** reproduced. |

## 2. Finance FAQs — "Finance & Wealth Compass"

Repo `chennab12/finance-faqs` (main at a98692d, PR #1 merged). Live at finance-faqs.streamlit.app **[V via memory/catalog]**, live page itself **[NI]**.

| Field | Finding |
|---|---|
| Main purpose | US personal-finance learning hub. **[V]** |
| Modules | `app.py` (sidebar radio, one section rendered per run), `content.py` (17 lessons, cheatsheet, sources), `calculations.py`, `visuals.py` (animated stage diagram). **[V]** |
| Calculators | Cash flow & net worth; emergency reserve (months covered, gap, progress to target); debt payoff (single debt, extra payment comparison); compound growth with fee & inflation; single-stock concentration. **[V]** |
| Charts | `st.line_chart` for debt balance and growth (before/after fee, contributed). HTML stage visuals per lesson. **[V]** |
| Tables | Master cheatsheet, sources table. **[V]** |
| Productivity | "Mark lesson understood" progress bar. **[V]** |
| AI/ML | None. **[V]** |
| Storage | Session only. **[V]** |
| Missing | No transactions, budgets, taxes calculator, retirement planning. An unmerged PR #2 adds Cloud Run deployment (memory) **[A]**. |

## 3. Taxes FAQs — "Tax Filing Compass" (2025 tax year, Federal + California)

Repo `chennab12/taxes-faqs` (2 commits, last 283c60f 2026-10-02).

| Field | Finding |
|---|---|
| Main purpose | Organize and explain filing a 2025 federal + CA return by Oct 15, 2026. **[V]** |
| Modules | `app.py` (16 tabs), `content.py` (12 topics, 24-item checklist, 11 filing steps, 12 mistakes, missed items, myths, escalation, 34 official sources), `calculations.py`, `tools.py` (6 tools), `review.py` (final cross-check, CTC phaseout screen, two-earner example). **[V]** |
| Calculators | 2025 ordinary-income bracket tax for **all 4 filing statuses** with per-bracket breakdown; standard vs itemized comparison (medical 7.5% AGI floor); payment reconciliation; capital-gain arithmetic; rental result before limits; filing readiness %. **[V]** |
| Charts | `st.bar_chart` (tax per bracket, deduction comparison), Graphviz income-to-filing flow. **[V]** |
| Tables | Bracket table by status, editable checklist with status select, mistakes/myths/escalation tables, reconciliation ledger. **[V]** |
| Productivity | Days-to-deadline metric, checklist progress, JSON progress save/restore, CSV export. **[V]** |
| AI/ML | None. **[V]** |
| Storage | Session; checklist JSON download/upload. **[V]** |
| Missing | No tests, no CI; 2025-only constants (no year switch); no state other than CA; dense one-line code style (hard to maintain). **[V]** |
| Accuracy | 2025 brackets and standard deductions ($31,500 MFJ etc.) match the post-2025-law IRS figures to the auditor's knowledge **[A — not live-checked against irs.gov from this sandbox]**. |

## 4. Life Admin Pilot — "Family Life Admin Copilot"

Repo `chennab12/life-admin-pilot` (3789974, 2026-10-18). **[V]**

| Field | Finding |
|---|---|
| Main purpose | Household paperwork: bills, deadlines, maintenance, documents, records. **[V]** |
| Modules | Single 61 KB `app.py`: tasks with repeats, regex date/amount extraction, PDF text via `pypdf`, bill/quote comparison, household records, reminders, JSON import/export. **[V]** |
| Calculators | Compare two bills/plans over N months (monthly price, fees, promos, setup); compare two repair quotes (line items, tax, discount, warranty, cost per warranty year). **[V]** |
| Charts | None (metrics and tables). **[V]** |
| Tables | Editable tasks and records; line-by-line quote diff. **[V]** |
| Productivity | Overdue/upcoming dashboard, recurring tasks auto-advance, document → task, renewals in next 90 days → task. **[V]** |
| AI/ML | None; rule-based extraction labeled "Demo, no live AI". No OCR. **[V]** |
| Storage | Session + JSON backup/restore. **[V]** |
| Missing | No tests or CI in repo; single-file structure; no money totals across bills. **[V]** |

## 5. AI Financial Auditor (probable source of ai-finz-auditor.streamlit.app [A])

Repo `chennab12/ai-financial-auditor` (2 commits, 2026-10-05). One 5 KB `app.py`. **[V]**

| Field | Finding |
|---|---|
| Main purpose | Upload a bank CSV, detect subscriptions, show savings and cancellation scripts. **[V]** |
| Calculators / logic | A row is a "subscription" if its description has one of 9 keywords **or the amount is under $50**; "price hike detected" is simply `amount > $15`; "annual savings potential" is a flat 30% of the total. **[V]** These rules do not detect recurrence or price changes. |
| Charts | None (metrics + table). `plotly` is in requirements but unused. **[V]** |
| Productivity | Per-merchant cancellation email template. **[V]** |
| AI/ML | Labeled "multi-agent" and has an "LLM mode" that asks for an **OpenAI key, which is never used**; Pydantic models are defined but unused. Effectively no AI. **[V]** |
| Storage | None. **[V]** |
| Missing | Real recurrence detection, date handling, tests. Requests a paid-API key (conflicts with the no-paid-API rule). **[V]** |

## 6. Finz Learner (finz-learner.streamlit.app) — **[NI]**

Repo `chennab12/finz-learner` is not visible to the audit's GitHub access, and the live site is blocked. The only evidence is a catalog entry in `master-aio-FAQs/catalog.json` describing it as a "Financial Learning Agent", itself marked "internal pages not fully verified". **Access needed:** add `finz-learner` to the Claude GitHub app's repositories (or share where its code lives). Nothing about its features is claimed here.

## 7. Stocks & Retirement FAQs

Repo `chennab12/stocks-retire-faqs` (6be3f86, 2026-10-15). **[V]**

| Field | Finding |
|---|---|
| Main purpose | Investing, taxes, RSUs and retirement for a California tech family. **[V]** |
| Modules | `app.py`, `calculations.py` (2026 limits/brackets), 4 topic modules (14 categories / 43 topics / 86 quiz questions), `content.py` (sources with allowed-domain test, key numbers, 12-week plan, red flags). **[V]** |
| Calculators (16) | Compound growth, retirement (FI) number, retirement projection, 401(k) match & max (age-based catch-up incl. 60–63), Roth vs traditional, tax bracket estimator (2026 fed + CA + FICA + SDI, two earners), RSU tax gap, ESPP return, concentration (with drop scenario and amount to sell to reach 10%), allocation & rebalance, fee drag, 529 college, emergency fund, Social Security claiming (factor + break-even), how long money lasts, life insurance need. **[V]** |
| Charts | line/bar/area charts (growth by year, fee drag, SS break-even, etc.). **[V]** |
| Tables | Mistakes tables, key numbers, net-worth log with totals, CSV downloads. **[V]** |
| Productivity | Money checkup "ladder" (what to fund next), year planner/milestones by age, net-worth log (CSV in/out), quiz center, search, progress JSON. **[V]** |
| AI/ML | None. **[V]** |
| Storage | Session + CSV/JSON download/upload. **[V]** |
| Missing | No transactions or budgets; MFJ-only tax tables; CA brackets are an approximation (its own docstring says so). **[V]** |

## 8. Stocks FAQs — "Stocks & Investing Compass"

Repo `chennab12/stocks-faqs` (7de8e37, 2026-10-01). README calls it a "replacement for the nutrition app's content", so its live URL is unknown **[A]**.

| Field | Finding |
|---|---|
| Purpose | 16 investing lessons + cheatsheet. **[V]** |
| Calculators (7 modes) | Compound growth & fee drag (multiplicative fee), monthly saving for goal, valuation ratios (P/E, yield), drawdown & recovery, rebalance planner, portfolio stress test, ESPP discount. **[V]** |
| Charts / tables | line + bar charts; cheatsheet, compare-approaches table, research & SMART-goal worksheet with download. **[V]** |
| AI / storage | None / session + downloads. **[V]** |
| Missing | No tests/CI; deprecated `use_container_width` warning. **[V]** |

## 9. Intel MyBen

Repo `chennab12/intel-myben` (fba0fa8). Live at intel-myben.streamlit.app per memory **[A]**.

| Field | Finding |
|---|---|
| Purpose | Benefits & life hub for an Intel TPM family in California. **[V]** |
| Calculators (11) | Take-home pay (2026 fed + CA + FICA + SDI, 401k/HSA/FSA/premium treatment incl. CA taxing HSA, child tax credit), RSU withholding gap (handles $1M supplemental threshold), ESPP purchase, account-limit gaps, emergency fund, life insurance, college, retirement, mortgage, concentration, health-plan compare (premium + deductible + coinsurance + OOP max + employer HSA, with chart), net worth. **[V]** |
| Charts | Spec-driven chart helper (`insights.py`: bar/line per topic), plan-compare chart. **[V]** |
| Productivity | Editable benefits sheet (CSV in/out), year planner with `.ics` export, family emergency card, annual life review score, Google News RSS headlines. **[V]** |
| AI / storage | None (RSS summarizer is sentence truncation) / session + CSV. **[V]** |
| Missing | Single earner in take-home; CTC has no income phaseout **[V]**. Intel-specific plan facts left as "check" items. |

## 10. Home Admin FAQs

Repo `chennab12/home-admin-faqs` (0d1d8f2). **[V]**

| Field | Finding |
|---|---|
| Purpose | Rental condo (Sunnyvale) + primary home (Santa Clara) management. **[V]** |
| Calculators (14) | Rental cash flow, CA rent-increase cap (AB 1482), deposit max/return deadline, mortgage + amortization with extra, **refinance break-even**, Prop 13 property tax + supplemental, rental depreciation, sale gain (exclusion, recapture), maintenance budget, insurance rebuild gap & earthquake deductible, manager vs self-manage, solar payback, leak cost, reserves. **[V]** |
| Charts / tables | line/bar charts; "My two homes" numbers sheet, expense & repair log, binder checklist. **[V]** |
| Productivity | Year calendar with `.ics` export, 12-week plan, quiz, search, progress JSON. **[V]** |
| AI / storage | None / session + CSV/JSON. **[V]** |

## 11. India Finz FAQs — "India Finance Compass"

Repo `chennab12/india-finz-faqs` (4450d2c). INR/lakh formatting, 19 topics, 8 calculators (budget & runway, SIP scenarios, inflation goal, EMI & prepayment, net worth & employer stock, life cover, FD after-tax, DICGC ceiling), monthly checklist. No tests. **[V]** India-specific; out of scope for a US core (see strategy).

## 12. Home Mgmt FAQs (older)

Repo `chennab12/home-mgmt-faqs` (dc1b88c, 2026-09-29). Maintenance FAQs + a CSV tracker. Superseded by home-admin-faqs; uses deprecated `st.components.v1.html`. **[V]**

---

## Cross-cutting observations [V]

1. **Same logic re-implemented many times:** compound growth (6 apps), emergency fund (5), loan/mortgage payment (4), concentration (4), ESPP (3), RSU gap (2), life insurance (3), federal/CA tax (3), `visuals.py` stage diagram (copied in most apps).
2. **Conventions disagree.** Growth: `finance-faqs` converts the annual rate to an effective monthly rate; `stocks-retire-faqs` uses nominal rate ÷ 12. Same inputs ($10k + $500/mo, 7%, 20 yrs) give **$292,465 vs $300,851** (≈2.9% apart). Fees are subtracted in one app and multiplicative in another.
3. **Tax constants are duplicated and drift:** CA MFJ standard deduction is `11_400` in stocks-retire-faqs and `11_412` in intel-myben. taxes-faqs is 2025-only; the others are 2026.
4. **Code quality ranges widely:** finz-admin-pilot (typed, validated, 59 tests) vs taxes-faqs/stocks-faqs/india-finz-faqs (semicolon one-liners, no tests).
5. **No app uses a paid API at runtime** except the unused OpenAI key field in ai-financial-auditor. diary-faqs (non-finance) optionally calls the Anthropic API and falls back to rules.
