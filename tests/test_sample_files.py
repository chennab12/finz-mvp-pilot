"""The downloadable test files in data/ must load cleanly and exercise every rule."""

import copy
from collections import Counter
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from finlife import actions, metrics
from finlife.data import sample, storage
from finlife.data import transactions as tx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TODAY = date(2026, 10, 19)
ACTION_KINDS = {"due", "task", "cashflow", "savings-rate", "emergency", "debt", "budget", "goal", "goal-late",
                "sub-cancel", "clean", "networth-snapshot"}


def comprehensive():
    data, problems = storage.from_backup_bytes(storage.to_backup_json(sample.comprehensive_data(TODAY)).encode())
    assert problems == []
    return data


def test_comprehensive_data_fires_every_action_rule():
    data = comprehensive()
    m = metrics.compute(data, TODAY)
    acts = actions.build_actions(data, m, TODAY, lambda v: f"${v:,.0f}")
    kinds = Counter(a["key"].split(":")[0] for a in acts)
    assert ACTION_KINDS <= set(kinds), ACTION_KINDS - set(kinds)
    assert {a["key"] for a in acts if a["key"] == "clean:flags"} and {a["key"] for a in acts if a["key"] == "clean:uncat"}
    assert {"High", "Medium", "Low"} <= {a["priority"] for a in acts}
    assert "goal:Home down payment" in data["settings"]["dismissed"]
    assert all(a["key"] != "goal:Home down payment" for a in acts)  # snoozed


def test_comprehensive_data_covers_every_option():
    data = comprehensive()
    df = data["transactions"]
    assert {"Salary", "Interest", "Other income", "Fees", "Uncategorized", "Transfer",
            "Credit card payment"} <= set(df["category"])
    assert df["exclude"].any() and (df["notes"] != "").any()
    flags = set(tx.flag_table(df)["flags"])
    assert {"Possible duplicate", "Looks like a transfer"} <= flags
    assert {b["frequency"] for b in data["bills"]} >= {"Weekly", "Monthly", "Quarterly", "Yearly"}
    assert any(not b["active"] for b in data["bills"]) and any(b["autopay"] for b in data["bills"])
    assert {s["decision"] for s in data["subscriptions"]} == set(storage.SUB_DECISIONS)
    assert any(s["cancelled"] for s in data["subscriptions"])
    assert len({d["type"] for d in data["debts"]}) >= 4
    assert any(t["done"] for t in data["tasks"]) and any(not t["due_date"] for t in data["tasks"])


def test_bank_export_csv_imports_with_split_columns():
    raw = tx.read_csv_bytes(sample.bank_export_csv(TODAY))
    mapping = tx.guess_mapping(list(raw.columns))
    assert mapping["date"] == "Posted Date" and mapping["debit"] == "Debit" and mapping["credit"] == "Credit"
    rows, problems = tx.map_columns(raw, mapping, amount_mode="split", default_account="Joint checking")
    assert len(rows) == len(raw) - 2
    assert any("date" in p for p in problems) and any("amount" in p for p in problems)
    assert rows["amount"].max() == 3250.00 and rows["amount"].min() == -500.00
    assert "Possible duplicate" in set(tx.flag_table(rows)["flags"])


@pytest.mark.parametrize("key", list(storage.SCHEMAS))
def test_committed_table_csvs_import(key):
    rows, _ = storage.table_from_csv(key, (DATA / "tables" / f"{key}.csv").read_bytes())
    assert rows, key


def test_committed_backup_restores():
    data, problems = storage.from_backup_bytes((DATA / "finlife-full-sample-backup.json").read_bytes())
    assert problems == [] and len(data["transactions"]) > 250


def test_every_page_renders_with_comprehensive_data(monkeypatch, tmp_path):
    monkeypatch.setenv("FINLIFE_STORAGE", "session")
    monkeypatch.setenv("FINLIFE_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    data = sample.comprehensive_data(date.today())
    at.session_state["data"] = data
    at.session_state["base"] = copy.deepcopy(data)
    at.session_state["ver"] = at.session_state["ver"] + 1
    for screen in ["dashboard", "actions", "transactions", "budget", "accounts", "calculators", "data_page", "guide"]:
        at.switch_page(f"screens/{screen}.py")
        at.run()
        assert not at.exception, (screen, [e.message for e in at.exception])
