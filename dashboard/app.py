from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.utils import get_connection as _get_conn


@st.cache_resource
def _get_db_connection():
    return _get_conn()


def load_summary(conn, ticker: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM gold.summary WHERE ticker = ?", [ticker]
    ).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def load_prices(conn, ticker: str, days: int) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    return conn.execute(
        """SELECT * FROM silver.prices
           WHERE ticker = ? AND date >= ?
           ORDER BY date""",
        [ticker, cutoff],
    ).df()


def rsi_signal(rsi) -> str:
    if pd.isna(rsi):
        return "N/A"
    if rsi > 70:
        return "Overbought"
    if rsi < 30:
        return "Oversold"
    return "Neutral"


def fmt_volume(v) -> str:
    if pd.isna(v):
        return "N/A"
    v = float(v)
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(int(v))


def fig_candlestick(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC",
    ))
    for col, color, name in [
        ("ma_7", "#f59e0b", "MA7"),
        ("ma_21", "#10b981", "MA21"),
        ("ma_50", "#6366f1", "MA50"),
    ]:
        valid = df[["date", col]].dropna()
        fig.add_trace(go.Scatter(
            x=valid["date"], y=valid[col],
            name=name, line=dict(color=color, width=1.5),
        ))
    fig.update_layout(xaxis_rangeslider_visible=False, height=400)
    return fig


def fig_volume(df: pd.DataFrame) -> go.Figure:
    colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(df["close"], df["open"])
    ]
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["volume"], marker_color=colors, name="Volume",
    ))
    fig.update_layout(height=200, showlegend=False)
    return fig


def fig_rsi(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "rsi_14"]].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["rsi_14"],
        name="RSI", line=dict(color="#6366f1"),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444",
                  annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#22c55e",
                  annotation_text="Oversold (30)")
    fig.update_layout(height=300, yaxis=dict(range=[0, 100]), title="RSI (14)")
    return fig


def fig_macd(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "macd", "macd_signal", "macd_hist"]].dropna()
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in valid["macd_hist"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valid["date"], y=valid["macd_hist"],
        marker_color=colors, name="Histogram",
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd"],
        name="MACD", line=dict(color="#6366f1"),
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd_signal"],
        name="Signal", line=dict(color="#f59e0b"),
    ))
    fig.update_layout(height=300, title="MACD (12/26/9)")
    return fig


if __name__ == "__main__":
    pass  # main() added in Task 4
