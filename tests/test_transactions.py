from datetime import date

import pandas as pd
import pytest

from finlife.data import transactions as tx


def frame(rows):
    return tx.normalize(pd.DataFrame(rows))


def row(d, desc, amount, account="Checking", category="", exclude=False):
    return {"date": d, "description": desc, "amount": amount, "account": account, "category": category,
            "exclude": exclude, "source": "rule"}


@pytest.mark.parametrize("raw,expected", [
    ("$1,234.50", 1234.5), ("(12.00)", -12.0), ("-5", -5.0), ("12.00 CR", 12.0), ("40.10 DR", -40.1),
    ("", None), ("abc", None), ("€ 9.99", 9.99), (7, 7.0),
])
def test_parse_amount(raw, expected):
    assert tx.parse_amount(raw) == expected


def test_refund_reduces_category_spending_not_income():
    df = frame([
        row("2026-09-01", "Pay", 1000, category="Salary"),
        row("2026-09-03", "Online store order", -100, "Card", "Shopping"),
        row("2026-09-10", "Online store refund", 40, "Card", "Shopping"),
    ])
    s = tx.monthly_summary(df).iloc[0]
    assert s["income"] == 1000
    assert s["spending"] == 60
    cats = tx.category_spending(df, "2026-09").set_index("category")
    assert cats.loc["Shopping", "spent"] == 60
    assert cats.loc["Shopping", "refunds"] == 40


def test_transfers_and_card_repayments_are_not_double_counted():
    df = frame([
        row("2026-09-01", "Pay", 3000, category="Salary"),
        row("2026-09-05", "Groceries", -200, "Card", "Groceries"),
        row("2026-09-06", "Dinner", -50, "Card", "Dining"),
        # Paying the card from checking: excluded on both sides.
        row("2026-09-25", "Credit card autopay", -250, "Checking", "Credit card payment"),
        row("2026-09-25", "Payment thank you", 250, "Card", "Credit card payment"),
        # Moving money to savings: excluded.
        row("2026-09-16", "Transfer to savings", -500, "Checking", "Transfer"),
        row("2026-09-16", "Transfer from checking", 500, "Savings", "Transfer"),
    ])
    s = tx.monthly_summary(df).iloc[0]
    assert s["income"] == 3000
    assert s["spending"] == 250  # each purchase counted once, on the card
    assert s["surplus"] == 2750


def test_excluded_rows_are_ignored():
    df = frame([row("2026-09-05", "Cafe", -20, category="Dining"),
                row("2026-09-05", "Cafe", -20, category="Dining", exclude=True)])
    assert tx.monthly_summary(df).iloc[0]["spending"] == 20


def test_duplicate_flags_later_copy_only():
    df = frame([row("2026-09-17", "CORNER CAFE", -23.4, "Card"), row("2026-09-17", "Corner  cafe", -23.4, "Card"),
                row("2026-09-18", "CORNER CAFE", -23.4, "Card")])
    dups = tx.duplicate_ids(df)
    assert dups == {df.loc[1, "id"]}


def test_transfer_pair_detection():
    df = frame([row("2026-09-20", "Zelle to savings", -250, "Checking"),
                row("2026-09-21", "Deposit", 250, "Savings"),
                row("2026-09-21", "Same account refund", 250, "Checking"),
                row("2026-09-01", "Far apart", -99, "Checking"), row("2026-09-20", "Far apart", 99, "Savings")])
    pairs = tx.transfer_pair_ids(df)
    assert pairs == {df.loc[0, "id"], df.loc[1, "id"]}


def test_keyword_rules_first_match_and_word_start():
    rules = tx.clean_rules([{"keyword": "payment thank you", "category": "Credit card payment"},
                            {"keyword": "rent", "category": "Housing"},
                            {"keyword": "cafe", "category": "Dining"}])
    assert tx.suggest_category("RENT PAYMENT", -2000, rules) == "Housing"
    assert tx.suggest_category("CURRENT ACCOUNT FEE", -5, rules) == "Uncategorized"
    assert tx.suggest_category("PAYMENT THANK YOU", 300, rules) == "Credit card payment"
    assert tx.suggest_category("Mystery deposit", 50, rules) == "Other income"


def test_apply_rules_keeps_manual_corrections():
    df = frame([row("2026-09-01", "Corner cafe", -10)])
    df.loc[0, ["category", "source"]] = ["Gifts & donations", "manual"]
    rules = [{"keyword": "cafe", "category": "Dining"}]
    assert tx.apply_rules(df, rules).loc[0, "category"] == "Gifts & donations"
    assert tx.apply_rules(df, rules, overwrite_manual=True).loc[0, "category"] == "Dining"


def test_csv_mapping_signed_and_split_columns():
    raw = tx.read_csv_bytes(b"Posted Date,Payee,Amount\n09/01/2026,Cafe,\"$1,200.00\"\nbad,Shop,5\n09/02/2026,Shop,oops\n")
    m = tx.guess_mapping(list(raw.columns))
    assert m["date"] == "Posted Date" and m["description"] == "Payee" and m["amount"] == "Amount"
    out, problems = tx.map_columns(raw, m, flip_sign=True, default_account="Card")
    assert len(out) == 1 and out.loc[0, "amount"] == -1200.0 and out.loc[0, "account"] == "Card"
    assert out.loc[0, "date"] == date(2026, 9, 1)
    assert len(problems) == 2

    raw2 = tx.read_csv_bytes(b"Date,Description,Debit,Credit\n2026-09-01,Groceries,45.10,\n2026-09-02,Pay,,900\n")
    m2 = tx.guess_mapping(list(raw2.columns))
    out2, _ = tx.map_columns(raw2, m2, amount_mode="split")
    assert list(out2["amount"]) == [-45.10, 900.0]


def test_csv_mapping_day_first_dates():
    raw = tx.read_csv_bytes(b"Date,Description,Amount\n03/04/2026,Cafe,-5\n")
    out, _ = tx.map_columns(raw, tx.guess_mapping(list(raw.columns)), dayfirst=True)
    assert out.loc[0, "date"] == date(2026, 4, 3)


def test_mapping_requires_columns():
    raw = tx.read_csv_bytes(b"A,B\n1,2\n")
    with pytest.raises(ValueError):
        tx.map_columns(raw, {"date": None, "description": "B", "amount": "A"})


def test_budget_vs_actual():
    df = frame([row("2026-09-05", "Cafe", -80, category="Dining")])
    bva = tx.budget_vs_actual(df, [{"category": "Dining", "monthly_budget": 50},
                                   {"category": "Travel", "monthly_budget": 100}], "2026-09").set_index("category")
    assert bva.loc["Dining", "remaining"] == -30
    assert bva.loc["Travel", "actual"] == 0
