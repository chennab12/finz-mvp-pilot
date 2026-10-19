# FinLife 360

One personal-finance app for a household. It combines the strongest parts of CB's existing finance apps (mainly finz-admin-pilot, plus ideas and formulas from finance-faqs, stocks-retire-faqs, intel-myben, taxes-faqs and home-admin-faqs) into a single Streamlit app.

- **No paid AI and no API keys.** Insights and the action list come from plain, testable rules.
- **No login and no database server.** Data lives in the browser session, with optional auto-save to a local JSON file.
- **Synthetic sample data only.** The sample household ("Northwind Labs" payroll, "Oak Apts" rent and so on) is generated in code. It contains no real personal information.

The audit that shaped this app is in [docs/](docs/).

## What it does

| Page | What you can do |
|---|---|
| **Dashboard** | Pick a month. Shows income, spending, money left over and savings rate, net worth, emergency-fund months, total debt, bills due in the next 30 days and open actions. Includes income vs spending, a category donut, budget vs actual, the net-worth trend, rule-based insights and your top actions. |
| **Action Center** | A prioritized to-do list built from your data: overdue or due-soon bills and renewals, your own tasks, cash-flow deficit, low savings rate, a thin emergency fund, high-APR debt, over-budget categories, goals that are behind, subscriptions marked Cancel, transactions to review and a stale net-worth snapshot. Each action says why it matters and what to do, and you can mark it Done or snooze it. Also includes a "what to fund next" checkup ladder, a 30-day calendar, and editable tasks, subscriptions, insurance and documents. |
| **Income & Expenses** | Quick-add a transaction. Import a bank CSV with column mapping and keyword category rules. Edit, add or delete transactions in an editable table with search and category filters. Duplicate and transfer flags, with one-click fixes. CSV export. |
| **Budget & Goals** | Monthly budgets per category with budget vs actual, savings goals with progress, recurring bills, and a cash-flow projection. |
| **Accounts & Net Worth** | Accounts and debts, net worth by type, and net-worth snapshots over time. |
| **Calculator Center** | Loan & mortgage (amortization, extra payments), refinance break-even, debt payoff (avalanche vs snowball), savings goal, investment growth (fees and inflation), emergency fund, retirement (FI number, how long money lasts), take-home pay (2026 federal + California, FICA, 401(k)/HSA/FSA, child tax credit) and subscriptions. Calculators pre-fill from your data where possible, and every input stays editable. |
| **Import & Export** | Full JSON backup and restore, CSV export of any table, and CSV import into any table (add or replace) with a preview. |
| **Guide & Assumptions** | Getting started, what each page does, every assumption the calculators make, privacy notes and official reference links. |

Every page has a 💡 plain-English explanation. Results that are estimates carry a 📐 **Estimate** label that lists their assumptions.

## Run it locally

Needs Python 3.10 or newer.

```bash
git clone https://github.com/chennab12/finz-mvp-pilot.git
cd finz-mvp-pilot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The app starts with the synthetic sample household. Use **🧹 Start with empty data** in the sidebar to begin with your own numbers, or import a CSV on **Income & Expenses**.

To try every feature at once, restore [data/finlife-full-sample-backup.json](data/finlife-full-sample-backup.json) from the sidebar. [data/README.md](data/README.md) lists every test file (a messy bank CSV, a CSV per table) and what each one exercises.

## Where your data is stored

| Mode | When | What happens |
|---|---|---|
| **Local file** | The app is opened at `localhost` or `127.0.0.1`, or `FINLIFE_STORAGE=file` is set | Every change is saved to `finlife_data/finlife.json` (atomic write) and loaded again next time. |
| **Session only** | Anywhere else (for example Streamlit Community Cloud) | Data lives only in your browser tab. Use **Download backup** in the sidebar and **Restore** it next time. This keeps one visitor's data from being written to a shared server file. |

Settings:

- `FINLIFE_STORAGE=file` or `session` forces a mode.
- `FINLIFE_DATA_DIR=/path/to/folder` changes where the local file is written. The default is `./finlife_data`, which is git-ignored.

## Tests

```bash
pip install pytest
python -m pytest -q
```

111 tests cover:

- loan, refinance, debt payoff (including the duplicate-name bug found in the audit), savings, growth with fees and inflation, retirement and tax calculations, with known reference values and bracket edges;
- input validation (negative, NaN, infinite and out-of-range values are rejected with a clear message);
- the data layer: CSV import mapping, rules, duplicate and transfer flags, bills rolling forward, backup and restore, local file persistence, CSV round trips and the sample data;
- the action rules and dashboard metrics;
- the files in data/: they load, the bank CSV imports, and the full backup fires every action rule;
- every page and every calculator rendered with Streamlit's AppTest, plus quick-add, Done and Snooze, empty and sample data, currency change and save-and-reload.

GitHub Actions runs the suite on every push ([.github/workflows/tests.yml](.github/workflows/tests.yml)).

## Deploy

### Streamlit Community Cloud (free)

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app**, then choose **Deploy a public app from GitHub**.
3. Repository: `chennab12/finz-mvp-pilot`. Branch: `main`. Main file path: `app.py`.
4. Optional: under **Advanced settings**, choose Python 3.12.
5. Click **Deploy**.

No secrets are needed. On Community Cloud the app runs in **session only** mode, so remind users to download a backup.

### Any server or container

```bash
pip install -r requirements.txt
FINLIFE_STORAGE=session streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

