import numpy as np
import pandas as pd
import pytest

from pipeline.transform import transform
from pipeline.utils import get_connection, setup_schemas


def _make_bronze_df(ticker: str = "AAPL", n: int = 10) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-01", periods=n).date
    close = 100 + np.cumsum(rng.standard_normal(n) * 2)
    return pd.DataFrame({
        "ticker": ticker,
        "date": dates,
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": rng.integers(1_000_000, 10_000_000, n),
        "ingested_at": pd.Timestamp.utcnow(),
    })


def _insert_bronze(conn, df: pd.DataFrame) -> None:
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
    conn.execute("INSERT OR REPLACE INTO bronze.prices SELECT * FROM df")


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


def test_transform_populates_silver(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 10))
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 10


def test_transform_silver_has_only_ohlcv_columns(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 10))
    transform(conn=conn)
    cols = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='silver' AND table_name='prices'"
        ).fetchall()
    }
    assert cols == {"ticker", "date", "open", "high", "low", "close", "volume"}


def test_transform_drops_null_close(conn):
    df = _make_bronze_df("AAPL", 10)
    df.loc[0, "close"] = None
    _insert_bronze(conn, df)
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 9


def test_transform_deduplicates(conn):
    # Create bronze without PK to allow duplicate (ticker, date) pairs
    conn.execute("""
        CREATE TABLE bronze.prices (
            ticker      VARCHAR,
            date        DATE,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            ingested_at TIMESTAMP
        )
    """)
    df = pd.DataFrame([
        {
            "ticker": "AAPL",
            "date": pd.Timestamp("2023-01-03").date(),
            "open": 99.0, "high": 101.0, "low": 98.0,
            "close": 100.0, "volume": 1_000_000,
            "ingested_at": pd.Timestamp("2023-01-03 10:00:00"),
        },
        {
            "ticker": "AAPL",
            "date": pd.Timestamp("2023-01-03").date(),
            "open": 99.5, "high": 101.5, "low": 98.5,
            "close": 100.5, "volume": 1_100_000,
            "ingested_at": pd.Timestamp("2023-01-03 11:00:00"),
        },
    ])
    conn.execute("INSERT INTO bronze.prices SELECT * FROM df")
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 1
    close = conn.execute("SELECT close FROM silver.prices WHERE ticker='AAPL'").fetchone()[0]
    assert abs(close - 100.5) < 1e-9


def test_transform_is_idempotent(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 10))
    transform(conn=conn)
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 10


def test_transform_multiple_tickers(conn):
    _insert_bronze(conn, pd.concat([_make_bronze_df("AAPL", 10), _make_bronze_df("MSFT", 10)]))
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 20
