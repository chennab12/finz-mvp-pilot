# FinLife 360 — Best-of-Best Features and Consolidation Strategy

Audit date: 2026-10-19. Builds on FEATURE_COMPARISON.md (row numbers in brackets refer to its matrix). Tags: **[V]** verified, **[A]** assumed, **[NI]** not inspected.

## 1. The 20% that gives 80% of the value

A household gets most of its practical value from four questions: *Where did my money go? What is due next? Am I on track? What should I do next?* These 12 features answer them, and all but two already exist in good shape.

| # | Feature | Answers | Source | Strategy |
|---|---|---|---|---|
| 1 | Transaction import, categorization, duplicate/transfer cleanup | Where did my money go? | FAP | Reuse directly |
| 2 | Dashboard: income, spending, surplus, category and monthly charts, rule-based insights | Where did my money go? | FAP | Reuse with modifications (add net-worth tile) |
| 3 | Budgets and budget vs actual | Am I on track? | FAP | Reuse directly |
| 4 | Recurring bills with Paid roll-forward + Upcoming/Overdue organizer (loans, insurance, subscriptions, documents) | What is due next? | FAP (+ LAP records) | Merge |
| 5 | Savings goals + cash-flow projection | Am I on track? | FAP | Reuse directly |
| 6 | Net-worth log over time | Am I on track? | SRF | Reuse with modifications (Plotly trend, loan balances from organizer) |
| 7 | Emergency-fund check using real average spending | Am I safe? | FFQ + FAP | Merge |
| 8 | Debt payoff (avalanche vs snowball) | What should I do next? | FAP | Reuse with modifications (fix duplicate-name bug [V]) |
| 9 | Loan/mortgage amortization with extra payment + refinance | What should I do next? | FAP + HAF | Merge |
| 10 | Household tax & take-home estimator (fed + CA + FICA, year-keyed) | How much do I keep? | MYB + SRF + TAX | Merge |
| 11 | Money checkup ladder (what to fund next: match, high-APR debt, emergency fund, HSA, 401(k)…) | What should I do next? | SRF | Reuse with modifications (pre-fill from data) |
| 12 | One JSON backup/restore for everything | Will I lose my data? | FAP | Reuse with modifications |

Everything else (retirement depth, equity comp, insurance, home/rental, learning, quizzes) is valuable but secondary and comes after the core works.

## 2. Classification of every feature

### Reuse directly (copy the module, adjust imports and tests)
- Transaction CSV import + mapping, category rules, duplicate/transfer flags, monthly summaries, export — FAP `transactions.py` [V]
- Budgets, bills, goals, cash-flow projection, upcoming items — FAP `planning.py` [V]
- Loan payment and amortization schedule — FAP `finance.py` [V]
- Savings goal (required monthly / months to goal), subscription annual cost — FAP [V]
- Rule-based insights — FAP `insights.py` [V]
- Plotly theme helper `style_fig` — FAP [V]
- 401(k) match & limits, Roth vs traditional, FI number, years-to-FI, money lasts, Social Security factor and break-even, rebalance, 529 plan — SRF `calculations.py` [V]
- Concentration with drop scenario — SRF [V]
- Refinance break-even — HAF [V]
- `.ics` calendar export — HAF `calendar_ics` [V]
- Allowed-domain test for source links — SRF/MYB pattern [V]

### Reuse with modifications
- Debt payoff — FAP; key debts by row id (bug [V]); add FFQ's "+$X/month" comparison.
- JSON storage — FAP; extend schema to net-worth log, tax profile, household records; add `schema_version`.
- Dashboard — FAP; add net-worth and emergency-fund tiles.
- Net-worth log — SRF; Plotly trend, categories (cash, investments, retirement, home, loans).
- Money checkup ladder — SRF; read inputs from the user's data instead of re-asking.
- Tax filing checklist and deadline center — TAX; parameterize the tax year, rewrite the dense one-line code into readable functions, add tests.
- Deduction comparison and payment reconciliation — TAX; move into the tax page.
- RSU withholding gap — MYB; get marginal rates from the merged tax engine.
- Health plan compare — MYB; remove Intel-specific labels.
- Household records (home, vehicle, purchases, warranties) and renewals → task — LAP; merge into the FAP organizer.
- Bill/plan and repair-quote comparison — LAP; extract from the 61 KB single file.
- Document date/amount extraction — LAP; output a bill or organizer item.
- Home property tax (Prop 13), rental cash flow, depreciation, sale gain — HAF; optional "Home & rental" page.
- Learning content — SRF structure; seed with FFQ's 17 lessons and TAX topics; remove overlap.