Use `FINLIFE_STORAGE=file` only when the server is for one household, and point `FINLIFE_DATA_DIR` at a persistent volume.

## Assumptions and conventions

- **Loans** use APR ÷ 12 as the monthly rate. **Savings and investment growth** convert an effective annual return to a monthly rate as `(1 + r)^(1/12) − 1`, and an annual fee reduces growth multiplicatively. All schedules stop at 600 months (50 years).
- **Taxes** use 2026 federal brackets and standard deductions (married filing jointly and single), Social Security 6.2% up to $184,500, Medicare 1.45% plus 0.9% above $250,000 (joint) or $200,000 (single), the $2,200 child tax credit with its phase-out, and California's 2025 brackets with a $11,412 / $5,706 standard deduction, the 1% surcharge above $1M and 1.3% SDI. They ignore itemized deductions, credits other than the child tax credit, AMT and local taxes. Verify against IRS and FTB tables before acting.
- **Retirement** uses a withdrawal rate you choose (4% by default) and a real (after-inflation) return.
- **Insights and actions** are fixed rules (for example, a savings rate under 10%, debt over 10% APR, or a category over budget). Each action shows the rule that produced it.
- The **emergency fund** counts only accounts you tick as emergency savings, measured against average essential spending over complete months.

## Project layout

```
app.py                 navigation, sidebar (backup/restore, currency, sample/empty), auto-save
screens/               one thin file per page (calls finlife.views)
finlife/calc/          pure calculation engines, no Streamlit: loans, debt, savings, retirement, tax
finlife/data/          transactions, planning (budgets, bills, goals, dated items), storage, net worth, sample data
finlife/metrics.py     dashboard numbers computed once from the data
finlife/actions.py     prioritized action rules, snooze, checkup ladder
finlife/insights.py    plain-English spending insights
finlife/ui/            shared formatting, editors, explanations and Plotly charts
finlife/views/         one module per page
tests/                 pytest unit tests and AppTest page tests
data/                  synthetic test files: full backup, bank CSV, one CSV per table
scripts/               make_sample_files.py regenerates data/ for today's date
docs/                  the consolidation audit
```

## Audit documents

| Document | What it covers |
|---|---|
| [APP_INVENTORY.md](docs/APP_INVENTORY.md) | Every finance app found: purpose, modules, calculators, charts, tables, storage, AI, gaps |
| [FEATURE_COMPARISON.md](docs/FEATURE_COMPARISON.md) | Head-to-head comparison of duplicated features and the master comparison matrix |
| [BEST_OF_BEST_FEATURES.md](docs/BEST_OF_BEST_FEATURES.md) | The top 20% of features and the reuse / merge / rewrite / remove / add classification |
| [MASTER_ARCHITECTURE.md](docs/MASTER_ARCHITECTURE.md) | Single-app Streamlit architecture, data model and quality bar |
| [DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) | Phased plan with priorities and exit criteria |

FinLife 360 is an educational planning tool, not financial, tax or legal advice.
