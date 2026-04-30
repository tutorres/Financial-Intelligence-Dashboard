from datetime import date, timedelta

import duckdb
import pandas as pd
import pytest

from dashboard.app import fmt_volume, load_prices, load_summary, rsi_signal
from dashboard.app import _stat_card_html, build_landing_html


def _make_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA gold")
    conn.execute("""
        CREATE TABLE gold.summary (
            ticker         VARCHAR PRIMARY KEY,
            last_updated   DATE,
            last_close     DOUBLE,
            pct_change_1d  DOUBLE,
            pct_change_7d  DOUBLE,
            pct_change_30d DOUBLE,
            avg_volume_30d DOUBLE,
            current_rsi    DOUBLE
        )
    """)
    conn.execute("CREATE SCHEMA silver")
    conn.execute("""
        CREATE TABLE silver.prices (
            ticker        VARCHAR NOT NULL,
            date          DATE NOT NULL,
            open          DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            volume        BIGINT,
            daily_return  DOUBLE, ma_7 DOUBLE, ma_21 DOUBLE, ma_50 DOUBLE,
            rsi_14        DOUBLE, macd DOUBLE, macd_signal DOUBLE,
            macd_hist     DOUBLE, volatility_21 DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)
    return conn


@pytest.fixture
def conn():
    c = _make_conn()
    yield c
    c.close()


@pytest.fixture
def conn_with_data():
    c = _make_conn()
    c.execute("""
        INSERT INTO gold.summary VALUES
        ('AAPL', '2024-01-03', 185.0, 1.5, 3.2, 5.0, 1050000.0, 55.0)
    """)
    today = date.today()
    for i in range(60):
        d = (today - timedelta(days=i)).isoformat()
        c.execute("""
            INSERT INTO silver.prices VALUES
            ('AAPL', ?, 100.0, 102.0, 99.0, 101.0, 1000000,
             0.01, 100.5, 100.3, 100.1, 55.0, 0.5, 0.4, 0.1, 0.015)
        """, [d])
    yield c
    c.close()


# --- load_summary ---

def test_load_summary_returns_dict(conn_with_data):
    result = load_summary(conn_with_data, "AAPL")
    assert result is not None
    assert isinstance(result, dict)


def test_load_summary_correct_values(conn_with_data):
    result = load_summary(conn_with_data, "AAPL")
    assert abs(result["last_close"] - 185.0) < 1e-9
    assert abs(result["current_rsi"] - 55.0) < 1e-9


def test_load_summary_returns_none_for_unknown_ticker(conn_with_data):
    assert load_summary(conn_with_data, "BADTICKER") is None


def test_load_summary_returns_none_when_empty(conn):
    assert load_summary(conn, "AAPL") is None


# --- load_prices ---

def test_load_prices_returns_dataframe(conn_with_data):
    result = load_prices(conn_with_data, "AAPL", 30)
    assert isinstance(result, pd.DataFrame)


def test_load_prices_filters_by_ticker(conn_with_data):
    assert load_prices(conn_with_data, "MSFT", 365).empty


def test_load_prices_filters_by_days(conn_with_data):
    result_30 = load_prices(conn_with_data, "AAPL", 30)
    result_60 = load_prices(conn_with_data, "AAPL", 60)
    assert len(result_30) < len(result_60)


def test_load_prices_ordered_by_date(conn_with_data):
    result = load_prices(conn_with_data, "AAPL", 60)
    dates = result["date"].tolist()
    assert dates == sorted(dates)


# --- rsi_signal ---

def test_rsi_signal_overbought():
    assert rsi_signal(75.0) == "Overbought"


def test_rsi_signal_oversold():
    assert rsi_signal(25.0) == "Oversold"


def test_rsi_signal_neutral():
    assert rsi_signal(55.0) == "Neutral"


def test_rsi_signal_none():
    assert rsi_signal(None) == "N/A"


def test_rsi_signal_nan():
    assert rsi_signal(float("nan")) == "N/A"


# --- fmt_volume ---

def test_fmt_volume_millions():
    assert fmt_volume(2_500_000.0) == "2.5M"


def test_fmt_volume_thousands():
    assert fmt_volume(750_000.0) == "750.0K"


def test_fmt_volume_none():
    assert fmt_volume(None) == "N/A"


# --- _stat_card_html ---

def test_stat_card_html_up_shows_green_and_up_arrow():
    html = _stat_card_html("AAPL", 189.43, 1.24)
    assert "#00ff88" in html
    assert "▲" in html
    assert "189.43" in html
    assert "AAPL" in html


def test_stat_card_html_down_shows_red_and_down_arrow():
    html = _stat_card_html("MSFT", 415.20, -0.42)
    assert "#ff4d4d" in html
    assert "▼" in html
    assert "415.20" in html


def test_stat_card_html_none_price_shows_dash():
    html = _stat_card_html("AAPL", None, None)
    assert "—" in html


# --- build_landing_html ---

def test_build_landing_html_structure():
    html = build_landing_html([])
    assert "Financial" in html
    assert "Intelligence" in html
    assert "Dashboard" in html
    assert "// data pipeline" in html
    assert "// tech stack" in html
    assert "// covered assets" in html


def test_build_landing_html_shows_live_stats_when_provided():
    stats = [{"ticker": "AAPL", "last_close": 189.43, "pct_change_1d": 1.24}]
    html = build_landing_html(stats)
    assert "189.43" in html
    assert "AAPL" in html


def test_build_landing_html_falls_back_to_placeholder_tickers():
    html = build_landing_html([])
    for ticker in ["AAPL", "MSFT", "NVDA", "BTC-USD"]:
        assert ticker in html