### Merge multiple implementations
- Compound growth + fees + inflation — FFQ (chart/UX) + STK (multiplicative fee) + FAP (validation). Pick one compounding convention; today's apps differ by ≈2.9% over 20 years [V].
- Emergency fund — FFQ (gap + progress) + FAP (average of complete months).
- Household tax engine — MYB (payroll/cafeteria treatment, $1M supplemental, CTC) + SRF (two earners, RSU, itemized, CA surcharge) + TAX (all filing statuses, bracket breakdown, CTC phaseout). One constants file per tax year; resolve the CA standard deduction mismatch (11,400 vs 11,412 [V]) against the FTB table.
- ESPP — SRF (ordinary-income split) + MYB (zero-input guards).
- Life insurance need — SRF + MYB (same formula; keep MYB's separate mortgage input).
- Loan tools — FAP (schedule) + HAF (refinance).
- Organizer — FAP organizer + LAP household records and tasks.
- Calendar export — HAF + MYB.

### Rewrite
- Recurring-charge / subscription detection — AUD's rules (keyword or amount < $50; "price hike" = amount > $15 [V]) do not detect recurrence. Rewrite as a deterministic rule over imported transactions: normalized merchant, ≥3 occurrences, amount within ±10%, spacing ≈ 7/30/91/365 days; flag a price change when the latest amount exceeds the median by > 5%.
- Tax constants — rewrite into one year-keyed data module with tests at every bracket boundary (TAX already has boundary tests in spirit; SRF/MYB have some).

### Remove (do not migrate)
- AUD "LLM Agentic Mode" with an OpenAI key field that is never used [V] (and conflicts with the no-paid-API rule).
- AUD flat "30% savings potential" figure [V].
- MYB Google News headlines (not money admin; network-dependent).
- HAF niche calculators: solar payback, leak cost, rent-increase cap, deposit rules — keep them in home-admin-faqs and link out.
- STK valuation ratios, drawdown, stress test — educational, low daily value (could return in P3).
- IND India-specific calculators — keep India Finance Compass as its own app; revisit as a locale pack later.
- home-mgmt-faqs tracker — superseded by HAF/LAP.
- Duplicate copies of `visuals.py` stage diagrams outside the Learn section.

### Add as a new feature (no good existing implementation)
1. **Recurring-charge detection** (see Rewrite) feeding the subscription tracker. P1.
2. **Local, free "smart categorization"**: learn keyword rules from the user's own manual corrections (most-frequent category per normalized merchant). Pure Python, no model download, no API. P1.
3. **Net worth assembled from data**: loan balances from the organizer + latest account balances. P1.
4. **Annual money review**: one page that pulls budget variance, emergency-fund months, debt-free date, savings rate, net-worth change, tax-year checklist status. P2.
5. **Optional local persistence**: when run on the user's own computer, auto-save the JSON backup to a local file (`FINLIFE_DATA_DIR`), so nothing is lost on refresh. Still no DB server, no login. P2.
6. **Credit card utilization tracker** (balance ÷ limit per card from the organizer), since credit cards are in scope but no app tracks utilization. P2.

## 3. Financial categories coverage after consolidation

| Category the user listed | Covered by | Gap after consolidation |
|---|---|---|
| Personal finance / household management | FAP core + LAP records | — |
| Budgeting | FAP | — |
| Banking | FAP import, transfer detection | No live bank sync (by design: no paid APIs, no credentials) |
| Savings | FAP goals, FFQ/FAP emergency fund | — |
| Debt | FAP payoff + organizer loans | — |
| Credit cards | FAP (card payments excluded correctly) | Utilization tracker is new (P2) |
| Mortgages | FAP amortization + HAF refinance, Prop 13 | — |
| Taxes | Merged tax engine + TAX checklist | Only federal + California |
| Investments | Growth, fees, rebalance, concentration, ESPP/RSU | No holdings import or prices (by design) |
| Retirement | SRF suite | — |
| Insurance | Life need, health plan compare, renewal tracker, rebuild gap | No auto/umbrella calculators |
| Financial calculators | ≈25 consolidated | — |
| Financial education | Learn hub | finz-learner content unknown [NI] |
