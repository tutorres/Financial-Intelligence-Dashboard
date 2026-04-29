from datetime import date, timedelta

import pandas as pd
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


if __name__ == "__main__":
    pass  # main() added in Task 4
