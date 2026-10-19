"""Income & Expenses: add, import, categorize and correct transactions (from finz-admin-pilot)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finlife.data import storage
from finlife.data import transactions as tx
from finlife.ui import common as ui

ss = st.session_state


def _add_one() -> None:
    desc = (ss.get("qa_desc") or "").strip()
    amount = ss.get("qa_amount") or 0.0
    if not desc or amount <= 0:
        ss.flash_error = "Enter a description and an amount above zero."
        return
    signed = amount if ss.qa_kind == "Money in" else -amount
    category = ss.qa_cat
    if category == "(suggest from rules)":
        category = tx.suggest_category(desc, signed, tx.clean_rules(ss.data["rules"]))
    row = pd.DataFrame([{"id": tx.new_id(), "date": ss.qa_date, "description": desc[:200], "amount": signed,
                         "account": (ss.get("qa_account") or "Manual").strip() or "Manual", "category": category,
                         "exclude": False, "source": "manual", "notes": ""}])
    ss.data["transactions"] = tx.normalize(pd.concat([ss.data["transactions"], row], ignore_index=True))
    ui.commit(f"Added '{desc}' ({ui.fmt(signed)}) as {category}.")
    ss.qa_desc, ss.qa_amount = "", 0.0


def _import_section(data: dict) -> None:
    with st.expander("⬆️ Import a bank or card CSV", expanded=data["transactions"].empty):
        st.markdown("Upload an export from your bank or card, check which column is which, preview, then import. "
                    "The file is read in memory; nothing is sent anywhere.")
        upload = st.file_uploader("CSV file", type=["csv"], key=f"csv_{ss.ver}")
        if upload is None:
            return
        try:
            raw = tx.read_csv_bytes(upload.getvalue())
        except ValueError as exc:
            st.error(str(exc))
            return
        if raw.empty:
            st.warning("This file has no rows.")
            return
        st.markdown("**1. What's in the file** (first 5 rows)")
        st.dataframe(raw.head(5), hide_index=True, width="stretch")
        guess = tx.guess_mapping(list(raw.columns))
        cols = ["—"] + list(raw.columns)

        def pick(label, field, column, help_text=None):
            default = guess.get(field)
            return column.selectbox(label, cols, index=cols.index(default) if default in cols else 0,
                                    key=f"map_{field}_{ss.ver}", help=help_text)

        st.markdown("**2. Match the columns**")
        c1, c2 = st.columns(2)
        mapping = {"date": pick("Date column", "date", c1), "description": pick("Description column", "description", c2)}
        mode = st.radio("Amounts are in…", ["One column (money out is negative)", "Separate money-out and money-in columns"],
                        horizontal=True, key=f"amode_{ss.ver}")
        c3, c4 = st.columns(2)
        if mode.startswith("One"):
            mapping["amount"] = pick("Amount column", "amount", c3)
            flip = c4.checkbox("Purchases are positive in this file (flip signs)", key=f"flip_{ss.ver}",
                               help="Many card exports show purchases as positive numbers.")
        else:
            mapping["debit"] = pick("Money-out (debit) column", "debit", c3)
            mapping["credit"] = pick("Money-in (credit) column", "credit", c4)
            flip = False
        c5, c6 = st.columns(2)
        mapping["account"] = pick("Account column (optional)", "account", c5)
        mapping["category"] = pick("Category column (optional)", "category", c6,
                                   "Used only when the value matches one of this app's categories.")
        c7, c8 = st.columns(2)
        default_account = c7.text_input("Account name if no column", value=upload.name.rsplit(".", 1)[0][:40],
                                        key=f"acct_{ss.ver}")
        dayfirst = c8.checkbox("Dates are day-first (31/12/2026)", key=f"dayfirst_{ss.ver}")
        mapping = {k: (None if v == "—" else v) for k, v in mapping.items()}
        try:
            mapped, problems = tx.map_columns(raw, mapping, amount_mode="single" if mode.startswith("One") else "split",
                                              flip_sign=flip, default_account=default_account or "Imported",
                                              dayfirst=dayfirst)
            mapped = tx.apply_rules(mapped, data["rules"])
        except ValueError as exc:
            st.warning(str(exc))
            return
        st.markdown(f"**3. Preview**: {len(mapped)} of {len(raw)} rows readable")
        for p in problems:
            st.warning(p)
        st.dataframe(mapped.head(10)[["date", "description", "amount", "account", "category"]], hide_index=True,
                     width="stretch", column_config={"amount": ui.money_col("Amount"), "category": "Suggested category"})
        how = st.radio("Import mode", ["Add to existing", "Replace existing"], horizontal=True, key=f"imode_{ss.ver}")
        if st.button("✅ Import transactions", type="primary", disabled=mapped.empty):
            new = mapped if how == "Replace existing" else tx.normalize(
                pd.concat([data["transactions"], mapped], ignore_index=True))
            data["transactions"] = new
            if how == "Replace existing":
                data["settings"]["is_sample"] = False
            ui.commit(f"Imported {len(mapped)} transactions. Check 'Needs review' below.")
            st.rerun()


def render() -> None:
    data = ui.data()
    st.title("💳 Income & Expenses")
    st.caption("Every transaction in one table. **Negative = money out, positive = money in.** Change any category, "
               "add rows, or tick Exclude to leave a row out of all totals.")
    ui.sample_banner()

    with st.form("quick_add", clear_on_submit=False, border=True):
        st.markdown("**➕ Add a transaction**")
        c = st.columns([1.1, 2.2, 1.1, 1.3])
        c[0].radio("Type", ["Money out", "Money in"], key="qa_kind")
        c[1].text_input("Description", key="qa_desc", placeholder="e.g. Farmers market")
        c[2].number_input("Amount", min_value=0.0, step=1.0, key="qa_amount")
        c[3].date_input("Date", value=ui.today(), key="qa_date")
        c = st.columns([2, 2, 1])
        c[0].selectbox("Category", ["(suggest from rules)"] + tx.ALL_CATEGORIES, key="qa_cat")
        c[1].text_input("Account", value="Checking", key="qa_account")
        c[2].form_submit_button("Add", type="primary", on_click=_add_one, width="stretch")

    _import_section(data)

    with st.expander("🏷️ Category rules (how categories are suggested)"):
        st.caption("A rule matches when its keyword starts a word in the description (case-insensitive): "
                   "'rent' matches *RENT PAYMENT* but not *CURRENT*. Rules are checked top to bottom; the first match "
                   "wins. With no match, money in becomes *Other income* and money out *Uncategorized*.")
        ui.edit_records("rules", {
            "keyword": st.column_config.TextColumn("Keyword", required=True),
            "category": st.column_config.SelectboxColumn("Category", options=tx.ALL_CATEGORIES, required=True),
        }, height=300)
        overwrite = st.checkbox("Also overwrite my manual corrections", value=False)
        if st.button("🔁 Re-apply rules to all transactions"):
            data["transactions"] = tx.apply_rules(data["transactions"], data["rules"], overwrite_manual=overwrite)
            ui.commit("Re-applied the rules" + (" to every row." if overwrite else "; your manual corrections were kept."))
            st.rerun()

    base_tx = ss.base["transactions"]
    if base_tx.empty and data["transactions"].empty:
        st.info("No transactions yet. Add one above, import a CSV, or load the sample household from the sidebar.")
        return

    st.markdown("#### ✏️ All transactions")
    c = st.columns([2, 2, 1])
    search = c[0].text_input("Search descriptions", key="tx_search", placeholder="e.g. market", on_change=ui.commit)
    cat_filter = c[1].multiselect("Categories", tx.ALL_CATEGORIES, key="tx_cats", on_change=ui.commit)
    view = base_tx.sort_values("date", ascending=False).reset_index(drop=True)
    filtered = bool(search or cat_filter)
    if search:
        view = view[view["description"].str.contains(search, case=False, regex=False)]
    if cat_filter:
        view = view[view["category"].isin(cat_filter)]
    c[2].metric("Rows shown", f"{len(view)} / {len(base_tx)}")
    edited = st.data_editor(
        view, key=f"ed_tx_{ss.ver}", num_rows="dynamic", hide_index=True,
        width="stretch", height=430,
        column_order=["exclude", "date", "description", "amount", "category", "account", "source", "notes"],
        column_config={
            "exclude": st.column_config.CheckboxColumn("Exclude", help="Leave this row out of all totals.",
                                                       default=False, width="small"),
            "date": ui.date_col("Date", required=True),
            "description": st.column_config.TextColumn("Description", width="medium", required=True),
            "amount": ui.money_col("Amount", required=True, help="Negative = money out, positive = money in."),
            "category": st.column_config.SelectboxColumn("Category", options=tx.ALL_CATEGORIES),
            "account": st.column_config.TextColumn("Account"),
            "source": st.column_config.TextColumn("Category from", disabled=True,
                                                  help="rule = keyword rule, manual = your change, file = CSV column"),
            "notes": st.column_config.TextColumn("Notes"),
        })
    current = tx.normalize(edited)
    before = base_tx.set_index("id")["category"]
    changed = current["id"].map(before).fillna("__new__") != current["category"]
    current.loc[changed, "source"] = "manual"
    current.loc[current["category"] == "", "category"] = "Uncategorized"
    if filtered:
        # Rows hidden by the filter are kept; rows deleted from the filtered view are removed.
        hidden = base_tx[~base_tx["id"].isin(view["id"])]
        data["transactions"] = tx.normalize(pd.concat([hidden, current], ignore_index=True))
    else:
        data["transactions"] = current

    df_now = data["transactions"]
    if not df_now.empty:
        flags = tx.flag_table(df_now)
        flagged = df_now.merge(flags, on="id")
        flagged = flagged[(flagged["flags"] != "") & ~flagged["exclude"]]
        st.markdown("#### 🚩 Needs review")
        if flagged.empty:
            st.success("No possible duplicates or unmarked transfers.", icon="👍")
        else:
            st.caption("*Possible duplicate* = same date, amount and description as an earlier row. *Transfer pair* = "
                       "equal and opposite amounts in two of your accounts within 3 days.")
            st.dataframe(flagged[["flags", "date", "description", "amount", "account", "category"]], hide_index=True,
                         width="stretch", column_config={"flags": "Flag", "date": "Date", "description": "Description",
                                                            "amount": ui.money_col("Amount"), "account": "Account",
                                                            "category": "Category"})
            f1, f2 = st.columns(2)
            dup_ids = tx.duplicate_ids(df_now)
            pair_ids = (tx.transfer_pair_ids(df_now) | tx.transfer_keyword_ids(df_now)) - dup_ids
            if f1.button(f"Exclude {len(dup_ids)} possible duplicate(s)", disabled=not dup_ids, width="stretch"):
                data["transactions"].loc[data["transactions"]["id"].isin(dup_ids), "exclude"] = True
                ui.commit("Excluded the later copy of each possible duplicate.")
                st.rerun()
            if f2.button(f"Mark {len(pair_ids)} row(s) as Transfer", disabled=not pair_ids, width="stretch"):
                mask = data["transactions"]["id"].isin(pair_ids)
                data["transactions"].loc[mask, ["category", "source"]] = ["Transfer", "manual"]
                ui.commit("Marked those rows as transfers; they no longer count as income or spending.")
                st.rerun()
        counted = tx.counted(df_now)
        st.caption(f"{len(df_now)} rows · {len(counted)} counted in totals · {int(df_now['exclude'].sum())} excluded · "
                   f"{int(df_now['category'].isin(tx.EXCLUDED_CATEGORIES).sum())} transfers or card repayments left out")
        ui.csv_download("transactions", "⬇️ Export transactions (CSV)")

    ui.explain("How totals avoid double counting", """
- A **card purchase** is counted once, on the card. The later **Credit card payment** from checking is left out.
- **Transfer** rows (for example checking → savings) are left out: moving your own money is not spending.
- A **refund** (money in, in a spending category) lowers that category's spending instead of counting as income.
- Tick **Exclude** for anything that should not count, such as a confirmed duplicate.
""")
