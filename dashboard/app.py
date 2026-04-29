import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.utils import TICKERS, get_connection as _get_conn


@st.cache_resource
def _get_db_connection():
    return _get_conn()


def load_summary(conn, ticker: str) -> dict | None:
    row = conn.execute("""
        SELECT ticker, last_updated, last_close,
               pct_change_1d, pct_change_7d, pct_change_30d,
               avg_volume_30d, current_rsi
        FROM gold.summary WHERE ticker = ?
    """, [ticker]).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def load_prices(conn, ticker: str, days: int) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    return conn.execute("""
        SELECT ticker, date, open, high, low, close, volume,
               daily_return, ma_7, ma_21, ma_50, rsi_14,
               macd, macd_signal, macd_hist, volatility_21
        FROM silver.prices
        WHERE ticker = ? AND date >= ?
        ORDER BY date
    """, [ticker, cutoff]).df()


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
        if valid.empty:
            continue
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


def main() -> None:
    st.set_page_config(
        page_title="Financial Intelligence Dashboard",
        page_icon="📈",
        layout="centered",
    )

    st.title("📈 Financial Intelligence Dashboard")
    st.markdown(
        "*Real-time stock & crypto analytics — technical indicators, LSTM trend prediction, "
        "and natural language queries.*"
    )

    st.divider()

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        st.page_link("pages/1_Dashboard.py", label="Open Dashboard →", icon="🚀")

    st.divider()

    col_desc, col_stack = st.columns([3, 2])

    with col_desc:
        st.markdown("### What it does")
        st.markdown(
            "- Ingests daily OHLCV data via **yfinance** for 8 assets\n"
            "- Processes through **Bronze → Silver → Gold** DuckDB layers\n"
            "- Computes **RSI, MACD, moving averages (7/21/50d), volatility**\n"
            "- LSTM trend classification (up / down / neutral) via PyTorch\n"
            "- Natural language queries via **Groq LLM** (llama3 / mixtral)"
        )

    with col_stack:
        st.markdown("### Tech Stack")
        st.markdown(
            "| Layer | Tech |\n"
            "|---|---|\n"
            "| Data | yfinance |\n"
            "| Storage | DuckDB |\n"
            "| Charts | Plotly |\n"
            "| UI | Streamlit |\n"
            "| ML | PyTorch LSTM |\n"
            "| LLM | Groq API |"
        )

    st.divider()

    st.markdown("### Covered Assets")
    stocks = [t for t in TICKERS if not t.endswith("-USD")]
    crypto = [t for t in TICKERS if t.endswith("-USD")]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Stocks**")
        for t in stocks:
            st.markdown(f"- `{t}`")
    with c2:
        st.markdown("**Crypto**")
        for t in crypto:
            st.markdown(f"- `{t}`")

    st.divider()

    st.markdown("### Pipeline Architecture")
    st.code(
        "yfinance  →  Bronze (raw OHLCV)\n"
        "          →  Silver (RSI / MACD / MAs / volatility)\n"
        "          →  Gold   (aggregated + ML-ready features)\n"
        "                         ↓\n"
        "            Streamlit Dashboard  +  LSTM  +  Groq Chat",
        language=None,
    )

    st.caption("Built by Arthur Torres · Computer Engineering Portfolio Project")


if __name__ == "__main__":
    main()
