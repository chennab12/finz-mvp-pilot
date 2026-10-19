"""FinLife 360: one place for everyday money admin, planning and calculators.

Run with:  streamlit run app.py

No API keys, no login and no paid services. All numbers come from plain Python calculations on
the records you enter. See README.md for storage options.
"""

from __future__ import annotations

import streamlit as st

from finlife.data import sample, storage
from finlife.ui import common as ui

st.set_page_config(page_title="FinLife 360", page_icon="💠", layout="wide", initial_sidebar_state="auto")

st.markdown(
    """
    <style>
      .block-container {padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1220px;}
      div[data-testid="stMetricValue"] {font-size: 1.5rem;}
      div[data-testid="stMetric"] {background: rgba(42,120,214,0.06); border: 1px solid rgba(128,128,128,0.18);
                                   border-radius: 12px; padding: 10px 14px;}
      .fl-pill {display:inline-block; padding:1px 9px; border-radius:999px; font-size:0.78rem; font-weight:600;}
      .fl-High {background:rgba(227,73,72,.16); color:#c03636;}
      .fl-Medium {background:rgba(237,161,0,.18); color:#a06a00;}
      .fl-Low {background:rgba(27,175,122,.16); color:#12805a;}
      @media (max-width: 640px) {
        .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: 3.6rem;}
        div[data-testid="stMetricValue"] {font-size: 1.2rem;}
        h1 {font-size: 1.5rem !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state


# --- First run: choose storage and load data ----------------------------------------------------
if "data" not in ss:
    try:
        host = st.context.headers.get("host")
    except Exception:  # noqa: BLE001 - no request context (e.g. tests)
        host = None
    ss.storage_mode = storage.storage_mode(host)
    loaded = None
    if ss.storage_mode == "file":
        try:
            loaded = storage.load_from_file()
        except (ValueError, OSError) as exc:
            ss.flash_error = f"Could not read the saved data file ({exc}). Started with sample data instead."
    if loaded:
        ss.data, notes = loaded
        if notes:
            ss.flash = " ".join(notes)
    else:
        ss.data = sample.sample_data(ui.today())
    ss.base = ui.copy_data(ss.data)
    ss.ver = 0
    ss.saved_fp = storage.fingerprint(ss.data) if loaded else None


# --- Sidebar: data controls ---------------------------------------------------------------------
def cb_sample():
    ui.set_data(sample.sample_data(ui.today()), "Loaded the sample household.")


def cb_empty():
    ui.set_data(storage.empty_data(), "Started with empty data. Add accounts, transactions and budgets.")


def cb_restore():
    upload = ss.get(f"restore_{ss.ver}")
    if upload is None:
        ss.flash_error = "Choose a JSON backup file first."
        return
    try:
        restored, notes = storage.from_backup_bytes(upload.getvalue())
    except ValueError as exc:
        ss.flash_error = str(exc)
        return
    ui.set_data(restored, "Restored your backup. " + " ".join(notes))


def cb_currency():
    ss.data["settings"]["currency"] = ss.currency_pick
    ui.commit()


with st.sidebar:
    st.markdown("### 💠 FinLife 360")
    if ss.storage_mode == "file":
        st.success(f"**Saved on this computer** in `{storage.data_file()}` after every change.", icon="💾")
    else:
        st.warning("**Not saved automatically.** On a shared server your data lives only in this browser "
                   "tab. Download a backup to keep it.", icon="🔒")
    st.download_button("⬇️ Download backup (JSON)", storage.to_backup_json(ss.data),
                       f"finlife-backup-{ui.today().isoformat()}.json", "application/json", width="stretch")
    st.file_uploader("Restore a backup", type=["json"], key=f"restore_{ss.ver}")
    st.button("♻️ Restore from file", on_click=cb_restore, width="stretch")
    st.divider()
    cur = ss.data["settings"].get("currency", "USD")
    st.selectbox("Currency symbol", list(storage.CURRENCIES), index=list(storage.CURRENCIES).index(cur),
                 key="currency_pick", on_change=cb_currency,
                 help="Changes the symbol only; amounts are not converted.")
    st.button("📋 Load sample household", on_click=cb_sample, width="stretch",
              help="Replaces everything with made-up demo records.")
    confirm = st.checkbox("I want to remove all records", key="confirm_empty")
    st.button("🧹 Start with empty data", on_click=cb_empty, disabled=not confirm, width="stretch")
    st.caption("No live AI, no bank logins, no API keys. Every number is calculated from your records "
               "with rules you can read in each page's 💡 box.")


# --- Navigation ---------------------------------------------------------------------------------
pages = {
    "Overview": [
        st.Page("screens/dashboard.py", title="Dashboard", icon="📊", url_path="dashboard", default=True),
        st.Page("screens/actions.py", title="Action Center", icon="✅", url_path="actions"),
    ],
    "Money": [
        st.Page("screens/transactions.py", title="Income & Expenses", icon="💳", url_path="transactions"),
        st.Page("screens/budget.py", title="Budget & Goals", icon="🎯", url_path="budget"),
        st.Page("screens/accounts.py", title="Accounts & Net Worth", icon="🏦", url_path="accounts"),
    ],
    "Tools": [
        st.Page("screens/calculators.py", title="Calculator Center", icon="🧮", url_path="calculators"),
        st.Page("screens/data_page.py", title="Import & Export", icon="🔄", url_path="data"),
        st.Page("screens/guide.py", title="Guide & Assumptions", icon="📘", url_path="guide"),
    ],
}
for group in pages.values():
    for page in group:
        ui.PAGES[page.url_path] = page

nav = st.navigation(pages, position="top")
if ss.get("last_page") != nav.url_path:
    # Leaving a page: keep its table edits by making them the editors' new starting point.
    if "last_page" in ss:
        ui.commit()
    ss.last_page = nav.url_path

with st.container():  # always present, so a message never shifts the page layout
    ui.flash_messages()
nav.run()

# --- Persist after the page has run -------------------------------------------------------------
if ss.storage_mode == "file":
    fp = storage.fingerprint(ss.data)
    if fp != ss.get("saved_fp"):
        try:
            storage.save_to_file(ss.data)
            ss.saved_fp = fp
        except OSError as exc:
            st.error(f"Could not save to {storage.data_file()}: {exc}")
