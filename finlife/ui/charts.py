"""Plotly chart builders shared by the pages. Every chart is paired with a table or metric on its page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from finlife.ui.common import AQUA, BLUE, GREEN, ORANGE, RED, SERIES, VIOLET, YELLOW, style_fig


def income_vs_spending(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=summary["month"], y=summary["income"], name="Income", marker_color=AQUA)
    fig.add_bar(x=summary["month"], y=summary["spending"], name="Spending", marker_color=ORANGE)
    fig.add_scatter(x=summary["month"], y=summary["surplus"], name="Left over", mode="lines+markers",
                    line=dict(color=BLUE, width=3))
    fig.update_layout(title="Income vs spending by month", barmode="group")
    return style_fig(fig)


def category_donut(cats: pd.DataFrame, title: str, top: int = 7) -> go.Figure:
    cats = cats[cats["spent"] > 0].sort_values("spent", ascending=False)
    if len(cats) > top + 1:
        other = pd.DataFrame([{"category": "Other", "spent": cats["spent"].iloc[top:].sum()}])
        cats = pd.concat([cats.head(top)[["category", "spent"]], other], ignore_index=True)
    fig = go.Figure(go.Pie(labels=cats["category"], values=cats["spent"], hole=0.55, sort=True,
                           marker=dict(colors=(SERIES * 3)[: len(cats)]), textinfo="percent",
                           hovertemplate="%{label}: %{value:,.2f} (%{percent})<extra></extra>"))
    fig = style_fig(fig, height=380, money_axis=None)
    fig.update_layout(title=title, showlegend=True,
                      legend=dict(orientation="v", x=1.02, xanchor="left", y=0.5, yanchor="middle"))
    return fig


def budget_bars(bva: pd.DataFrame, title: str) -> go.Figure:
    bva = bva.sort_values("budget")
    colors = [RED if a > b else GREEN for a, b in zip(bva["actual"], bva["budget"])]
    fig = go.Figure()
    fig.add_bar(y=bva["category"], x=bva["budget"], name="Budget", orientation="h",
                marker_color="rgba(128,128,128,0.30)")
    fig.add_bar(y=bva["category"], x=bva["actual"], name="Spent", orientation="h", marker_color=colors, width=0.45)
    fig.update_layout(title=title, barmode="overlay", hovermode="y unified")
    return style_fig(fig, height=max(300, 34 * len(bva) + 90), money_axis="x")


def net_worth_trend(hist: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=hist["date"], y=hist["assets"], name="Assets", mode="lines", line=dict(color=AQUA, width=2))
    fig.add_scatter(x=hist["date"], y=hist["liabilities"], name="Debts", mode="lines", line=dict(color=ORANGE, width=2))
    fig.add_scatter(x=hist["date"], y=hist["net_worth"], name="Net worth", mode="lines+markers",
                    line=dict(color=BLUE, width=3), fill="tozeroy", fillcolor="rgba(42,120,214,0.10)")
    fig.update_layout(title="Net worth over time")
    return style_fig(fig)


def horizontal_totals(frame: pd.DataFrame, label: str, value: str, title: str, color: str = VIOLET) -> go.Figure:
    frame = frame.sort_values(value)
    fig = go.Figure(go.Bar(y=frame[label], x=frame[value], orientation="h", marker_color=color))
    fig.update_layout(title=title, hovermode="y unified")
    return style_fig(fig, height=max(240, 34 * len(frame) + 90), money_axis="x")


def balance_lines(frame: pd.DataFrame, x: str, series: dict, title: str, x_title: str) -> go.Figure:
    fig = go.Figure()
    for i, (col, name) in enumerate(series.items()):
        fig.add_scatter(x=frame[x], y=frame[col], name=name, mode="lines",
                        line=dict(color=SERIES[i % len(SERIES)], width=3 if i == 0 else 2,
                                  dash="solid" if i == 0 else "dot"))
    fig.update_layout(title=title, xaxis_title=x_title)
    return style_fig(fig)


def stacked_growth(rows: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=rows["Year"], y=rows["Contributions"], name="Money you put in", marker_color=BLUE)
    fig.add_bar(x=rows["Year"], y=rows["Growth"], name="Growth", marker_color=AQUA)
    fig.add_scatter(x=rows["Year"], y=rows["Without fees"], name="Without fees", mode="lines",
                    line=dict(color=YELLOW, width=2, dash="dot"))
    fig.add_scatter(x=rows["Year"], y=rows["Today's dollars"], name="In today's dollars", mode="lines",
                    line=dict(color=VIOLET, width=2))
    fig.update_layout(title="Projected balance by year", barmode="stack", xaxis_title="Year")
    return style_fig(fig)


def gauge(value: float, target: float, title: str, suffix: str = "") -> go.Figure:
    top = max(target * 1.5, value * 1.1, 1)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number=dict(suffix=suffix, valueformat=".1f"),
        gauge=dict(axis=dict(range=[0, top]), bar=dict(color=BLUE),
                   steps=[dict(range=[0, target * 0.5], color="rgba(227,73,72,0.20)"),
                          dict(range=[target * 0.5, target], color="rgba(237,161,0,0.20)"),
                          dict(range=[target, top], color="rgba(27,175,122,0.20)")],
                   threshold=dict(line=dict(color=GREEN, width=3), value=target))))
    fig.update_layout(title=title)
    return style_fig(fig, height=250, money_axis=None)
