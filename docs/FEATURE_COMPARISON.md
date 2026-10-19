# FinLife 360 — Feature Comparison

Audit date: 2026-10-19. Tags: **[V]** verified in code or a local run, **[A]** assumed, **[NI]** not inspected. See APP_INVENTORY.md for access limits (no live site could be opened; `finz-learner` code is not accessible and is excluded from every comparison below).

App short names: **FAP** finz-admin-pilot · **FFQ** finance-faqs · **TAX** taxes-faqs · **LAP** life-admin-pilot · **AUD** ai-financial-auditor · **SRF** stocks-retire-faqs · **STK** stocks-faqs · **MYB** intel-myben · **HAF** home-admin-faqs · **IND** india-finz-faqs.

Quality scale (implementation quality): ★★★★★ tested, validated, edge cases handled · ★★★★ correct and clear, minor gaps · ★★★ works, simplified · ★★ partial or misleading · ★ placeholder.

---

## Part A — Head-to-head comparisons of duplicated features

### A1. Compound growth / investment projection
| App | Method | Extras | Quality |
|---|---|---|---|
| FFQ | annual → effective monthly rate, end-of-month deposits; fee = return − fee | before/after fee, inflation-adjusted, contributed line | ★★★★ [V] |
| SRF | nominal annual ÷ 12, closed form | growth by year, separate fee-drag calculator, rule of 72, real rate | ★★★★ [V] |
| STK | effective monthly, fee multiplicative `(1+r)(1−f)−1` | no-fee vs fee chart | ★★★ [V] |
| FAP | monthly loop with validation | chart + table | ★★★★ [V] |
| MYB, IND | effective monthly loop | — | ★★★ [V] |

**Best: FFQ's chart/UX + FAP's validation, one convention.** Same inputs give $292,465 (FFQ) vs $300,851 (SRF) **[V]**, so the merged engine must pick and document one convention. Recommend the effective-annual convention (matches how fund returns are quoted) and STK's multiplicative fee, with a visible "assumptions" note.

### A2. Loan / mortgage payment and amortization
| App | Coverage | Quality |
|---|---|---|
| FAP | payment, full monthly schedule, extra payment, months & interest saved, final payment trimmed, 0% exact, input errors | ★★★★★ [V] |
| HAF | payment, yearly balances with extra, **refinance break-even**, interest change incl. closing costs | ★★★★ [V] |
| MYB | payment only | ★★★ [V] |
| IND | EMI + lump-sum prepayment | ★★★ [V] (INR) |

**Best: FAP schedule + HAF refinance.** FAP is the most robust and tested; HAF adds the only refinance analysis.

### A3. Debt payoff
| App | Coverage | Quality |
|---|---|---|
| FAP | many debts, avalanche vs snowball, minimums, rollover, never-pays-off warnings, per-debt payoff month, chart | ★★★★ [V] — duplicate-name bug [V] |
| FFQ | one debt, extra-payment comparison, balance chart | ★★★ [V] |

**Best: FAP**, after fixing the duplicate-name merge (key by row id, not name).

### A4. Emergency fund
FFQ (months covered, gap to target, progress bar) ★★★★ · FAP (coverage from actual average spend of complete months) ★★★★ · SRF/MYB (target = essentials × months) ★★★ · IND (runway) ★★★. **[V]**
**Best: merge FFQ UI with FAP's "use my real average spending" input.**

### A5. Income tax / take-home
| App | Year | Scope | Quality |
|---|---|---|---|
| TAX | 2025 | Federal only, **all 4 filing statuses**, bracket breakdown, deduction compare, payment reconciliation, CTC phaseout screen | ★★★★ [V] |
| MYB | 2026 | Fed + CA + FICA + SDI, one earner, 401k vs cafeteria-plan FICA treatment, CA taxes HSA, CTC (no phaseout), $1M supplemental rule | ★★★★ [V] |
| SRF | 2026 | Fed + CA + FICA + SDI, **two earners**, RSU income, itemized override, CA mental-health surcharge; HSA not FICA-exempt; no CTC | ★★★★ [V] |

