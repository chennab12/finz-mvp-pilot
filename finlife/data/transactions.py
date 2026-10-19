"""Transaction import, keyword categorisation, flags and summaries.

Sign convention everywhere: negative amount = money out, positive = money in.

How totals avoid double counting:
* Categories in EXCLUDED_CATEGORIES (Transfer, Credit card payment) never count
  as income or spending. A card purchase is counted once, when it happens on
  the card; the later payment from checking to the card is excluded.
* A positive amount in a spending category is a refund. It reduces that
  category's spending instead of being counted as income.
* Rows ticked "Exclude" (for example a confirmed duplicate) are ignored.
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import date

import pandas as pd

INCOME_CATEGORIES = ["Salary", "Interest", "Other income"]
EXCLUDED_CATEGORIES = ["Transfer", "Credit card payment"]
SPENDING_CATEGORIES = [
    "Housing", "Groceries", "Dining", "Transport", "Utilities", "Insurance",
    "Healthcare", "Subscriptions", "Shopping", "Entertainment", "Travel",
    "Education", "Gifts & donations", "Debt payments", "Fees", "Uncategorized",
]
ALL_CATEGORIES = INCOME_CATEGORIES + SPENDING_CATEGORIES + EXCLUDED_CATEGORIES

DEFAULT_RULES = [
    ("payroll", "Salary"), ("salary", "Salary"), ("direct dep", "Salary"),
    ("interest paid", "Interest"), ("interest earned", "Interest"),
    ("payment thank you", "Credit card payment"), ("card autopay", "Credit card payment"),
    ("credit card payment", "Credit card payment"), ("crd pmt", "Credit card payment"),
    ("transfer", "Transfer"), ("xfer", "Transfer"),
    ("car loan", "Debt payments"), ("student loan", "Debt payments"), ("loan payment", "Debt payments"),
    ("rent", "Housing"), ("mortgage", "Housing"), ("hoa", "Housing"),
    ("grocer", "Groceries"), ("market", "Groceries"), ("supermarket", "Groceries"),
    ("cafe", "Dining"), ("coffee", "Dining"), ("restaurant", "Dining"), ("pizza", "Dining"),
    ("taqueria", "Dining"), ("fuel", "Transport"), ("gas station", "Transport"),
    ("transit", "Transport"), ("rideshare", "Transport"), ("parking", "Transport"),
    ("electric", "Utilities"), ("water", "Utilities"), ("internet", "Utilities"),
    ("mobile", "Utilities"), ("insurance", "Insurance"), ("pharmacy", "Healthcare"),
    ("clinic", "Healthcare"), ("dental", "Healthcare"), ("streaming", "Subscriptions"),
    ("music plus", "Subscriptions"), ("cloud storage", "Subscriptions"), ("gym", "Subscriptions"),
    ("department store", "Shopping"), ("online store", "Shopping"), ("hardware", "Shopping"),
    ("cinema", "Entertainment"), ("concert", "Entertainment"), ("airline", "Travel"),
    ("hotel", "Travel"), ("tuition", "Education"), ("bookstore", "Education"),
    ("charity", "Gifts & donations"), ("fee", "Fees"),
]

TRANSFER_KEYWORDS = ["transfer", "xfer", "payment thank you", "card autopay", "zelle to", "to savings", "from savings"]
COLUMNS = ["id", "date", "description", "amount", "account", "category", "exclude", "source", "notes"]
MAX_ROWS = 20_000


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def category_group(category: str) -> str:
    if category in INCOME_CATEGORIES:
        return "income"
    if category in EXCLUDED_CATEGORIES:
        return "excluded"
    return "spending"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_AMOUNT_JUNK = re.compile(r"[^\d.\-]")


def parse_amount(value) -> float | None:
    """Parse '$1,234.50', '(12.00)', '-5', '12.00 CR' etc. Returns None if not a number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else round(float(value), 2)
    text = str(value).strip()
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    upper = text.upper()
    if upper.endswith("DR"):
        negative, text = True, text[:-2]
    elif upper.endswith("CR"):
        text = text[:-2]
    cleaned = _AMOUNT_JUNK.sub("", text)
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return round(-abs(number) if negative else number, 2)


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read an uploaded CSV as text columns, trying common encodings."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(data), dtype=str, encoding=encoding, keep_default_na=False,
                             skip_blank_lines=True, nrows=MAX_ROWS + 1)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except UnicodeDecodeError as exc:
            last_error = exc
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise ValueError(f"Could not read this CSV: {exc}") from exc
    raise ValueError(f"Could not decode this CSV: {last_error}")


