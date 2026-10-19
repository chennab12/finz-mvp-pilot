"""Record schemas, validation, JSON backup/restore, CSV table import/export and local file persistence.

Ported from finz-admin-pilot's storage module and extended with accounts, debts, a net-worth log,
task priorities and an optional local data file.

Persistence modes
* "file": everything is saved to one JSON file (default ./finlife_data/finlife.json, or the folder in
  FINLIFE_DATA_DIR) after every change, and loaded again when the app starts. Meant for running the
  app on your own computer.
* "session": records live only in the browser session (used on shared hosting such as Streamlit
  Community Cloud, so visitors never share a file). Use the JSON backup to keep your data.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from finlife.data import transactions as tx

APP_ID = "finlife-360"
SCHEMA_VERSION = 1
MAX_BACKUP_BYTES = 10 * 1024 * 1024
MAX_TABLE_ROWS = 5000

CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "CAD": "C$", "AUD": "A$", "JPY": "¥"}
ZERO_DECIMAL = {"JPY"}

ACCOUNT_TYPES = ["Checking", "Savings", "Investment", "Retirement", "Property", "Vehicle", "Other asset"]
DEBT_TYPES = ["Credit card", "Car loan", "Student loan", "Mortgage", "Personal loan", "Other debt"]
PRIORITIES = ["High", "Medium", "Low"]
SUB_DECISIONS = ["Keep", "Review", "Cancel"]
BILLING = ["Weekly", "Monthly", "Quarterly", "Yearly"]

# Field name -> type for every record list. Types: str, float, date, bool.
SCHEMAS: dict[str, dict[str, str]] = {
    "rules": {"keyword": "str", "category": "str"},
    "budgets": {"category": "str", "monthly_budget": "float"},
    "bills": {"name": "str", "amount": "float", "frequency": "str", "next_due": "date", "category": "str",
              "autopay": "bool", "active": "bool"},
    "goals": {"name": "str", "target": "float", "saved": "float", "monthly_contribution": "float", "deadline": "date"},
    "accounts": {"name": "str", "type": "str", "balance": "float", "emergency_fund": "bool"},
    "debts": {"name": "str", "type": "str", "balance": "float", "apr": "float", "min_payment": "float",
              "next_due": "date"},
    "insurance": {"policy": "str", "provider": "str", "premium": "float", "term_months": "float",
                  "renewal_date": "date", "notes": "str"},
    "subscriptions": {"name": "str", "amount": "float", "billing": "str", "renewal_date": "date", "decision": "str",
                      "cancelled": "bool"},
    "documents": {"document": "str", "category": "str", "due_date": "date", "done": "bool", "notes": "str"},
    "tasks": {"task": "str", "priority": "str", "due_date": "date", "done": "bool", "notes": "str"},
    "net_worth_log": {"date": "date", "assets": "float", "liabilities": "float", "note": "str"},
}
LIST_KEYS = list(SCHEMAS)
TABLE_LABELS = {
    "transactions": "Transactions", "budgets": "Budgets", "bills": "Recurring bills", "goals": "Savings goals",
    "accounts": "Accounts (assets)", "debts": "Debts", "insurance": "Insurance policies",
    "subscriptions": "Subscriptions", "documents": "Documents checklist", "tasks": "Tasks",
    "net_worth_log": "Net-worth history", "rules": "Category rules",
}
DEFAULT_SETTINGS = {"currency": "USD", "starting_balance": 0.0, "is_sample": False, "emergency_months": 6.0,
                    "dismissed": {}}


def empty_data() -> dict:
    data = {key: [] for key in LIST_KEYS}
    data["rules"] = [{"keyword": k, "category": c} for k, c in tx.DEFAULT_RULES]
    data["transactions"] = tx.normalize(pd.DataFrame(columns=tx.COLUMNS))
    data["settings"] = json.loads(json.dumps(DEFAULT_SETTINGS))
    return data


# ---------------------------------------------------------------------------
# Coercion
# ---------------------------------------------------------------------------

def coerce(value, kind: str):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if kind == "float":
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").strip()
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return None if pd.isna(number) or number in (float("inf"), float("-inf")) else round(number, 2)
    if kind == "bool":
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "y")
        return bool(value)
    if kind == "date":
        if isinstance(value, (datetime, pd.Timestamp)):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        try:
            return date.fromisoformat(str(value).strip()[:10]).isoformat()
        except ValueError:
            return None
    return str(value).strip()[:300]


def clean_records(key: str, records) -> list[dict]:
    """Keep only known fields with the right types; drop rows that are entirely empty."""
    schema = SCHEMAS[key]
    out = []
    if not isinstance(records, list):
        return out
    for rec in records[:MAX_TABLE_ROWS]:
        if not isinstance(rec, dict):
            continue
        row = {f: coerce(rec.get(f), kind) for f, kind in schema.items()}
        if all(v in (None, "", False) for v in row.values()):
            continue
        out.append(row)
    return out


def clean_settings(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    if raw.get("currency") in CURRENCIES:
        settings["currency"] = raw["currency"]
    settings["starting_balance"] = coerce(raw.get("starting_balance"), "float") or 0.0
    settings["is_sample"] = bool(raw.get("is_sample"))
    months = coerce(raw.get("emergency_months"), "float")
    settings["emergency_months"] = months if months and 0 < months <= 36 else 6.0
    dismissed = raw.get("dismissed") if isinstance(raw.get("dismissed"), dict) else {}
    settings["dismissed"] = {str(k)[:120]: coerce(v, "date") for k, v in list(dismissed.items())[:500]
                             if coerce(v, "date")}
    return settings


# ---------------------------------------------------------------------------
# JSON backup / restore (also the format of the local data file)
# ---------------------------------------------------------------------------

def to_payload(data: dict) -> dict:
    payload = {"app": APP_ID, "schema_version": SCHEMA_VERSION,
               "settings": clean_settings(data.get("settings"))}
    for key in LIST_KEYS:
        payload[key] = clean_records(key, data.get(key, []))
    txs = data.get("transactions")
    if isinstance(txs, pd.DataFrame) and not txs.empty:
        out = tx.normalize(txs)
        out["date"] = out["date"].astype(str)
        payload["transactions"] = out.to_dict(orient="records")
    else:
        payload["transactions"] = []
    return payload


def to_backup_json(data: dict) -> str:
    payload = to_payload(data)
    payload["exported_at"] = datetime.now().isoformat(timespec="seconds")
    return json.dumps(payload, indent=2, default=str)


def from_payload(payload) -> tuple[dict, list[str]]:
    if not isinstance(payload, dict) or payload.get("app") != APP_ID:
        raise ValueError("This JSON file was not exported by FinLife 360.")
    notes: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        notes.append("The file came from a different app version; unknown fields were ignored.")
    data = empty_data()
    for key in LIST_KEYS:
        if key in payload:
            data[key] = clean_records(key, payload.get(key))
    data["settings"] = clean_settings(payload.get("settings"))
    raw_tx = payload.get("transactions") if isinstance(payload.get("transactions"), list) else []
    frame = pd.DataFrame([r for r in raw_tx[: tx.MAX_ROWS] if isinstance(r, dict)])
    before = len(frame)
    data["transactions"] = tx.normalize(frame)
    skipped = before - len(data["transactions"])
    if skipped:
        notes.append(f"{skipped} transaction(s) with an invalid date or amount were skipped.")
    return data, notes


def from_backup_bytes(raw: bytes) -> tuple[dict, list[str]]:
    """Parse and validate an uploaded backup. Raises ValueError for unusable files."""
    if len(raw) > MAX_BACKUP_BYTES:
        raise ValueError("Backup file is larger than 10 MB.")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Not a valid JSON file: {exc}") from exc
    return from_payload(payload)


# ---------------------------------------------------------------------------
# CSV export / import for the record tables
# ---------------------------------------------------------------------------

def table_to_csv(key: str, data: dict) -> bytes:
    if key == "transactions":
        return tx.to_export_csv(data["transactions"])
    frame = pd.DataFrame(clean_records(key, data.get(key, [])), columns=list(SCHEMAS[key]))
    return frame.to_csv(index=False).encode("utf-8")


def table_from_csv(key: str, raw: bytes) -> tuple[list[dict], list[str]]:
    """Read a CSV whose header uses this table's column names (as exported). Returns (rows, notes)."""
    if key not in SCHEMAS:
        raise ValueError("Unknown table.")
    if len(raw) > MAX_BACKUP_BYTES:
        raise ValueError("CSV file is larger than 10 MB.")
    try:
        frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"Could not read this CSV: {exc}") from exc
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    expected = list(SCHEMAS[key])
    matched = [c for c in expected if c in frame.columns]
    if not matched:
        raise ValueError(f"No matching columns. Expected some of: {', '.join(expected)}.")
    notes = []
    missing = [c for c in expected if c not in frame.columns]
    if missing:
        notes.append(f"Columns not in the file were left blank: {', '.join(missing)}.")
    extra = [c for c in frame.columns if c not in expected]
    if extra:
        notes.append(f"Ignored columns: {', '.join(extra)}.")
    rows = clean_records(key, frame.to_dict("records"))
    if len(frame) > len(rows):
        notes.append(f"{len(frame) - len(rows)} empty row(s) skipped.")
    return rows, notes


