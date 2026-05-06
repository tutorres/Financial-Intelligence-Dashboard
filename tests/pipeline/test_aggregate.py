import numpy as np
import pandas as pd
import pytest

from pipeline.aggregate import aggregate
from pipeline.utils import get_connection, setup_schemas


def _make_silver_df(ticker: str = "AAPL", n: int = 60) -> pd.DataFrame:
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
    })


def _insert_silver(conn, df: pd.DataFrame) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver.prices (
            ticker  VARCHAR NOT NULL,
            date    DATE NOT NULL,
            open    DOUBLE,
            high    DOUBLE,
            low     DOUBLE,
            close   DOUBLE,
            volume  BIGINT,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("INSERT INTO silver.prices SELECT * FROM df")


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


def test_aggregate_creates_gold_prices(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM gold.prices").fetchone()[0]
    assert count == 60


def test_gold_prices_rsi_bounded(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    rows = conn.execute(
        "SELECT rsi_14 FROM gold.prices WHERE ticker='AAPL' AND rsi_14 IS NOT NULL"
    ).df()
    assert len(rows) > 0
    assert (rows["rsi_14"] >= 0).all()
    assert (rows["rsi_14"] <= 100).all()


def test_gold_prices_ma7(conn):
    df = _make_silver_df("AAPL", 60)
    _insert_silver(conn, df)
    aggregate(conn=conn)
    rows = conn.execute(
        "SELECT ma_7 FROM gold.prices WHERE ticker='AAPL' ORDER BY date"
    ).df()
    expected = df["close"].iloc[:7].mean()
    assert abs(rows["ma_7"].iloc[6] - expected) < 1e-9


def test_aggregate_creates_summary_one_row_per_ticker(conn):
    _insert_silver(conn, pd.concat([_make_silver_df("AAPL", 60), _make_silver_df("MSFT", 60)]))
    aggregate(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM gold.summary").fetchone()[0]
    assert count == 2


def test_summary_last_close_matches_silver(conn):
    df = _make_silver_df("AAPL", 60)
    _insert_silver(conn, df)
    aggregate(conn=conn)
    last_close = conn.execute(
        "SELECT last_close FROM gold.summary WHERE ticker='AAPL'"
    ).fetchone()[0]
    assert abs(last_close - df.iloc[-1]["close"]) < 1e-9


def test_aggregate_is_idempotent(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    aggregate(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM gold.summary").fetchone()[0]
    assert count == 1
