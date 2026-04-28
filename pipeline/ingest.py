from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from pipeline.utils import TICKERS, get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.prices (
            ticker      VARCHAR NOT NULL,
            date        DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            ingested_at TIMESTAMP NOT NULL,
            PRIMARY KEY (ticker, date)
        )
    """)


def _fetch_ticker(ticker: str, period_days: int = 365) -> pd.DataFrame | None:
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=period_days)
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            logger.warning("No data returned for %s", ticker)
            return None
        df = df.reset_index()
        # Flatten MultiIndex columns (yfinance >= 0.2.38 may return them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
        df["ticker"] = ticker
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ingested_at"] = datetime.now(timezone.utc)
        return df[["ticker", "date", "open", "high", "low", "close", "volume", "ingested_at"]]
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", ticker, exc)
        return None


def ingest(
    conn=None,
    tickers: list[str] | None = None,
    period_days: int = 365,
) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_table(conn)
    for ticker in tickers or TICKERS:
        df = _fetch_ticker(ticker, period_days)
        if df is None:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO bronze.prices
            SELECT ticker, date, open, high, low, close, volume, ingested_at
            FROM df
        """)
        logger.info("Ingested %d rows for %s", len(df), ticker)
    if own_conn:
        conn.close()


if __name__ == "__main__":
    ingest()
