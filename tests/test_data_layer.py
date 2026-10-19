import json
from datetime import date

import pytest

from finlife.data import networth, planning, sample, storage
from finlife.data import transactions as tx

TODAY = date(2026, 10, 19)


def test_add_months_clamps_month_end():
    assert planning.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert planning.add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


def test_bill_occurrences_and_overdue():
    bills = [{"name": "Rent", "amount": 1000, "frequency": "Monthly", "next_due": "2026-10-10", "active": True},
             {"name": "Off", "amount": 5, "frequency": "Monthly", "next_due": "2026-10-20", "active": False}]
    occ = planning.bill_occurrences(bills, TODAY, date(2026, 12, 31))
    assert [o["due"] for o in occ] == [date(2026, 10, 10), date(2026, 11, 10), date(2026, 12, 10)]
    assert occ[0]["overdue"] and not occ[1]["overdue"]


def test_monthly_equivalent():
    bills = [{"name": "A", "amount": 120, "frequency": "Yearly"}, {"name": "B", "amount": 10, "frequency": "Weekly"}]
    assert planning.monthly_equivalent(bills) == pytest.approx(10 + 520 / 12)


def test_goal_status_indicators():
    ok = planning.goal_status({"name": "A", "target": 1200, "saved": 0, "monthly_contribution": 200,
                               "deadline": "2027-10-19"}, TODAY)
    assert ok["status"] == "On track"
    behind = planning.goal_status({"name": "B", "target": 1200, "saved": 0, "monthly_contribution": 50,
                                   "deadline": "2027-04-19"}, TODAY)
    assert behind["status"] == "Behind"
    assert planning.goal_status({"name": "C", "target": 100, "saved": 100}, TODAY)["status"] == "Reached"
    assert planning.goal_status({"name": "", "target": 100}, TODAY) is None


def test_cash_flow_projection_math():
    bills = [{"name": "Insurance", "amount": 600, "frequency": "Yearly", "next_due": "2026-12-05"}]
    proj = planning.cash_flow_projection(today=TODAY, months=3, starting_balance=1000, monthly_income=3000,
                                         monthly_variable_spending=2000, bills=bills, goal_contributions=100)
    assert list(proj["Month"]) == ["Nov 2026", "Dec 2026", "Jan 2027"]
    assert list(proj["Bills"]) == [0, 600, 0]
    assert list(proj["Closing"]) == [1900, 2200, 3100]


def test_complete_item_advances_recurring_and_marks_one_offs():
    data = {"bills": [{"name": "Rent", "next_due": "2026-10-31", "frequency": "Monthly"}],
            "debts": [{"name": "Car", "balance": 100, "next_due": "2026-10-06"}],
            "insurance": [{"policy": "Auto", "renewal_date": "2026-11-01", "term_months": 6}],
            "subscriptions": [{"name": "News", "billing": "Yearly", "renewal_date": "2026-10-30"}],
            "tasks": [{"task": "Call bank", "due_date": "2026-10-20", "done": False}]}
    planning.complete_item(data, "bills", 0)
    planning.complete_item(data, "debts", 0)
    planning.complete_item(data, "insurance", 0)
    planning.complete_item(data, "subscriptions", 0)
    planning.complete_item(data, "tasks", 0)
    assert data["bills"][0]["next_due"] == "2026-11-30"
    assert data["debts"][0]["next_due"] == "2026-11-06"
    assert data["insurance"][0]["renewal_date"] == "2027-05-01"
    assert data["subscriptions"][0]["renewal_date"] == "2027-10-30"
    assert data["tasks"][0]["done"] is True


def test_upcoming_items_skip_completed_and_paid_off():
    data = {"tasks": [{"task": "Open", "due_date": "2026-10-20", "done": False},
                      {"task": "Done", "due_date": "2026-10-20", "done": True},
                      {"task": "Overdue", "due_date": "2026-10-01", "done": False}],
            "debts": [{"name": "Paid", "balance": 0, "next_due": "2026-10-21"}],
            "bills": []}
    assert [i["title"] for i in planning.upcoming_items(data, TODAY, 30)] == ["Overdue", "Open"]


def test_net_worth_totals_and_snapshot():
    accounts = [{"name": "Cash", "type": "Savings", "balance": 5000, "emergency_fund": True},
                {"name": "401k", "type": "Retirement", "balance": 20000, "emergency_fund": False},
                {"name": "", "type": "Savings", "balance": 999}]
    debts = [{"name": "Card", "balance": 1500}]
    t = networth.totals(accounts, debts)
    assert t == {"assets": 25000, "liabilities": 1500, "net_worth": 23500, "emergency_savings": 5000, "liquid": 5000}
    log = networth.record_snapshot([{"date": "2026-10-19", "assets": 1, "liabilities": 1}], accounts, debts, TODAY)
    assert len(log) == 1 and log[0]["assets"] == 25000
    hist = networth.history(log + [{"date": "2026-09-01", "assets": 20000, "liabilities": 2000}])
    assert list(hist["net_worth"]) == [18000, 23500]


