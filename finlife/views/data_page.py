"""Import & Export: CSV for every table, full JSON backup, and where your data is stored."""

from __future__ import annotations

import streamlit as st

from finlife.data import storage
from finlife.ui import common as ui

ss = st.session_state
TABLES = [k for k in storage.TABLE_LABELS if k != "transactions"]


def render() -> None:
    data = ui.data()
    st.title("🔄 Import & Export")
    st.caption("Move your data in and out as CSV (open it in Excel or Google Sheets) or as one JSON backup file.")

    st.markdown("#### Where your data lives")
    if ss.storage_mode == "file":
        st.success(f"Saved automatically to **{storage.data_file()}** on this computer after every change. "
                   "Set the `FINLIFE_DATA_DIR` environment variable to use another folder.", icon="💾")
    else:
        st.warning("This app is running on a shared server, so nothing is saved between visits. Download the JSON "
                   "backup below and restore it from the sidebar next time. To save automatically, run the app on "
                   "your own computer (see README).", icon="🔒")

    st.markdown("#### ⬇️ Export")
    c = st.columns(3)
    c[0].download_button("Full backup (JSON)", storage.to_backup_json(data),
                         f"finlife-backup-{ui.today().isoformat()}.json", "application/json", width="stretch")
    c[1].download_button("Transactions (CSV)", storage.table_to_csv("transactions", data),
                         f"finlife-transactions-{ui.today().isoformat()}.csv", "text/csv", width="stretch")
    pick = c[2].selectbox("Another table (CSV)", TABLES, format_func=lambda k: storage.TABLE_LABELS[k], key="exp_pick")
    c[2].download_button(f"Download {storage.TABLE_LABELS[pick].lower()}", storage.table_to_csv(pick, data),
                         f"finlife-{pick}-{ui.today().isoformat()}.csv", "text/csv", width="stretch")

    st.markdown("#### ⬆️ Import a table from CSV")
    st.caption("Use the same column names as the export (download one first as a template). Bank or card statements "
               "go through **Income & Expenses → Import a bank or card CSV**, which lets you match any column names.")
    c = st.columns([1, 2])
    key = c[0].selectbox("Table", TABLES, format_func=lambda k: storage.TABLE_LABELS[k], key="imp_pick")
    c[0].caption("Columns: " + ", ".join(storage.SCHEMAS[key]))
    upload = c[1].file_uploader("CSV file", type=["csv"], key=f"imp_file_{ss.ver}")
    if upload is not None:
        try:
            rows, notes = storage.table_from_csv(key, upload.getvalue())
        except ValueError as exc:
            st.error(str(exc))
            return
        for n in notes:
            st.info(n)
        st.dataframe(ui.records_frame(key, rows).head(20), hide_index=True, width="stretch")
        mode = st.radio("Import mode", ["Add to existing", "Replace existing"], horizontal=True, key=f"imp_mode_{ss.ver}")
        if st.button(f"✅ Import {len(rows)} row(s) into {storage.TABLE_LABELS[key].lower()}", type="primary",
                     disabled=not rows):
            data[key] = rows if mode == "Replace existing" else data[key] + rows
            ui.commit(f"Imported {len(rows)} row(s) into {storage.TABLE_LABELS[key].lower()}.")
            st.rerun()
