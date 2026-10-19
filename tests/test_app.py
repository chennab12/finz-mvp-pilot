"""Run the real Streamlit app headlessly and click through every page."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
SCREENS = ["dashboard", "actions", "transactions", "budget", "accounts", "calculators", "data_page", "guide"]


@pytest.fixture(autouse=True)
def session_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("FINLIFE_STORAGE", "session")
    monkeypatch.setenv("FINLIFE_DATA_DIR", str(tmp_path))


def run(at):
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def start():
    return run(AppTest.from_file(APP, default_timeout=60))


def go(at, screen):
    at.switch_page(f"screens/{screen}.py")
    return run(at)


def test_every_page_renders_with_sample_data():
    at = start()
    assert any("Sample data" in i.value for i in at.info)
    for screen in SCREENS:
        go(at, screen)
        assert at.title, screen


def test_dashboard_numbers():
    at = start()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["💵 Income"].startswith("$")
    assert metrics["🛟 Emergency fund"].endswith("months")


def test_every_calculator_renders_without_errors():
    from finlife.views.calculators import CALCS

    at = go(start(), "calculators")
    for choice in CALCS:
        at.button_group(key="calc_pick").set_value(choice)
        run(at)
        assert at.subheader[0].value == choice
        assert not at.error, (choice, [e.value for e in at.error])
        assert len(at.metric) >= 2, choice


def test_quick_add_transaction():
    at = go(start(), "transactions")
    before = len(at.session_state["data"]["transactions"])
    at.text_input(key="qa_desc").set_value("Farmers market")
    at.number_input(key="qa_amount").set_value(42.5)
    at.button[[b.label for b in at.button].index("Add")].click()
    run(at)
    df = at.session_state["data"]["transactions"]
    assert len(df) == before + 1
    row = df[df["description"] == "Farmers market"].iloc[0]
    assert row["amount"] == -42.5 and row["category"] == "Groceries"


def test_action_done_moves_bill_forward():
    at = go(start(), "actions")
    bill = next(b for b in at.session_state["data"]["bills"] if b["name"] == "Auto insurance")
    due = bill["next_due"]
    done = next(b for b in at.button if b.key and b.key.startswith("done_due:bills:"))
    done.click()
    run(at)
    bill = next(b for b in at.session_state["data"]["bills"] if b["name"] == "Auto insurance")
    assert bill["next_due"] > due


def test_snooze_hides_action():
    at = go(start(), "actions")
    snooze = next(b for b in at.button if b.key and b.key.startswith("snooze_"))
    snooze.click()
    run(at)
    assert at.session_state["data"]["settings"]["dismissed"]


def test_empty_data_and_sample_reload():
    at = start()
    at.checkbox(key="confirm_empty").check()
    run(at)
    next(b for b in at.button if b.label.startswith("🧹")).click()
    run(at)
    assert at.session_state["data"]["transactions"].empty
    for screen in SCREENS:
        go(at, screen)
    next(b for b in at.button if b.label.startswith("📋")).click()
    run(at)
    assert not at.session_state["data"]["transactions"].empty


def test_currency_switch():
    at = start()
    at.selectbox(key="currency_pick").set_value("EUR")
    run(at)
    assert {m.label: m.value for m in at.metric}["💵 Income"].startswith("€")


def test_file_mode_saves_and_reloads(monkeypatch, tmp_path):
    monkeypatch.setenv("FINLIFE_STORAGE", "file")
    at = start()
    saved = tmp_path / "finlife.json"
    assert saved.exists()
    at.selectbox(key="currency_pick").set_value("GBP")
    run(at)
    again = start()
    assert again.session_state["data"]["settings"]["currency"] == "GBP"
