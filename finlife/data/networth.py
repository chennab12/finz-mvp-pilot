"""Net worth from accounts and debts, plus a dated history log (idea from stocks-retire-faqs)."""

from __future__ import annotations

from datetime import date

import pandas as pd

from finlife.data.planning import parse_date, to_float

LIQUID_TYPES = {"Checking", "Savings"}


def _positive(items: list[dict], field: str) -> list[tuple[dict, float]]:
    out = []
    for item in items:
        value = to_float(item.get(field))
        if value is not None and value > 0 and str(item.get("name") or "").strip():
            out.append((item, value))
    return out


def totals(accounts: list[dict], debts: list[dict]) -> dict:
    assets = sum(v for _, v in _positive(accounts, "balance"))
    liabilities = sum(v for _, v in _positive(debts, "balance"))
    emergency = sum(v for a, v in _positive(accounts, "balance") if a.get("emergency_fund"))
    liquid = sum(v for a, v in _positive(accounts, "balance") if a.get("type") in LIQUID_TYPES)
    return {"assets": assets, "liabilities": liabilities, "net_worth": assets - liabilities,
            "emergency_savings": emergency, "liquid": liquid}


def by_type(items: list[dict], kind_field: str = "type") -> pd.DataFrame:
    rows = [{"type": item.get(kind_field) or "Other", "balance": value} for item, value in _positive(items, "balance")]
    if not rows:
        return pd.DataFrame(columns=["type", "balance"])
    return pd.DataFrame(rows).groupby("type", as_index=False)["balance"].sum().sort_values("balance", ascending=False)


def record_snapshot(log: list[dict], accounts: list[dict], debts: list[dict], today: date, note: str = "") -> list[dict]:
    """Add (or replace) today's entry in the net-worth history. Returns the new, date-sorted log."""
    t = totals(accounts, debts)
    entry = {"date": today.isoformat(), "assets": round(t["assets"], 2), "liabilities": round(t["liabilities"], 2),
             "note": note}
    kept = [e for e in log if str(e.get("date")) != today.isoformat()]
    return sorted(kept + [entry], key=lambda e: str(e.get("date")))


def history(log: list[dict]) -> pd.DataFrame:
    rows = []
    for e in log:
        d = parse_date(e.get("date"))
        assets, liabilities = to_float(e.get("assets")), to_float(e.get("liabilities"))
        if d is None or assets is None or liabilities is None:
            continue
        rows.append({"date": d, "assets": assets, "liabilities": liabilities, "net_worth": assets - liabilities})
    frame = pd.DataFrame(rows, columns=["date", "assets", "liabilities", "net_worth"])
    return frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
