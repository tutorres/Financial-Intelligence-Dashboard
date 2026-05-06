import logging
from pathlib import Path
from pipeline.utils import get_connection, setup_schemas, get_logger, TICKERS, DATA_DIR


def test_get_connection_returns_connection():
    conn = get_connection(":memory:")
    assert conn is not None
    conn.close()


def test_get_connection_accepts_memory():
    conn = get_connection(":memory:")
    result = conn.execute("SELECT 42").fetchone()
    assert result[0] == 42
    conn.close()


def test_setup_schemas_creates_all_four():
    conn = get_connection(":memory:")
    setup_schemas(conn)
    schemas = [
        row[0]
        for row in conn.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
    ]
    assert "bronze" in schemas
    assert "silver" in schemas
    assert "gold" in schemas
    assert "features" in schemas
    conn.close()


def test_setup_schemas_is_idempotent():
    conn = get_connection(":memory:")
    setup_schemas(conn)
    setup_schemas(conn)  # must not raise
    conn.close()


def test_tickers_has_four_entries():
    assert len(TICKERS) == 4
    assert "AAPL" in TICKERS
    assert "MSFT" in TICKERS
    assert "NVDA" in TICKERS
    assert "BTC-USD" in TICKERS


def test_get_logger_returns_named_logger():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"
    assert logger.level == logging.INFO


def test_data_dir_is_path():
    assert isinstance(DATA_DIR, Path)
    assert DATA_DIR.name == "data"
