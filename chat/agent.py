import json
import os
from collections.abc import Iterator
from datetime import date, timedelta

import duckdb
from dotenv import load_dotenv

load_dotenv()

_GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
try:
    from groq import Groq
    _client = Groq(api_key=_GROQ_API_KEY) if _GROQ_API_KEY else None
except Exception:
    _client = None


def is_available() -> bool:
    return _client is not None


def _get_summary(conn, ticker: str) -> dict:
    row = conn.execute(
        "SELECT ticker, last_close, pct_change_1d, pct_change_7d, pct_change_30d, "
        "avg_volume_30d, current_rsi FROM gold.summary WHERE ticker = ?",
        [ticker],
    ).df()
    if row.empty:
        return {"error": "no data"}
    return row.astype(object).iloc[0].to_dict()


def _get_recent_prices(conn, ticker: str, days: int = 30) -> list:
    cutoff = date.today() - timedelta(days=days)
    df = conn.execute(
        "SELECT date, open, high, low, close, volume, daily_return, "
        "ma_7, ma_21, ma_50, rsi_14, macd, macd_signal, macd_hist, volatility_21 "
        "FROM gold.prices WHERE ticker = ? AND date >= ? "
        "ORDER BY date DESC LIMIT 30",
        [ticker, cutoff],
    ).df()
    df["date"] = df["date"].astype(str)
    return df.to_dict(orient="records")


def _get_prediction(conn, ticker: str) -> dict:
    try:
        row = conn.execute(
            "SELECT signal, confidence, p_down, p_neutral, p_up, predicted_at "
            "FROM gold.predictions WHERE ticker = ? ORDER BY predicted_at DESC LIMIT 1",
            [ticker],
        ).df()
    except duckdb.CatalogException:
        return {"error": "no prediction available"}
    if row.empty:
        return {"error": "no prediction available"}
    d = row.astype(object).iloc[0].to_dict()
    d["predicted_at"] = str(d["predicted_at"])
    return d
