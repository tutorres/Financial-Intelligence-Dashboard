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
    st.title("Financial Intelligence Dashboard")

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
            st.plotly_chart(fig_candlestick(df), use_container_width=True)
            st.plotly_chart(fig_volume(df), use_container_width=True)

    with tab3:
        if df.empty:
            st.info("No data available for this period.")
        else:
            st.plotly_chart(fig_rsi(df), use_container_width=True)
            st.plotly_chart(fig_macd(df), use_container_width=True)


main()
