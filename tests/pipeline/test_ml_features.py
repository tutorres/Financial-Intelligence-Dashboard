import numpy as np
import pandas as pd
import pytest

from pipeline.ml_features import ml_features
from pipeline.utils import get_connection, setup_schemas


def _make_gold_df(ticker: str = "AAPL", n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-01", periods=n).date
    close = 100 + np.cumsum(rng.standard_normal(n) * 2)
    daily_return = pd.Series(close).pct_change().values
    ma_7 = pd.Series(close).rolling(7).mean().values
    ma_21 = pd.Series(close).rolling(21).mean().values
    return pd.DataFrame({
        "ticker": ticker,
        "date": dates,
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
        "daily_return": daily_return,
        "ma_7": ma_7,
        "ma_21": ma_21,
        "ma_50": pd.Series(close).rolling(50).mean().values,
        "rsi_14": rng.uniform(20, 80, n),
        "macd": rng.standard_normal(n) * 0.5,
        "macd_signal": rng.standard_normal(n) * 0.5,
        "macd_hist": rng.standard_normal(n) * 0.1,
        "volatility_21": rng.uniform(0.005, 0.03, n),
    })


def _insert_gold_prices(conn, df: pd.DataFrame) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.prices (
            ticker        VARCHAR NOT NULL,
            date          DATE NOT NULL,
            open          DOUBLE,
            high          DOUBLE,
            low           DOUBLE,
            close         DOUBLE,
            volume        DOUBLE,
            daily_return  DOUBLE,
            ma_7          DOUBLE,
            ma_21         DOUBLE,
            ma_50         DOUBLE,
            rsi_14        DOUBLE,
            macd          DOUBLE,
            macd_signal   DOUBLE,
            macd_hist     DOUBLE,
            volatility_21 DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("INSERT INTO gold.prices SELECT * FROM df")


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


def test_ml_features_populates_model_input(conn):
    _insert_gold_prices(conn, _make_gold_df("AAPL", 60))
    ml_features(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM features.model_input").fetchone()[0]
    assert count > 0


def test_close_norm_bounded(conn):
    _insert_gold_prices(conn, _make_gold_df("AAPL", 60))
    ml_features(conn=conn)
    rows = conn.execute(
        "SELECT close_norm FROM features.model_input WHERE close_norm IS NOT NULL"
    ).df()
    assert (rows["close_norm"] >= 0).all()
    assert (rows["close_norm"] <= 1).all()


def test_volume_norm_bounded(conn):
    _insert_gold_prices(conn, _make_gold_df("AAPL", 60))
    ml_features(conn=conn)
    rows = conn.execute(
        "SELECT volume_norm FROM features.model_input WHERE volume_norm IS NOT NULL"
    ).df()
    assert (rows["volume_norm"] >= 0).all()
    assert (rows["volume_norm"] <= 1).all()


def test_ml_features_is_idempotent(conn):
    _insert_gold_prices(conn, _make_gold_df("AAPL", 60))
    ml_features(conn=conn)
    ml_features(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM features.model_input").fetchone()[0]
    assert count > 0


def test_ml_features_multiple_tickers(conn):
    gold = pd.concat([_make_gold_df("AAPL", 60), _make_gold_df("MSFT", 60)])
    _insert_gold_prices(conn, gold)
    ml_features(conn=conn)
    tickers = conn.execute(
        "SELECT DISTINCT ticker FROM features.model_input ORDER BY ticker"
    ).df()["ticker"].tolist()
    assert "AAPL" in tickers
    assert "MSFT" in tickers