def test_backup_round_trip():
    data = sample.sample_data(TODAY)
    restored, notes = storage.from_backup_bytes(storage.to_backup_json(data).encode())
    assert not notes
    assert len(restored["transactions"]) == len(data["transactions"])
    for key in storage.LIST_KEYS:
        assert restored[key] == storage.clean_records(key, data[key]), key
    assert restored["settings"]["is_sample"] is True
    assert tx.monthly_summary(restored["transactions"]).equals(tx.monthly_summary(data["transactions"]))


@pytest.mark.parametrize("payload", [b"not json", json.dumps({"app": "other"}).encode(), json.dumps([1, 2]).encode()])
def test_backup_rejects_foreign_files(payload):
    with pytest.raises(ValueError):
        storage.from_backup_bytes(payload)


def test_backup_drops_unknown_fields_and_bad_rows():
    payload = {"app": storage.APP_ID, "schema_version": 1,
               "settings": {"currency": "XXX", "emergency_months": 99, "dismissed": {"a": "2026-11-01", "b": "x"}},
               "goals": [{"name": "Trip", "target": "500", "evil": "<script>"}, "junk"],
               "transactions": [{"date": "2026-09-01", "description": "x", "amount": "-5"},
                                {"date": "nope", "description": "y", "amount": 1}]}
    restored, notes = storage.from_backup_bytes(json.dumps(payload).encode())
    assert restored["goals"] == [{"name": "Trip", "target": 500.0, "saved": None, "monthly_contribution": None,
                                  "deadline": None}]
    assert restored["settings"]["currency"] == "USD"
    assert restored["settings"]["emergency_months"] == 6.0
    assert restored["settings"]["dismissed"] == {"a": "2026-11-01"}
    assert len(restored["transactions"]) == 1 and notes


def test_local_file_persistence_round_trip(tmp_path):
    data = sample.sample_data(TODAY)
    path = storage.save_to_file(data, tmp_path / "x" / "finlife.json")
    loaded, notes = storage.load_from_file(path)
    assert not notes and storage.fingerprint(loaded) == storage.fingerprint(data)
    assert storage.load_from_file(tmp_path / "missing.json") is None
    assert [p.name for p in path.parent.iterdir()] == ["finlife.json"]  # no temp files left behind


def test_storage_mode(monkeypatch):
    monkeypatch.delenv("FINLIFE_STORAGE", raising=False)
    assert storage.storage_mode("localhost:8501") == "file"
    assert storage.storage_mode("127.0.0.1:8501") == "file"
    assert storage.storage_mode("finlife.streamlit.app") == "session"
    assert storage.storage_mode(None) == "session"
    monkeypatch.setenv("FINLIFE_STORAGE", "session")
    assert storage.storage_mode("localhost") == "session"
    monkeypatch.setenv("FINLIFE_STORAGE", "file")
    assert storage.storage_mode("example.com") == "file"


def test_table_csv_round_trip_and_bad_files():
    data = sample.sample_data(TODAY)
    for key in storage.LIST_KEYS:
        rows, _ = storage.table_from_csv(key, storage.table_to_csv(key, data))
        assert rows == storage.clean_records(key, data[key]), key
    rows, notes = storage.table_from_csv("budgets", b'Category,Monthly_Budget,Extra\nGroceries,"$1,200",x\n,,\n')
    assert rows == [{"category": "Groceries", "monthly_budget": 1200.0}]
    assert any("Ignored columns: extra" in n for n in notes)
    with pytest.raises(ValueError):
        storage.table_from_csv("budgets", b"foo,bar\n1,2\n")


def test_sample_data_is_labeled_realistic_and_relative_to_today():
    data = sample.sample_data(TODAY)
    df = data["transactions"]
    assert data["settings"]["is_sample"] is True
    assert df["date"].max() <= TODAY
    assert len(tx.monthly_summary(df)) == sample.MONTHS_OF_HISTORY + 1
    assert len(tx.duplicate_ids(df)) == 1
    assert not tx.counted(df)["category"].isin(["", "Uncategorized"]).any()
    s = tx.monthly_summary(df).iloc[:-1]
    assert ((s["surplus"] / s["income"]).between(0.15, 0.5)).all()  # believable savings rate
    # The same date always gives the same sample.
    assert sample.sample_data(TODAY)["transactions"].drop(columns="id").equals(df.drop(columns="id"))
