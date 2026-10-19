# FinLife 360 — Development Roadmap

Audit date: 2026-10-19. No implementation starts until CB approves the audit. Sizes are relative effort (S / M / L), not calendar time. Every phase ends with tests green in CI and a usable app.

## Phase 0 — Before any code (decisions and access)

| Item | Owner | Status |
|---|---|---|
| Grant access to `chennab12/finz-learner` (add it to the Claude GitHub app) or point to its code, so it can be audited | CB | Open: currently **not inspected** |
| Confirm which repo each live URL deploys (finz-app-pilot → finz-admin-pilot? ai-finz-auditor → ai-financial-auditor?) | CB | Open: **assumed** by name |
| Choose the repo for FinLife 360 (empty `finz-mvp-pilot`, or a new `finlife-360`) | CB | Open |
| Approve conventions: effective-annual compounding; US federal + CA only; JSON storage | CB | Proposed |

## Phase 1 — Foundation (S)
Goal: an empty but solid shell.
- Scaffold layout from MASTER_ARCHITECTURE.md; `st.navigation`; CI workflow; `.streamlit/config.toml`.
- Move FAP `validation`, `ui` helpers (`style_fig`, `md()` escaping, money formatting), `storage.py` with `schema_version`.
- Exit: AppTest smoke passes for the shell; backup/restore round-trip test.

## Phase 2 — Money core MVP (M) — the 80% value
Source: finz-admin-pilot, nearly as-is.
- Transactions (import, mapping, rules, duplicate/transfer flags, export).
- Dashboard with rule-based insights.
- Budgets, bills with Paid roll-forward, goals, cash-flow projection.
- Organizer (loans, insurance, subscriptions, documents, tasks) + Upcoming/Overdue.
- Calculators: loan amortization, debt payoff (**fix duplicate-name bug first, with a regression test**), savings goal, subscription cost.
- Exit: all 59 FAP tests ported and passing; sample data loads on every page.

## Phase 3 — Safety net and net worth (S)
- Emergency fund (merge FFQ + FAP, pre-filled from average spending).
- Compound growth (merge FFQ + STK + FAP; documented convention; regression test showing the chosen number for a fixed case).
- Net-worth log (SRF) with Plotly trend; loans pulled from organizer.
- Refinance break-even (HAF).
- Money checkup ladder (SRF), pre-filled.
- Exit: dashboard shows net worth and emergency-fund months.

## Phase 4 — Taxes (M)
- `engines/tax/` with `tax_2025.py` and `tax_2026.py`; merge MYB take-home + SRF two-earner + TAX filing statuses and CTC phaseout.
- Resolve the CA standard deduction mismatch (11,400 vs 11,412) against the FTB table, and verify every constant against IRS/FTB pages from a network that can reach them.
- Tax page: take-home estimator, bracket breakdown chart, deduction comparison, payment reconciliation.
- Tax filing checklist (TAX), rewritten into readable functions, with JSON progress inside the main backup.
- Exit: boundary tests at every bracket edge for both years and all statuses.

## Phase 5 — Invest, retire, insure (M)
- SRF suite: 401(k) match & limits, Roth vs traditional, FI number, projection, money lasts, Social Security, rebalance, 529.
- Equity comp: RSU gap (MYB), ESPP (merge), concentration (SRF).
- Insurance: life need (merge), health plan compare (MYB, generic labels).
- Exit: SRF/MYB calculator tests ported; limits read from the tax-year module.

## Phase 6 — New smart features, still free and local (M)
- Recurring-charge detection over transactions (replaces AUD's rules) → feeds subscription tracker and an insight.
- Learn-from-corrections categorization.
- Credit card utilization tracker.
- `.ics` export for bills, renewals and tax dates (HAF pattern).
- Exit: unit tests with synthetic monthly, annual and price-change cases.

## Phase 7 — Home, documents, learning (L)
- Home & rental page (HAF property tax, rental cash flow, depreciation, sale gain).
- Documents page (LAP extraction → bill/organizer item; bill and repair-quote compare).
- Learn hub: SRF structure, FFQ basics, TAX topics, de-duplicated; finz-learner content once inspected.
- Annual money review page.
- Optional local auto-save when run on CB's computer.

## Phase 8 — Retire the old apps (S, CB's call)
- Add a "moved to FinLife 360" banner/link in each superseded app (FFQ, FAP, SRF, STK, TAX, AUD) only when CB asks.
- Keep HAF, MYB, IND and LAP live if CB still wants their niche content.

## Priority summary

| Priority | Features |
|---|---|
| P0 | Transactions, dashboard + insights, budgets, bills, goals, organizer, loan amortization, debt payoff (fixed), emergency fund, compound growth, net-worth log, household tax estimator, JSON backup |
| P1 | Refinance, tax checklist, deduction/payment tools, RSU, ESPP, concentration, 401(k), retirement, life insurance, subscriptions + recurrence detection, checkup ladder, `.ics` |
| P2 | Social Security, rebalance, 529, health plan compare, home & rental, documents, compare tools, learn hub, annual review, credit utilization, local auto-save |
| P3 | Quiz, valuation/stress tools, stage visuals, India locale pack |