Constants drift: CA standard deduction 11,400 (SRF) vs 11,412 (MYB) **[V]**. **Best: merge.** One `tax` engine with year-keyed tables (2025, 2026), TAX's filing-status coverage, MYB's payroll treatment, SRF's two-earner/RSU support, and TAX's CTC phaseout.

### A6. RSU withholding gap / ESPP / concentration
- RSU gap: MYB handles the $1M supplemental 37% tier and YTD; SRF does not. **Best: MYB** [V].
- ESPP: SRF also returns ordinary-income portion on quick sale; MYB returns market value/gain. **Best: merge** (SRF's tax split + MYB's guard for zero inputs) [V].
- Concentration: SRF adds drop scenario and "amount to sell to get to 10%". **Best: SRF** [V].

### A7. Retirement planning
Only SRF has FI number, years-to-FI, money-lasts, 401(k) match & limits by age, Roth vs traditional, Social Security claiming. MYB has a simpler retirement projection. **Best: SRF** [V].

### A8. Net worth
FFQ snapshot ★★ · MYB snapshot calculator ★★★ · SRF **dated net-worth log with totals and CSV** ★★★★ · IND snapshot. **Best: SRF log**, later fed from FAP accounts [V].

### A9. Bills, reminders and renewals
FAP bills with frequencies + Paid roll-forward + Upcoming/Overdue across loans/insurance/subscriptions/documents ★★★★★ · LAP tasks with repeats, renewals within 90 days → task ★★★★ · HAF/MYB year calendars with `.ics` export ★★★★ [V]. **Best: FAP organizer + `.ics` export from HAF/MYB.**

### A10. Subscriptions
FAP: editable subscription list → annual cost chart ★★★★ [V]. AUD: "detection" = keyword OR amount < $50, "price hike" = amount > $15 ★ [V, misleading]. **Best: FAP; rewrite detection** as a recurrence rule over imported transactions (same normalized merchant, similar amount, ~monthly/annual spacing).

### A11. Insurance
SRF + MYB life-insurance need (same formula; MYB also separates mortgage) ★★★ · MYB health-plan compare with chart ★★★★ · HAF homeowners rebuild gap and earthquake deductible ★★★ · FAP insurance renewal tracker ★★★★ [V]. **Best: MYB plan compare + SRF/MYB life need (merge) + FAP tracker.**

### A12. Document capture
LAP regex extraction of dates and $ amounts from pasted text or text PDFs, suggested due date/amount/type, correct-before-save ★★★★ [V]. Only source. **Reuse with modifications** (create a bill or organizer item, not just a task).

### A13. Learning content
FFQ 17 lessons ★★★★ · SRF 43 topics + 86 quiz ★★★★ · TAX 12 topics + filing checklist ★★★★ · STK 16 lessons ★★★ · HAF 45 home topics ★★★★ · MYB 19 life topics ★★★ · IND 19 India topics. [V] Heavy overlap in basics (budget, emergency fund, debt, investing). **Best: SRF structure (topics + quiz + search) seeded with FFQ basics and TAX checklist.**

### A14. Data persistence
FAP versioned JSON backup with per-field coercion and error list ★★★★★ · LAP JSON with cleaning ★★★★ · SRF/HAF/TAX progress JSON ★★★ · others none [V]. **Best: FAP storage module** extended to all FinLife sections.

### A15. Charts and visual quality
FAP Plotly with shared theme, every chart paired with a table ★★★★★ · MYB spec-driven chart helper ★★★★ · others Streamlit native charts ★★★ [V]. **Best: FAP `style_fig` + MYB's spec approach** for content-page charts.

### A16. Code quality and maintainability
FAP (typed functions, dataclasses, `InputError`, 59 tests) > SRF ≈ HAF ≈ MYB (clean modules, 24–32 tests) > FFQ (small, 14 tests) > LAP (single 61 KB file, no tests) > TAX ≈ STK ≈ IND (dense one-liners, no tests) > AUD (unused code paths) [V].

---

