import pandas as pd
import pytest
from unittest.mock import patch

from pipeline.ingest import ingest
from pipeline.utils import get_connection, setup_schemas


def _make_yf_df() -> pd.DataFrame:
    """Minimal DataFrame matching yfinance single-ticker output."""
    return pd.DataFrame(
        {
            "Open": [180.0, 182.0],
            "High": [185.0, 186.0],
            "Low": [179.0, 181.0],
            "Close": [184.0, 185.0],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="Date"),
    )


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


@pytest.fixture
def mock_yf():
    with patch("pipeline.ingest.yf.download", return_value=_make_yf_df()) as m:
        yield m


@pytest.fixture
def mock_yf_empty():
    with patch("pipeline.ingest.yf.download", return_value=pd.DataFrame()) as m:
        yield m


@pytest.fixture
def mock_yf_error():
    with patch("pipeline.ingest.yf.download", side_effect=Exception("network error")) as m:
        yield m


def test_ingest_creates_bronze_rows(conn, mock_yf):
    ingest(conn=conn, tickers=["AAPL"])
    count = conn.execute("SELECT COUNT(*) FROM bronze.prices").fetchone()[0]
    assert count == 2


def test_ingest_stores_correct_ticker(conn, mock_yf):
    ingest(conn=conn, tickers=["AAPL"])
    tickers = conn.execute("SELECT DISTINCT ticker FROM bronze.prices").fetchall()
    assert tickers == [("AAPL",)]


def test_ingest_upsert_no_duplicates(conn, mock_yf):
    ingest(conn=conn, tickers=["AAPL"])
    ingest(conn=conn, tickers=["AAPL"])  # re-run
    count = conn.execute("SELECT COUNT(*) FROM bronze.prices").fetchone()[0]
    assert count == 2


def test_ingest_skips_empty_ticker(conn, mock_yf_empty):
    ingest(conn=conn, tickers=["BADTICKER"])  # must not raise
    count = conn.execute("SELECT COUNT(*) FROM bronze.prices").fetchone()[0]
    assert count == 0


def test_ingest_skips_erroring_ticker(conn, mock_yf_error):
    ingest(conn=conn, tickers=["BADTICKER"])  # must not raise
    count = conn.execute("SELECT COUNT(*) FROM bronze.prices").fetchone()[0]
    assert count == 0


def test_ingest_continues_after_failed_ticker(conn):
    def side_effect(ticker, **kwargs):
        if ticker == "BADTICKER":
            raise Exception("network error")
        return _make_yf_df()

    with patch("pipeline.ingest.yf.download", side_effect=side_effect):
        ingest(conn=conn, tickers=["BADTICKER", "AAPL"])

    count = conn.execute("SELECT COUNT(*) FROM bronze.prices").fetchone()[0]
    assert count == 2
