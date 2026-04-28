import numpy as np
import pandas as pd
import pytest

from pipeline.transform import transform
from pipeline.utils import get_connection, setup_schemas


def _make_bronze_df(ticker: str = "AAPL", n: int = 60) -> pd.DataFrame:
    """60 rows of synthetic OHLCV — enough for all indicators (ma_50 needs 50)."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-01", periods=n).date
    close = 100 + np.cumsum(rng.standard_normal(n) * 2)
    return pd.DataFrame(
        {
            "ticker": ticker,
            "date": dates,
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.98,
            "close": close,
            "volume": rng.integers(1_000_000, 10_000_000, n),
            "ingested_at": pd.Timestamp.utcnow(),
        }
    )


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
    conn.execute("INSERT INTO bronze.prices SELECT * FROM df")


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


def test_transform_populates_silver(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 60))
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 60


def test_transform_daily_return(conn):
    df = _make_bronze_df("AAPL", 60)
    _insert_bronze(conn, df)
    transform(conn=conn)
    rows = conn.execute(
        "SELECT close, daily_return FROM silver.prices WHERE ticker='AAPL' ORDER BY date"
    ).df()
    # First row has NaN daily_return; second row is verifiable
    expected = (df.iloc[1]["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"]
    assert abs(rows.iloc[1]["daily_return"] - expected) < 1e-9


def test_transform_ma7(conn):
    df = _make_bronze_df("AAPL", 60)
    _insert_bronze(conn, df)
    transform(conn=conn)
    rows = conn.execute(
        "SELECT ma_7 FROM silver.prices WHERE ticker='AAPL' ORDER BY date"
    ).df()
    expected = df["close"].iloc[:7].mean()
    assert abs(rows["ma_7"].iloc[6] - expected) < 1e-9


def test_transform_rsi_bounded(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 60))
    transform(conn=conn)
    rows = conn.execute(
        "SELECT rsi_14 FROM silver.prices WHERE ticker='AAPL' AND rsi_14 IS NOT NULL"
    ).df()
    assert (rows["rsi_14"] >= 0).all()
    assert (rows["rsi_14"] <= 100).all()


def test_transform_is_idempotent(conn):
    _insert_bronze(conn, _make_bronze_df("AAPL", 60))
    transform(conn=conn)
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 60


def test_transform_multiple_tickers(conn):
    _insert_bronze(conn, pd.concat([_make_bronze_df("AAPL", 60), _make_bronze_df("MSFT", 60)]))
    transform(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
    assert count == 120
