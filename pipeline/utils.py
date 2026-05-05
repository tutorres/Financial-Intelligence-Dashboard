import logging
from pathlib import Path

import duckdb

TICKERS: list[str] = ["AAPL", "MSFT", "NVDA", "BTC-USD"]
DATA_DIR: Path = Path(__file__).parent.parent / "data"


def get_connection(path: str | None = None) -> duckdb.DuckDBPyConnection:
    if path is None:
        DATA_DIR.mkdir(exist_ok=True)
        path = str(DATA_DIR / "financial.duckdb")
    return duckdb.connect(path)


def setup_schemas(conn: duckdb.DuckDBPyConnection) -> None:
    for schema in ("bronze", "silver", "gold", "features"):
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
