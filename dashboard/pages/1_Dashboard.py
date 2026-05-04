import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard.app import (
    _get_db_connection,
    fig_candlestick,
    fig_macd,
    fig_rsi,
    fig_volume,
    fmt_volume,
    load_prices,
    load_summary,
    rsi_signal,
)
from pipeline.run import run as _run_pipeline
from pipeline.utils import TICKERS, get_connection as _get_raw_conn


def _data_ready() -> bool:
    conn = _get_raw_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM gold.summary").fetchone()[0] > 0
    except Exception:
        return False
    finally:
        conn.close()


def main() -> None:
    st.set_page_config(
        page_title="Dashboard · Financial Intelligence",
        page_icon="📊",
        layout="wide",
    )
    from dashboard.style import inject_global_css, inject_dashboard_css
    st.markdown(inject_global_css(), unsafe_allow_html=True)
    st.markdown(inject_dashboard_css(), unsafe_allow_html=True)
    st.markdown("""
<div style="border-bottom:1px solid #252525;padding:18px 6rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:2rem">
  <div style="display:flex;align-items:center;gap:24px">
    <a href="/" target="_self" style="color:#00ff88;font-size:15px;font-weight:700;letter-spacing:3px;text-decoration:none;font-family:'Geist Mono',monospace">FID_</a>
    <span style="color:#252525;font-size:20px;line-height:1">|</span>
    <span style="color:#8d8d8d;font-size:11px;font-family:'Geist Mono',monospace;letter-spacing:2px;text-transform:uppercase">Dashboard</span>
  </div>
  <a href="/" target="_self" style="color:#8d8d8d;font-size:11px;font-family:'Geist Mono',monospace;text-decoration:none;letter-spacing:1px">← Home</a>
</div>
""", unsafe_allow_html=True)

    if not _data_ready():
        with st.spinner("Fetching market data for the first time — this takes ~30 seconds..."):
            _run_pipeline()
        st.rerun()

    conn = _get_db_connection()

    col1, col2 = st.columns([1, 3])
    with col1:
        ticker = st.selectbox("Ticker", TICKERS)
    with col2:
        time_options = {"30d": 30, "90d": 90, "180d": 180, "1Y": 365}
        selected = st.radio("Time Range", list(time_options.keys()), horizontal=True)
        days = time_options[selected]

    try:
        df = load_prices(conn, ticker, days)
        summary = load_summary(conn, ticker)
    except Exception as exc:
        if "does not exist" in str(exc).lower() or "catalog" in str(exc).lower():
            st.warning("Pipeline tables not found. Run `python pipeline/run.py` first.")
        else:
            st.error(f"Unexpected error loading data: {exc}")
        st.stop()

    if df.empty and summary is None:
        st.warning("No data found. Run `python pipeline/run.py` first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Overview", "Price & Volume", "Technical Indicators"])

    with tab1:
        if summary is None:
            st.info("No summary data available for this ticker.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Last Close", f"${summary['last_close']:.2f}")
            c2.metric(
                "1-day Change",
                f"{summary['pct_change_1d']:.2f}%"
                if pd.notna(summary["pct_change_1d"]) else "N/A",
            )
            c3.metric(
                "7-day Change",
                f"{summary['pct_change_7d']:.2f}%"
                if pd.notna(summary["pct_change_7d"]) else "N/A",
            )
            c4.metric(
                "30-day Change",
                f"{summary['pct_change_30d']:.2f}%"
                if pd.notna(summary["pct_change_30d"]) else "N/A",
            )
            c5, c6 = st.columns(2)
            c5.metric("Avg Volume (30d)", fmt_volume(summary["avg_volume_30d"]))
            rsi_val = summary["current_rsi"]
            c6.metric(
                "RSI",
                f"{rsi_val:.1f} — {rsi_signal(rsi_val)}"
                if pd.notna(rsi_val) else "N/A",
            )

    with tab2:
        if df.empty:
            st.info("No data available for this period.")
        else:
            st.markdown("#### Price History")
            st.caption(
                "Each candle represents one trading day. "
                "A **green candle** means the price closed higher than it opened; **red** means it closed lower. "
                "The thin lines (wicks) show the intraday high and low. "
                "The colored lines are moving averages: "
                "**MA7** (amber) tracks short-term momentum, "
                "**MA21** (green) shows the monthly trend, and "
                "**MA50** (indigo) reflects the long-term direction. "
                "When a shorter MA crosses above a longer one, it's a bullish signal — and vice versa."
            )
            st.plotly_chart(fig_candlestick(df), use_container_width=True)

            st.markdown("#### Volume")
            st.caption(
                "Number of shares (or units) traded each day. "
                "**High volume on an up day** confirms buying pressure behind the move. "
                "**High volume on a down day** signals strong selling. "
                "Low volume moves are less reliable — they can reverse easily. "
                "Color matches the candle above: green = up day, red = down day."
            )
            st.plotly_chart(fig_volume(df), use_container_width=True)

    with tab3:
        if df.empty:
            st.info("No data available for this period.")
        else:
            col_rsi, col_macd = st.columns(2)
            with col_rsi:
                st.markdown("#### RSI — Relative Strength Index (14 days)")
                st.caption(
                    "Measures how overbought or oversold an asset is, on a scale from 0 to 100. "
                    "**Above 70**: overbought — a pullback is possible. "
                    "**Below 30**: oversold — a bounce is possible. "
                    "Works best combined with price action and volume."
                )
                st.plotly_chart(fig_rsi(df), use_container_width=True)
            with col_macd:
                st.markdown("#### MACD — Moving Average Convergence/Divergence (12 / 26 / 9)")
                st.caption(
                    "The **MACD line** (indigo) is the gap between the 12-day and 26-day EMAs. "
                    "The **Signal line** (amber) smooths it over 9 days. "
                    "Green histogram bars = bullish momentum; red = bearish. "
                    "A MACD crossover above Signal is a classic buy signal."
                )
                st.plotly_chart(fig_macd(df), use_container_width=True)


main()
