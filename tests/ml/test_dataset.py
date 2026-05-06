import pytest
import duckdb
import torch
from datetime import date, timedelta

from ml.dataset import StockSequenceDataset, FEATURE_COLS


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA features")
    c.execute("CREATE SCHEMA gold")
    c.execute("""
        CREATE TABLE features.model_input (
            ticker VARCHAR, date DATE,
            close_norm DOUBLE, volume_norm DOUBLE,
            ma_7_norm DOUBLE, ma_21_norm DOUBLE,
            rsi_14 DOUBLE, daily_return DOUBLE
        )
    """)
    c.execute("CREATE TABLE gold.prices (ticker VARCHAR, date DATE, close DOUBLE)")

    start = date(2024, 1, 1)
    for ticker in ["AAPL", "MSFT"]:
        for i in range(50):
            d = start + timedelta(days=i)
            c.execute(
                "INSERT INTO features.model_input VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [ticker, d, 0.5, 0.5, 0.5, 0.5, 50.0, 0.01],
            )
            c.execute(
                "INSERT INTO gold.prices VALUES (?, ?, ?)",
                [ticker, d, 100.0 + i],
            )
    yield c
    c.close()


def test_sequence_shape(conn):
    ds = StockSequenceDataset(conn, sequence_len=30, forward_days=5)
    x, y = ds[0]
    assert x.shape == (30, 6)
    assert x.dtype == torch.float32
    assert y.shape == ()
    assert y.dtype == torch.long


def test_sample_count(conn):
    # n=50, seq_len=30, forward_days=5
    # valid windows per ticker: n - seq_len - forward_days + 1 = 16
    # 2 tickers → 32 total
    ds = StockSequenceDataset(conn, sequence_len=30, forward_days=5)
    assert len(ds) == 32


def test_feature_cols(conn):
    ds = StockSequenceDataset(conn)
    assert ds.feature_cols == FEATURE_COLS
    assert len(ds.feature_cols) == 6
