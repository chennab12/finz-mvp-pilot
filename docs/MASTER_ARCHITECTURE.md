# FinLife 360 — Master Architecture (proposal)

Audit date: 2026-10-19. This is a design proposal; no code has been written. It follows the constraints already used across CB's apps and the user's brief: Python + Streamlit, **no paid AI APIs, no API keys, no login, no database server**, mobile-friendly, honest labels for estimates.

## 1. Guiding decisions

| Decision | Choice | Why |
|---|---|---|
| App shape | **One Streamlit app**, multipage via `st.navigation` | One deploy, one URL; pages load only when opened (FFQ's "render one section" lesson [V]) |
| Core codebase | Start from **finz-admin-pilot** | Best-tested, typed, validated code (59 tests [V]); already owns the P0 money-admin features |
| Logic vs UI | Pure-Python `engines/` with no Streamlit imports; pages only call engines | Lets every calculator be unit-tested; all strong source apps already separate `calculations.py` [V] |
| Charts | Plotly with one theme helper (FAP `style_fig`) | Best visual quality found [V]; consistent across pages |
| Storage | Session state + **one versioned JSON backup** (FAP `storage.py`); optional auto-save to a local folder when run locally | Works on Streamlit Community Cloud's ephemeral disk; no DB to secure |
| "AI" | Deterministic, explainable rules (insights, categorization learned from user corrections, recurrence detection) | Free, private, testable; meets "no paid AI APIs" |
| Tax data | One module per tax year (`tax_2025.py`, `tax_2026.py`) | Removes today's drifted copies [V] and supports the filing year vs planning year split |
| Scope | US federal + California | Matches CB's existing apps; India stays a separate app |

What it deliberately avoids: microservices, FastAPI backend, React front end, databases, authentication, background jobs, bank aggregators, LLM calls. None is needed for a single-household tool.

## 2. Folder layout

```
finlife-360/
├── app.py                     # st.navigation, sidebar (backup/restore, currency, sample data)
├── pages/
│   ├── dashboard.py           # P0  FAP dashboard + net worth + emergency tiles + insights
│   ├── transactions.py        # P0  FAP import, rules, flags, export
│   ├── budget_bills_goals.py  # P0  FAP budgets, bills, goals, projection
│   ├── organizer.py           # P0  FAP organizer + LAP household records
│   ├── net_worth.py           # P0  SRF log + Plotly trend
│   ├── calculators.py         # P0/P1 picker over engines (loan, refi, debt, growth, emergency, savings goal…)
│   ├── taxes.py               # P0/P1 take-home estimator, bracket view, filing checklist (TAX)
│   ├── invest_retire.py       # P1  401(k), Roth vs trad, FI, money lasts, SS, ESPP, RSU, concentration, rebalance, 529
│   ├── insurance.py           # P1/P2 life need, health plan compare, home rebuild gap
│   ├── home.py                # P2  Prop 13, rental cash flow, depreciation, sale gain (HAF)
│   ├── documents.py           # P2  LAP extraction + bill/quote compare
│   └── learn.py               # P2  lessons, cheatsheet, search, quiz
├── engines/                   # pure functions, no Streamlit
│   ├── validation.py          # InputError, _check_number (FAP)
│   ├── loans.py               # payment, amortization, refinance (FAP + HAF)
│   ├── debt.py                # avalanche/snowball (FAP, id-keyed)
│   ├── growth.py              # compound growth, fees, inflation, goal saving (merged)
│   ├── emergency.py
│   ├── tax/                   # engine.py + tax_2025.py + tax_2026.py (MYB + SRF + TAX)
│   ├── retirement.py          # SRF
│   ├── equity.py              # RSU gap, ESPP, concentration
│   ├── insurance.py           # life need, plan compare, rebuild gap
│   └── home.py                # HAF property/rental math
├── data_layer/
│   ├── transactions.py        # FAP
│   ├── planning.py            # FAP
│   ├── recurring.py           # NEW recurrence detection
│   ├── categorize.py          # NEW learn rules from corrections
│   ├── storage.py             # FAP, extended schema + schema_version
│   └── sample_data.py         # synthetic, labelled
├── insights/rules.py          # FAP rules + new ones
├── content/                   # lessons, sources (allowed-domain test), checklist (TAX)
├── ui/                        # style_fig, money formatting, md() escaping, sample banner (FAP)
├── tests/                     # engines (unit), data_layer (unit), pages (AppTest smoke)
├── .github/workflows/tests.yml
├── .streamlit/config.toml
└── requirements.txt           # streamlit, pandas, plotly, pypdf
```

## 3. Data model (single JSON document)

```
{
  "schema_version": 1,
  "settings":   {"currency": "USD", "tax_year": 2026, "state": "CA", "filing_status": "MFJ"},
  "transactions": [...],  "rules": [...],
  "budgets": [...],  "bills": [...],  "goals": [...],
  "organizer": {"loans": [...], "insurance": [...], "subscriptions": [...],
                "documents": [...], "tasks": [...], "household_records": [...]},
  "net_worth_log": [{"date": "...", "category": "...", "name": "...", "amount": ...}],
  "tax_profile": {"wages": [...], "pretax_401k": ..., "hsa": ..., "children": ...},
  "checklists": {"tax_filing_2025": [{"item": "...", "status": "Ready"}]}
}
```
Restore validates every field (FAP `clean_records` / `_coerce` pattern [V]) and returns a list of problems instead of failing. Every record carries an `id` (fixes the duplicate-name class of bug).

## 4. Data flow

```
CSV / manual entry ──► data_layer (normalize, rules, flags, recurrence)
                              │
                              ▼
                  session_state["data"]  ◄──► JSON backup / local auto-save
                              │
       ┌──────────────┬───────┴────────┬──────────────┐
       ▼              ▼                ▼              ▼
   dashboard     calculators       taxes/retire    organizer
   + insights   (engines/*)        (engines/*)     (+ .ics export)
```
Calculators pre-fill from the user's data where possible (average spend → emergency fund, organizer loans → debt payoff, budgets → essentials), but every input stays editable.

## 5. Quality bar

- Port each source app's tests with its module (158 tests pass today across FAP, SRF, HAF, MYB and FFQ [V]; only the tests for migrated functions move); add tests for every merge (growth convention, tax boundaries for 2025 and 2026, id-keyed debts).
- AppTest smoke test per page; CI on every push (pattern already in 6 repos [V]).
- Every estimate states its assumptions next to the result (all strong source apps already do this [V]).
- Links only to allowed official domains, enforced by a test (SRF/MYB pattern [V]).
- Sample data is synthetic and visibly labelled (FAP pattern [V]).

## 6. Deployment

Streamlit Community Cloud from a new repo (the empty `chennab12/finz-mvp-pilot` could host it if CB intends that **[A]**, otherwise a new `finlife-360` repo). The Dockerfile from finance-faqs PR #2 (Cloud Run, unmerged per memory **[A]**) can be reused later if CB wants Cloud Run.

## 7. Risks and open items

| Risk | Mitigation |
|---|---|
| Session data lost on refresh | Prominent backup button; local auto-save option; restore validates input |
| Tax figures go stale yearly | Year-keyed modules + a test that fails when the current year has no table |
| Merged calculators change results users saw before | Document the chosen conventions on the page and in README |
| finz-learner content unknown [NI] | Re-audit once access is granted; Learn page is P2 so it does not block the core |
| Live deployments not inspected | Verify that each live URL matches its repo `main` before migrating anything only seen live |