def guess_mapping(columns: list[str]) -> dict:
    """Best guess for which uploaded column holds which field."""
    lower = {c: c.lower() for c in columns}

    def find(*words):
        for word in words:
            for col, low in lower.items():
                if word in low:
                    return col
        return None

    return {
        "date": find("posted date", "transaction date", "date"),
        "description": find("description", "merchant", "payee", "memo", "details", "name"),
        "amount": find("amount", "value"),
        "debit": find("debit", "withdrawal", "money out"),
        "credit": find("credit", "deposit", "money in"),
        "account": find("account"),
        "category": find("category"),
    }


def map_columns(raw: pd.DataFrame, mapping: dict, *, amount_mode: str = "single", flip_sign: bool = False,
                default_account: str = "Imported", dayfirst: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """Convert an uploaded table to the app's columns. Returns (rows, problems).

    amount_mode "single": one signed column (negative = money out).
    amount_mode "split": separate debit (out) and credit (in) columns, both positive.
    flip_sign: for exports that show purchases as positive numbers.
    Rows with an unreadable date or amount are skipped and reported.
    """
    problems: list[str] = []
    if len(raw) > MAX_ROWS:
        problems.append(f"Only the first {MAX_ROWS:,} rows were read.")
        raw = raw.head(MAX_ROWS)
    if not mapping.get("date") or not mapping.get("description"):
        raise ValueError("Choose a date column and a description column.")
    if amount_mode == "single" and not mapping.get("amount"):
        raise ValueError("Choose an amount column.")
    if amount_mode == "split" and not (mapping.get("debit") or mapping.get("credit")):
        raise ValueError("Choose a debit column, a credit column, or both.")

    dates = pd.to_datetime(raw[mapping["date"]].astype(str).str.strip(), errors="coerce", dayfirst=dayfirst,
                           format="mixed")
    out_rows = []
    skipped_date = skipped_amount = 0
    for i in range(len(raw)):
        row = raw.iloc[i]
        d = dates.iloc[i]
        if pd.isna(d):
            skipped_date += 1
            continue
        if amount_mode == "single":
            amount = parse_amount(row[mapping["amount"]])
        else:
            debit = parse_amount(row[mapping["debit"]]) if mapping.get("debit") else None
            credit = parse_amount(row[mapping["credit"]]) if mapping.get("credit") else None
            if debit is None and credit is None:
                amount = None
            else:
                amount = round(abs(credit or 0.0) - abs(debit or 0.0), 2)
        if amount is None:
            skipped_amount += 1
            continue
        if flip_sign:
            amount = -amount
        account = str(row[mapping["account"]]).strip() if mapping.get("account") else ""
        category = str(row[mapping["category"]]).strip() if mapping.get("category") else ""
        out_rows.append({
            "id": new_id(),
            "date": d.date(),
            "description": str(row[mapping["description"]]).strip()[:200],
            "amount": amount,
            "account": account or default_account,
            "category": category if category in ALL_CATEGORIES else "",
            "exclude": False,
            "source": "file" if category in ALL_CATEGORIES else "",
            "notes": "",
        })
    if skipped_date:
        problems.append(f"{skipped_date} row(s) skipped: date could not be read.")
    if skipped_amount:
        problems.append(f"{skipped_amount} row(s) skipped: amount could not be read.")
    return normalize(pd.DataFrame(out_rows, columns=COLUMNS)), problems


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a transactions frame to the expected columns and types."""
    df = df.copy() if df is not None else pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS]
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").round(2)
    df = df[df["date"].notna() & df["amount"].notna()].copy()
    for col in ("description", "account", "category", "source", "notes"):
        df[col] = df[col].fillna("").astype(str)
    df["exclude"] = df["exclude"].fillna(False).astype(bool)
    missing = df["id"].isna() | (df["id"].astype(str).str.strip() == "")
    df.loc[missing, "id"] = [new_id() for _ in range(int(missing.sum()))]
    df["id"] = df["id"].astype(str)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Categorisation and flags
# ---------------------------------------------------------------------------

def clean_rules(rules: list[dict]) -> list[tuple[str, str]]:
    out = []
    for rule in rules:
        keyword = str(rule.get("keyword") or "").strip().lower()
        category = str(rule.get("category") or "").strip()
        if keyword and category:
            out.append((keyword, category))
    return out


def suggest_category(description: str, amount: float, rules: list[tuple[str, str]]) -> str:
    """First keyword rule found in the description wins.

    Matching is case-insensitive and anchored at the start of a word, so
    "rent" matches "RENT PAYMENT" but not "CURRENT".
    """
    text = (description or "").lower()
    for keyword, category in rules:
        if re.search(r"(?<![a-z0-9])" + re.escape(keyword), text):
            return category
    return "Other income" if amount > 0 else "Uncategorized"


def apply_rules(df: pd.DataFrame, rules: list[dict], overwrite_manual: bool = False) -> pd.DataFrame:
    """Fill categories from rules. Manual corrections are kept unless overwrite_manual."""
    df = df.copy()
    cleaned = clean_rules(rules)
    for i in df.index:
        if df.at[i, "source"] == "manual" and not overwrite_manual:
            continue
        if df.at[i, "source"] == "file" and df.at[i, "category"]:
            continue
        df.at[i, "category"] = suggest_category(df.at[i, "description"], float(df.at[i, "amount"]), cleaned)
        df.at[i, "source"] = "rule"
    return df


def _norm_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def duplicate_ids(df: pd.DataFrame) -> set[str]:
    """Rows sharing date, amount and normalised description with an earlier row."""
    if df.empty:
        return set()
    key = df["date"].astype(str) + "|" + df["amount"].round(2).astype(str) + "|" + df["description"].map(_norm_text)
    dup = key.duplicated(keep="first")
    return set(df.loc[dup, "id"])


def transfer_pair_ids(df: pd.DataFrame, window_days: int = 3) -> set[str]:
    """Pairs of opposite, equal amounts in different accounts within a few days.

    These look like money moving between your own accounts (a transfer or a
    card repayment). Rows already categorised as excluded are skipped.
    """
    flagged: set[str] = set()
    work = df[~df["category"].isin(EXCLUDED_CATEGORIES) & ~df["exclude"]].copy()
    if work.empty:
        return flagged
    work["abs"] = work["amount"].abs().round(2)
    outs = work[work["amount"] < 0]
    ins = work[work["amount"] > 0]
    used: set[str] = set()
    for _, out in outs.iterrows():
        candidates = ins[(ins["abs"] == out["abs"]) & (ins["account"] != out["account"])]
        for _, inc in candidates.iterrows():
            if inc["id"] in used:
                continue
            if abs((pd.Timestamp(inc["date"]) - pd.Timestamp(out["date"])).days) <= window_days:
                flagged.update({out["id"], inc["id"]})
                used.add(inc["id"])
                break
    return flagged


def transfer_keyword_ids(df: pd.DataFrame) -> set[str]:
    mask = df["description"].str.lower().apply(lambda t: any(k in t for k in TRANSFER_KEYWORDS))
    mask &= ~df["category"].isin(EXCLUDED_CATEGORIES)
    return set(df.loc[mask, "id"])


def flag_table(df: pd.DataFrame) -> pd.DataFrame:
    """One text column of review flags per transaction id."""
    dups = duplicate_ids(df)
    pairs = transfer_pair_ids(df)
    words = transfer_keyword_ids(df)
    flags = []
    for tid in df["id"]:
        f = []
        if tid in dups:
            f.append("Possible duplicate")
        if tid in pairs:
            f.append("Possible transfer pair")
        elif tid in words:
            f.append("Looks like a transfer")
        flags.append(", ".join(f))
    return pd.DataFrame({"id": df["id"], "flags": flags})


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def counted(df: pd.DataFrame) -> pd.DataFrame:
    """Rows that count toward income or spending, with a 'group' and 'month' column."""
    if df.empty:
        return df.assign(group=pd.Series(dtype=str), month=pd.Series(dtype=str))
    work = df[~df["exclude"]].copy()
    work["group"] = work["category"].map(lambda c: category_group(c or "Uncategorized"))
    work = work[work["group"] != "excluded"]
    work["month"] = pd.to_datetime(work["date"]).dt.to_period("M").astype(str)
    return work


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Income, spending (net of refunds) and surplus per month."""
    work = counted(df)
    if work.empty:
        return pd.DataFrame(columns=["month", "income", "spending", "surplus"])
    income = work[work["group"] == "income"].groupby("month")["amount"].sum()
    spending = -work[work["group"] == "spending"].groupby("month")["amount"].sum()
    out = pd.DataFrame({"income": income, "spending": spending}).fillna(0.0)
    out["surplus"] = out["income"] - out["spending"]
    return out.sort_index().reset_index(names="month").round(2)


def category_spending(df: pd.DataFrame, month: str | None = None) -> pd.DataFrame:
    """Net spending per category (purchases minus refunds)."""
    work = counted(df)
    work = work[work["group"] == "spending"]
    if month:
        work = work[work["month"] == month]
    if work.empty:
        return pd.DataFrame(columns=["category", "spent", "refunds"])
    work = work.assign(category=work["category"].replace("", "Uncategorized"))
    spent = -work.groupby("category")["amount"].sum()
    refunds = work[work["amount"] > 0].groupby("category")["amount"].sum()
    out = pd.DataFrame({"spent": spent, "refunds": refunds}).fillna(0.0)
    return out.sort_values("spent", ascending=False).reset_index(names="category").round(2)


def full_months(df: pd.DataFrame, today: date) -> list[str]:
    """Months in the data that are fully in the past (used for averages)."""
    if df.empty:
        return []
    current = pd.Period(today, "M")
    months = sorted(pd.to_datetime(df["date"]).dt.to_period("M").unique())
    return [str(m) for m in months if m < current]


def budget_vs_actual(df: pd.DataFrame, budgets: list[dict], month: str) -> pd.DataFrame:
    actual = category_spending(df, month).set_index("category")["spent"] if not df.empty else pd.Series(dtype=float)
    rows = []
    for b in budgets:
        cat = str(b.get("category") or "").strip()
        try:
            limit = float(b.get("monthly_budget") or 0)
        except (TypeError, ValueError):
            continue
        if not cat or limit < 0:
            continue
        spent = float(actual.get(cat, 0.0))
        rows.append({"category": cat, "budget": limit, "actual": spent, "remaining": limit - spent,
                     "used_pct": (spent / limit * 100) if limit > 0 else None})
    return pd.DataFrame(rows, columns=["category", "budget", "actual", "remaining", "used_pct"]).round(2)


def to_export_csv(df: pd.DataFrame) -> bytes:
    out = df.copy()
    out["date"] = out["date"].astype(str)
    return out.to_csv(index=False).encode("utf-8")
