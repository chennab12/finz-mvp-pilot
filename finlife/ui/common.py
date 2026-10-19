"""Shared Streamlit helpers: session state, money formatting, Plotly styling and editable tables.

State model (from finz-admin-pilot): `ss.data` holds the current records; `ss.base` feeds the data
editors. Editors keep their own pending edits until `commit()` copies data -> base and bumps
`ss.ver`, so every editor restarts from the saved records. app.py also commits when you switch
pages, so edits are never lost.
"""

from __future__ import annotations

import copy
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finlife.data import storage

ss = st.session_state

# Categorical palette in fixed order (from finz-admin-pilot; checked for colour-vision deficiency).
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
PAGES: dict = {}  # filled by app.py: name -> st.Page, used for links between pages


def today() -> date:
    return date.today()


def data() -> dict:
    return ss.data


def copy_data(d: dict) -> dict:
    return {k: (v.copy() if isinstance(v, pd.DataFrame) else copy.deepcopy(v)) for k, v in d.items()}


def commit(message: str | None = None) -> None:
    ss.base = copy_data(ss.data)
    ss.ver = ss.get("ver", 0) + 1
    if message:
        ss.flash = message


def set_data(new: dict, message: str) -> None:
    """Replace all records. Call from a widget callback (it also resets the currency picker)."""
    ss.data = new
    ss["currency_pick"] = new["settings"].get("currency", "USD")
    commit(message)


def currency() -> tuple[str, int]:
    cur = ss.data["settings"].get("currency", "USD")
    return storage.CURRENCIES.get(cur, "$"), (0 if cur in storage.ZERO_DECIMAL else 2)


def fmt(value: float | None, decimals: int | None = None) -> str:
    if value is None or pd.isna(value):
        return "—"
    sym, dec = currency()
    dec = dec if decimals is None else decimals
    sign = "-" if value < 0 else ""
    return f"{sign}{sym}{abs(value):,.{dec}f}"


def fmt0(value: float | None) -> str:
    return fmt(value, 0)


def md(text: str) -> str:
    """Escape $ for Markdown, where a pair of $ signs would start a math formula."""
    return text.replace("$", r"\$")


def money_col(label: str, **kwargs):
    cur = ss.data["settings"].get("currency", "USD")
    preset = {"USD": "dollar", "EUR": "euro", "JPY": "yen"}.get(cur)
    if preset:
        return st.column_config.NumberColumn(label, format=preset, **kwargs)
    sym, _ = currency()
    return st.column_config.NumberColumn(f"{label} ({sym.strip()})", format="localized", **kwargs)


def date_col(label: str, **kw):
    return st.column_config.DateColumn(label, format="YYYY-MM-DD", **kw)


def style_fig(fig: go.Figure, height: int = 340, money_axis: str | None = "y") -> go.Figure:
    sym, _ = currency()
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=56, b=8), hovermode="x unified",
                      title=dict(x=0, xanchor="left", y=0.98, yanchor="top", font=dict(size=15)),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left", title_text=""),
                      bargap=0.25, bargroupgap=0.08, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=True, zerolinecolor="rgba(128,128,128,0.5)")
    if money_axis == "y":
        fig.update_yaxes(tickprefix=sym, separatethousands=True)
    elif money_axis == "x":
        fig.update_xaxes(tickprefix=sym, separatethousands=True)
    return fig


def show_fig(fig: go.Figure) -> None:
    st.plotly_chart(fig, config=PLOT_CONFIG, width="stretch")


def explain(title: str, body: str) -> None:
    """A collapsed 'how this works' box in plain English."""
    with st.expander(f"💡 {title}"):
        st.markdown(body)


def estimate_note(text: str) -> None:
    st.caption(f"📐 **Estimate.** {text}")


def sample_banner() -> None:
    if ss.data["settings"].get("is_sample"):
        st.info("**Sample data.** These are made-up records for a fictional household, not anyone's real "
                "finances. Use **Start with empty data** in the sidebar before adding your own.", icon="📋")


def flash_messages() -> None:
    if ss.get("flash"):
        st.success(ss.pop("flash"), icon="✅")
    if ss.get("flash_error"):
        st.error(ss.pop("flash_error"), icon="⚠️")


def page_link(name: str, label: str, icon: str | None = None) -> None:
    page = PAGES.get(name)
    if page is not None:
        st.page_link(page, label=label, icon=icon)


# --- Editable record tables -------------------------------------------------

def records_frame(key: str, records: list[dict]) -> pd.DataFrame:
    schema = storage.SCHEMAS[key]
    df = pd.DataFrame(records, columns=list(schema))
    for field, kind in schema.items():
        if kind == "date":
            df[field] = pd.to_datetime(df[field], errors="coerce")
        elif kind == "float":
            df[field] = pd.to_numeric(df[field], errors="coerce").astype(float)
        elif kind == "bool":
            df[field] = df[field].map(lambda v: (field == "active") if v is None or pd.isna(v) else bool(v)).astype(bool)
        else:
            df[field] = df[field].fillna("").astype(str)
    return df


def edit_records(key: str, column_config: dict, height: int | str = "auto", column_order: list | None = None) -> list[dict]:
    """Editable table for one record list. Edits apply to ss.data immediately."""
    df = records_frame(key, ss.base.get(key, []))
    edited = st.data_editor(df, key=f"ed_{key}_{ss.ver}", column_config=column_config, num_rows="dynamic",
                            hide_index=True, width="stretch", height=height, column_order=column_order)
    ss.data[key] = storage.clean_records(key, edited.to_dict("records"))
    return ss.data[key]


def csv_download(key: str, label: str | None = None) -> None:
    st.download_button(label or f"⬇️ Export {storage.TABLE_LABELS[key].lower()} (CSV)",
                       storage.table_to_csv(key, ss.data), f"finlife-{key}-{today().isoformat()}.csv", "text/csv",
                       key=f"dl_{key}_{ss.ver}")