## Part B — Master comparison matrix

Migration complexity: **L** low (copy + adapt imports) · **M** medium (merge or refactor) · **H** high (rewrite / new design). Priority: **P0** MVP core · **P1** next · **P2** later · **P3** optional.

| # | Feature | Existing in | Quality (best) | Best source | Reason for selection | Recommended improvements | Migration | Priority |
|---|---|---|---|---|---|---|---|---|
| 1 | Transaction CSV import + column mapping | FAP, AUD | ★★★★★ | FAP | Debit/credit, sign flip, date order, preview; tested | Save mapping presets per bank | L | P0 |
| 2 | Category rules + manual correction | FAP | ★★★★★ | FAP | Word-start matching, manual edits preserved | Learn rules from corrections (local, see Best-of-Best) | L | P0 |
| 3 | Duplicate / transfer detection | FAP | ★★★★★ | FAP | Prevents double counting | none | L | P0 |
| 4 | Dashboard (income, spend, surplus, by category, by month) | FAP | ★★★★★ | FAP | Plotly + tables, excludes transfers | Add net-worth tile | L | P0 |
| 5 | Monthly budgets, budget vs actual | FAP | ★★★★ | FAP | Only implementation | Rollover option | L | P0 |
| 6 | Recurring bills + Paid roll-forward | FAP, LAP | ★★★★★ | FAP | Frequencies + roll-forward | `.ics` export (HAF/MYB) | L | P0 |
| 7 | Savings goals + cash-flow projection | FAP | ★★★★ | FAP | Deadline status, assumptions table | none | L | P0 |
| 8 | JSON backup / restore | FAP, LAP, SRF, TAX, HAF | ★★★★★ | FAP | Versioned schema, coercion, error list | One file for all sections; schema version field | M | P0 |
| 9 | Loan / mortgage amortization + extra payment | FAP, HAF, MYB, IND | ★★★★★ | FAP | Validated, full schedule, tests | Add HAF refinance | L | P0 |
| 10 | Refinance break-even | HAF | ★★★★ | HAF | Only one | Port into FAP-style validation | L | P1 |
| 11 | Debt payoff avalanche/snowball | FAP, FFQ | ★★★★ | FAP | Multi-debt, warnings | **Fix duplicate-name bug**; add FFQ "extra payment" compare | L | P0 |
| 12 | Emergency fund | FFQ, FAP, SRF, MYB, IND | ★★★★ | Merge FFQ + FAP | FFQ gap/progress UI; FAP real average spend | Pull essentials from budgets | L | P0 |
| 13 | Compound growth + fee + inflation | FFQ, SRF, STK, FAP, MYB, IND | ★★★★ | Merge FFQ + STK + FAP | Best chart, multiplicative fee, validation | One documented compounding convention | M | P0 |
| 14 | Household tax / take-home (fed + CA + FICA) | TAX, MYB, SRF | ★★★★ | Merge MYB + SRF + TAX | Payroll accuracy + two earners + all statuses | Year-keyed tables, CTC phaseout, one CA constant set, tests at bracket edges | M | P0 |
| 15 | Tax filing checklist + deadlines | TAX | ★★★★ | TAX | 24 items, statuses, JSON progress | Year parameter, tests, readable code | M | P1 |
| 16 | Deduction compare / payment reconciliation | TAX | ★★★★ | TAX | Only source | Fold into tax page | L | P1 |
| 17 | RSU withholding gap | MYB, SRF | ★★★★ | MYB | $1M supplemental tier | Use household tax engine for marginal rates | L | P1 |
| 18 | ESPP | SRF, MYB, STK | ★★★★ | Merge SRF + MYB | Tax split + guards | Qualifying vs disqualifying note | L | P1 |
| 19 | Concentration check | SRF, FFQ, MYB, IND | ★★★★ | SRF | Drop scenario + amount to sell | Feed from net-worth log | L | P1 |
| 20 | 401(k) match & limits, Roth vs traditional | SRF | ★★★★ | SRF | Only full version, 2026 limits | Year-keyed limits shared with tax engine | L | P1 |
| 21 | Retirement: FI number, projection, money lasts | SRF, MYB | ★★★★ | SRF | Most complete | Inflation-adjusted toggle | L | P1 |
| 22 | Social Security claiming | SRF | ★★★★ | SRF | Factor + break-even | Spousal benefit note | L | P2 |
| 23 | Net-worth log over time | SRF, MYB, FFQ | ★★★★ | SRF | Dated entries, totals, CSV | Plotly trend chart; include FAP loan balances | M | P0 |
| 24 | Allocation & rebalance | SRF, STK | ★★★★ | SRF | Dollar trades | none | L | P2 |
| 25 | 529 / college | SRF, MYB | ★★★★ | SRF | Inflated cost, monthly needed | none | L | P2 |
| 26 | Life insurance need | SRF, MYB, IND | ★★★ | Merge SRF + MYB | Same formula; MYB splits mortgage | One function | L | P1 |
| 27 | Health plan compare | MYB | ★★★★ | MYB | Only source, with chart | Generic (not Intel-specific) labels | L | P2 |
| 28 | Insurance / loan / document organizer + Upcoming list | FAP, LAP | ★★★★★ | FAP | Unified upcoming/overdue | Add LAP household records (vehicle, warranty) | M | P0 |
| 29 | Bill / plan / repair-quote compare | LAP | ★★★★ | LAP | Only source | Extract from single file into a module | M | P2 |
| 30 | Document date/amount extraction | LAP | ★★★★ | LAP | Only source, honest limits | Output to bills/organizer | M | P2 |
| 31 | Subscriptions cost tracker | FAP, AUD | ★★★★ | FAP | Real annual cost chart | Add detection (row 32) | L | P1 |
| 32 | Recurring-charge detection | AUD (★) | ★ | none → Rewrite | AUD rules are not recurrence detection | Recurrence over FAP transactions | M | P1 |
| 33 | Rule-based insights | FAP | ★★★★ | FAP | Shows the triggering rule | Add rules for subscriptions, emergency-fund gap | L | P0 |
| 34 | Money checkup ladder (what to fund next) | SRF | ★★★★ | SRF | Simple, high value | Pre-fill from user data | L | P1 |
| 35 | Home: property tax (Prop 13), rental cash flow, depreciation, sale gain | HAF | ★★★★ | HAF | Only source, CA-specific | Separate "Home & rental" module | M | P2 |
| 36 | Rent-increase cap, deposit rules, solar, leak | HAF | ★★★★ | HAF | Niche | Keep in home-admin-faqs, link out | — | P3 / Remove |
| 37 | Year calendar `.ics` export | HAF, MYB, (diary-faqs) | ★★★★ | HAF | Tested escaping | Generate from bills + tax dates | L | P1 |
| 38 | Learning lessons + cheatsheet | FFQ, SRF, STK, TAX, HAF, MYB, IND | ★★★★ | SRF structure + FFQ basics | Search, quiz, progress | De-duplicate overlap; one sources file with allowed-domain test (SRF/MYB pattern) | M | P2 |
| 39 | Quiz center | SRF, HAF | ★★★★ | SRF | Deterministic shuffles, scoring | — | L | P3 |
| 40 | Valuation ratios, drawdown, stress test | STK | ★★★ | STK | Only source | — | L | P3 |
| 41 | News headlines (RSS) | MYB | ★★★ | MYB | Free RSS | Not core to money admin | — | Remove |
| 42 | India calculators (INR, SIP, EMI, FD, DICGC) | IND | ★★★ | IND | Only source | Keep as separate app or later locale pack | — | P3 / Remove from core |
| 43 | "AI auditor" LLM mode | AUD | ★ | none | Unused paid key field | Do not migrate | — | Remove |
| 44 | Stage / animated visuals (`visuals.py`) | most | ★★★ | FFQ | Shared copy | Use only on Learn pages | L | P3 |
| 45 | Finz Learner features | finz-learner | — | **[NI]** | Code not accessible | Re-audit when access is granted | ? | ? |
