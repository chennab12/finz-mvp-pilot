from datetime import date

import pandas as pd

from finlife import actions, metrics
from finlife.data import sample, storage
from finlife.data import transactions as tx

TODAY = date(2026, 10, 19)
fmt = "${:,.0f}".format


def built(data):
    return actions.build_actions(data, metrics.compute(data, TODAY), TODAY, fmt)


def test_metrics_on_sample():
    data = sample.sample_data(TODAY)
    m = metrics.compute(data, TODAY)
    assert m["full_months"] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    assert m["last_full"]["month"] == "2026-09"
    assert 0.2 < m["savings_rate"] < 0.5
    assert m["essentials_basis"].startswith("average of 6")
    assert m["emergency_months"] == m["emergency_savings"] / m["essentials"]
    assert [d["name"] for d in m["high_apr_debts"]] == ["Credit card"]


def test_actions_are_sorted_and_explain_themselves():
    acts = built(sample.sample_data(TODAY))
    assert acts and [a["score"] for a in acts] == sorted((a["score"] for a in acts), reverse=True)
    assert acts[0]["priority"] == "High"
    for a in acts:
        assert a["why"] and a["how"] and a["rule"] and a["priority"] in storage.PRIORITIES
    titles = " ".join(a["title"] for a in acts)
    assert "Auto insurance" in titles  # overdue, not on autopay
    assert "Electricity" not in titles  # on autopay -> left to the "coming up" list
    assert "Pay down Credit card" in titles
    assert "Cancel News app" in titles


def test_empty_data_has_no_actions_and_no_crash():
    data = storage.empty_data()
    assert built(data) == []
    ladder = actions.checkup_ladder(metrics.compute(data, TODAY))
    assert [s["status"] for s in ladder][:2] == ["done", "current"]


def test_overspending_month_is_high_priority():
    data = storage.empty_data()
    data["transactions"] = tx.normalize(pd.DataFrame([
        {"date": "2026-09-01", "description": "pay", "amount": 1000, "category": "Salary"},
        {"date": "2026-09-02", "description": "rent", "amount": -1500, "category": "Housing"}]))
    acts = built(data)
    assert acts[0]["key"] == "cashflow:2026-09" and acts[0]["priority"] == "High"


def test_snooze_hides_rule_actions_until_date():
    data = sample.sample_data(TODAY)
    key = next(a["key"] for a in built(data) if a["kind"] == "rule")
    actions.snooze(data, key, TODAY)
    assert key not in {a["key"] for a in built(data)}
    later = date(2026, 11, 30)
    m = metrics.compute(data, later)
    assert key in {a["key"] for a in actions.build_actions(data, m, later, fmt)} or key.startswith("budget:")


def test_low_task_becomes_medium_when_overdue():
    data = storage.empty_data()
    data["tasks"] = [{"task": "File papers", "priority": "Low", "due_date": "2026-10-01", "done": False}]
    (a,) = built(data)
    assert a["priority"] == "Medium" and a["kind"] == "task"


def test_ladder_marks_first_unmet_step_current():
    m = metrics.compute(sample.sample_data(TODAY), TODAY)
    ladder = actions.checkup_ladder(m)
    assert sum(s["status"] == "current" for s in ladder) == 1
    assert ladder[0]["status"] == "current"  # the sample has an overdue bill
