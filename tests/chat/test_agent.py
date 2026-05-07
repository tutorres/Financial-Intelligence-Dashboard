from datetime import date, timedelta

import duckdb
import pytest


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA gold")
    c.execute("""
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
    c.execute("""
        CREATE TABLE gold.prices (
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
    yield c
    c.close()


def test_get_summary_tool(conn):
    conn.execute("""
        INSERT INTO gold.summary VALUES
        ('AAPL', '2024-01-03', 185.0, 1.5, 3.2, 5.0, 1050000.0, 55.0)
    """)
    from chat.agent import _get_summary
    result = _get_summary(conn, "AAPL")
    assert result["ticker"] == "AAPL"
    assert abs(result["last_close"] - 185.0) < 1e-9
    assert "pct_change_1d" in result
    assert "current_rsi" in result


def test_get_summary_tool_unknown_ticker(conn):
    from chat.agent import _get_summary
    result = _get_summary(conn, "UNKNOWN")
    assert result == {"error": "no data"}


def test_get_recent_prices_tool_capped_at_30(conn):
    today = date.today()
    for i in range(60):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute("""
            INSERT INTO gold.prices VALUES
            ('AAPL', ?, 100.0, 102.0, 99.0, 101.0, 1000000,
             0.01, 100.5, 100.3, 100.1, 55.0, 0.5, 0.4, 0.1, 0.015)
        """, [d])
    from chat.agent import _get_recent_prices
    result = _get_recent_prices(conn, "AAPL", days=365)
    assert len(result) <= 30
    assert all("date" in row and "close" in row for row in result)


def test_get_prediction_tool_no_table(conn):
    from chat.agent import _get_prediction
    result = _get_prediction(conn, "AAPL")
    assert result == {"error": "no prediction available"}