# ---------------------------------------------------------------------------
# Local file persistence
# ---------------------------------------------------------------------------

def data_dir() -> Path:
    return Path(os.environ.get("FINLIFE_DATA_DIR") or Path.cwd() / "finlife_data")


def data_file() -> Path:
    return data_dir() / "finlife.json"


def storage_mode(host: str | None) -> str:
    """'file' or 'session'. FINLIFE_STORAGE=file|session overrides; otherwise file only on localhost."""
    forced = (os.environ.get("FINLIFE_STORAGE") or "").strip().lower()
    if forced in ("file", "session"):
        return forced
    hostname = (host or "").split(":")[0].strip().lower()
    return "file" if hostname in ("localhost", "127.0.0.1", "::1", "[::1]") else "session"


def save_to_file(data: dict, path: Path | None = None) -> Path:
    """Write the data atomically (temp file + rename) so a crash never leaves half a file."""
    path = path or data_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(to_payload(data), indent=1, default=str)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".finlife-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def load_from_file(path: Path | None = None) -> tuple[dict, list[str]] | None:
    """Load the local data file, or None if there is none. Raises ValueError if it is unreadable."""
    path = path or data_file()
    if not path.exists():
        return None
    return from_backup_bytes(path.read_bytes())


def fingerprint(data: dict) -> str:
    """Cheap change detector: the serialized payload."""
    return json.dumps(to_payload(data), sort_keys=True, default=str)
