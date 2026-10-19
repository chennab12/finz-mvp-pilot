# Sample test files

All files here are **synthetic**. They describe a made-up household and contain no real personal or financial information. Use them to try every feature of FinLife 360, locally or on https://finz-mvp-pilot.streamlit.app/.

| File | Where to load it | What it exercises |
|---|---|---|
| [finlife-full-sample-backup.json](finlife-full-sample-backup.json) | Sidebar → choose the file under Restore → **♻️ Restore from file** | Everything at once. It holds every table and fires every rule in the app (see below). |
| [sample_bank_export.csv](sample_bank_export.csv) | **Income & Expenses** → Import a bank or card CSV | The import wizard. It has separate Debit and Credit columns, `$` signs, US dates, a pending row with no date and a check with no amount (both skipped and reported), a duplicate café charge, a Zelle and a savings transfer (flagged), a refund, and merchants that no rule knows. Under "Amounts are in…", choose "Separate money-out and money-in columns". |
| [sample_transactions.csv](sample_transactions.csv) | **Income & Expenses** → Import, or **Import & Export** → transactions | The same transactions as the backup, in the app's own export format. |
| [tables/*.csv](tables/) | **Import & Export** → Import a table (Add or Replace) | One CSV per table: accounts, bills, budgets, debts, documents, goals, insurance, net-worth log, rules, subscriptions and tasks. |

## What the full backup triggers

- **Dashboard:** 7 months of history (6 complete months plus the current month). The last complete month has a car repair and an urgent-care bill, so it shows a deficit. A large-purchase insight, category spikes, over-budget categories, and duplicate, transfer and uncategorized insights also appear.
- **Action Center:** all 12 rule types fire:
  - overdue and due-soon bills, debts, insurance and documents
  - your own tasks (an overdue Low task is raised to Medium)
  - a cash-flow deficit and a savings rate under 10%
  - a thin emergency fund
  - two high-APR cards
  - over-budget categories
  - a goal that is behind, and one past its deadline
  - a subscription marked Cancel
  - flagged and uncategorized transactions
  - a net-worth snapshot older than 35 days

  One action ("Home down payment") is snoozed, so **Bring back snoozed item(s)** has something to restore. Done tasks, a cancelled subscription and an inactive bill show that finished items are skipped.
- **Income & Expenses:**
  - custom keyword rules (auto repair, tax refund, babysitter) and an excluded row with a note
  - one row in every category group: salary, interest, other income, fees and uncategorized
  - transfers and card payments
- **Budget & Goals:** 14 budgets, bills of every frequency (weekly, monthly, quarterly and yearly; autopay and manual; one inactive), 5 goals (on track, behind, complete and past deadline), and the cash-flow projection.
- **Accounts & Net Worth:** 8 accounts of 6 types, two of them marked as emergency fund. Five debts:
  - two credit cards (avalanche and snowball pick different debts first)
  - a car loan
  - a student loan
  - a 0% medical payment plan

  The net-worth history stops more than 35 days ago, so press **Record snapshot** to add today.
- **Calculator Center:** the debt payoff and retirement calculators pre-fill from these debts and accounts.

## Dates

The files were generated for **2026-10-19**, and their due dates are relative to that day. On a later day more items show as overdue. To regenerate the files for today, run:

```bash
python scripts/make_sample_files.py            # or: python scripts/make_sample_files.py 2026-11-30
```

`tests/test_sample_files.py` checks that the files load, that the bank CSV imports, and that every rule fires.
