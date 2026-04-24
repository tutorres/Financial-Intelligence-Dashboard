# Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Bronze → Silver → Gold financial data pipeline using yfinance + DuckDB, fully tested with pytest and TDD.

**Architecture:** Three independent pipeline scripts (`ingest.py`, `transform.py`, `aggregate.py`) share a `utils.py` foundation. All logic is deterministic and tested against an in-memory DuckDB instance. A `run.py` script chains all three for CLI use.

**Tech Stack:** Python 3.11+, duckdb, yfinance, pandas, numpy, pytest

---

## File Map

| File | Role |
|------|------|
| `requirements.txt` | Python dependencies |
| `.gitignore` | Excludes data files, cache, venv |
| `data/.gitkeep` | Keeps the data dir in git without committing the DB |
| `pipeline/__init__.py` | Makes pipeline a package |
| `pipeline/utils.py` | `get_connection`, `setup_schemas`, `get_logger`, `TICKERS`, `DATA_DIR` |
| `pipeline/ingest.py` | yfinance → `bronze.prices` (upsert by ticker+date) |
| `pipeline/transform.py` | `bronze.prices` → `silver.prices` (indicators) |
| `pipeline/aggregate.py` | `silver.prices` → `gold.features` + `gold.summary` |
| `pipeline/run.py` | Chains ingest → transform → aggregate |
| `tests/__init__.py` | Makes tests a package |
| `tests/pipeline/__init__.py` | Makes tests/pipeline a package |
| `tests/pipeline/test_utils.py` | Tests for utils.py |
| `tests/pipeline/test_ingest.py` | Tests for ingest.py (mocks yfinance) |
| `tests/pipeline/test_transform.py` | Tests for transform.py (deterministic indicator math) |
| `tests/pipeline/test_aggregate.py` | Tests for aggregate.py (normalization + summary) |

---

## Task 1: Bootstrap project structure

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `pipeline/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/pipeline/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
duckdb>=0.10.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
pytest>=8.0.0
```

- [ ] **Step 2: Create .gitignore**

```
data/*.duckdb
data/*.db
__pycache__/
*.py[cod]
.pytest_cache/
*.egg-info/
.venv/
venv/
.env
.vscode/
.idea/
```

- [ ] **Step 3: Create data/.gitkeep, pipeline/__init__.py, tests/__init__.py, tests/pipeline/__init__.py**

All four files are empty. Just `touch` them (or create with no content).

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: packages install without errors.

- [ ] **Step 5: Verify pytest finds no tests yet (not an error)**

```bash
pytest tests/ -v
```

Expected output contains: `no tests ran` or `0 passed`.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore data/.gitkeep pipeline/__init__.py tests/__init__.py tests/pipeline/__init__.py
git commit -m "chore: bootstrap project structure and dependencies"
```

---

## Task 2: utils.py — shared foundation

**Files:**
- Create: `pipeline/utils.py`
- Create: `tests/pipeline/test_utils.py`

- [ ] **Step 1: Write failing tests**

`tests/pipeline/test_utils.py`:
```python
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


def test_setup_schemas_creates_all_three():
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
pytest tests/pipeline/test_utils.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.utils'`

- [ ] **Step 3: Implement utils.py**

`pipeline/utils.py`:
```python
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
    for schema in ("bronze", "silver", "gold"):
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
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/pipeline/test_utils.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/utils.py tests/pipeline/test_utils.py
git commit -m "feat: add utils module with db connection, schemas, and logger"
```

---

## Task 3: ingest.py — yfinance → bronze layer

**Files:**
- Create: `pipeline/ingest.py`
- Create: `tests/pipeline/test_ingest.py`

- [ ] **Step 1: Write failing tests**

`tests/pipeline/test_ingest.py`:
```python
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
pytest tests/pipeline/test_ingest.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.ingest'`

- [ ] **Step 3: Implement ingest.py**

`pipeline/ingest.py`:
```python
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from pipeline.utils import TICKERS, get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _create_table(conn) -> None:
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


def _fetch_ticker(ticker: str, period_days: int = 365) -> pd.DataFrame | None:
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=period_days)
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            logger.warning("No data returned for %s", ticker)
            return None
        df = df.reset_index()
        # Flatten MultiIndex columns (yfinance >= 0.2.38 may return them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
        df["ticker"] = ticker
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ingested_at"] = datetime.now(timezone.utc)
        return df[["ticker", "date", "open", "high", "low", "close", "volume", "ingested_at"]]
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", ticker, exc)
        return None


def ingest(
    conn=None,
    tickers: list[str] | None = None,
    period_days: int = 365,
) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_table(conn)
    for ticker in tickers or TICKERS:
        df = _fetch_ticker(ticker, period_days)
        if df is None:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO bronze.prices
            SELECT ticker, date, open, high, low, close, volume, ingested_at
            FROM df
        """)
        logger.info("Ingested %d rows for %s", len(df), ticker)
    if own_conn:
        conn.close()


if __name__ == "__main__":
    ingest()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/pipeline/test_ingest.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/ingest.py tests/pipeline/test_ingest.py
git commit -m "feat: add bronze layer ingestion from yfinance"
```

---

## Task 4: transform.py — bronze → silver layer

**Files:**
- Create: `pipeline/transform.py`
- Create: `tests/pipeline/test_transform.py`

- [ ] **Step 1: Write failing tests**

`tests/pipeline/test_transform.py`:
```python
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
pytest tests/pipeline/test_transform.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.transform'`

- [ ] **Step 3: Implement transform.py**

`pipeline/transform.py`:
```python
import pandas as pd

from pipeline.utils import get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    close = df["close"]
    df["daily_return"] = close.pct_change()
    df["ma_7"] = close.rolling(7).mean()
    df["ma_21"] = close.rolling(21).mean()
    df["ma_50"] = close.rolling(50).mean()
    df["rsi_14"] = _rsi(close)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["volatility_21"] = df["daily_return"].rolling(21).std()
    return df[[
        "ticker", "date", "open", "high", "low", "close", "volume",
        "daily_return", "ma_7", "ma_21", "ma_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "volatility_21",
    ]]


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver.prices (
            ticker        VARCHAR NOT NULL,
            date          DATE NOT NULL,
            open          DOUBLE,
            high          DOUBLE,
            low           DOUBLE,
            close         DOUBLE,
            volume        BIGINT,
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


def transform(conn=None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_table(conn)
    bronze = conn.execute(
        "SELECT * FROM bronze.prices ORDER BY ticker, date"
    ).df()
    if bronze.empty:
        logger.warning("bronze.prices is empty — nothing to transform")
        if own_conn:
            conn.close()
        return
    results = []
    for ticker in bronze["ticker"].unique():
        results.append(_compute_indicators(bronze[bronze["ticker"] == ticker]))
    result = pd.concat(results, ignore_index=True)
    conn.execute("DELETE FROM silver.prices")
    conn.execute("""
        INSERT INTO silver.prices
        SELECT ticker, date, open, high, low, close, volume,
               daily_return, ma_7, ma_21, ma_50, rsi_14,
               macd, macd_signal, macd_hist, volatility_21
        FROM result
    """)
    logger.info("Transformed %d rows into silver.prices", len(result))
    if own_conn:
        conn.close()


if __name__ == "__main__":
    transform()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/pipeline/test_transform.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/transform.py tests/pipeline/test_transform.py
git commit -m "feat: add silver layer transformation with technical indicators"
```

---

## Task 5: aggregate.py — silver → gold layer

**Files:**
- Create: `pipeline/aggregate.py`
- Create: `tests/pipeline/test_aggregate.py`

- [ ] **Step 1: Write failing tests**

`tests/pipeline/test_aggregate.py`:
```python
import numpy as np
import pandas as pd
import pytest

from pipeline.aggregate import aggregate
from pipeline.utils import get_connection, setup_schemas


def _make_silver_df(ticker: str = "AAPL", n: int = 60) -> pd.DataFrame:
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


def _insert_silver(conn, df: pd.DataFrame) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver.prices (
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
    conn.execute("INSERT INTO silver.prices SELECT * FROM df")


@pytest.fixture
def conn():
    c = get_connection(":memory:")
    setup_schemas(c)
    yield c
    c.close()


def test_aggregate_creates_features(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    count = conn.execute("SELECT COUNT(*) FROM gold.features").fetchone()[0]
    assert count > 0


def test_features_close_norm_bounded(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    rows = conn.execute(
        "SELECT close_norm FROM gold.features WHERE close_norm IS NOT NULL"
    ).df()
    assert (rows["close_norm"] >= 0).all()
    assert (rows["close_norm"] <= 1).all()


def test_features_volume_norm_bounded(conn):
    _insert_silver(conn, _make_silver_df("AAPL", 60))
    aggregate(conn=conn)
    rows = conn.execute(
        "SELECT volume_norm FROM gold.features WHERE volume_norm IS NOT NULL"
    ).df()
    assert (rows["volume_norm"] >= 0).all()
    assert (rows["volume_norm"] <= 1).all()


def test_aggregate_creates_summary_one_row_per_ticker(conn):
    silver = pd.concat([_make_silver_df("AAPL", 60), _make_silver_df("MSFT", 60)])
    _insert_silver(conn, silver)
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
pytest tests/pipeline/test_aggregate.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.aggregate'`

- [ ] **Step 3: Implement aggregate.py**

`pipeline/aggregate.py`:
```python
import pandas as pd

from pipeline.utils import get_connection, get_logger, setup_schemas

logger = get_logger(__name__)


def _normalize(series: pd.Series) -> pd.Series:
    series = series.astype(float)
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.0, index=series.index)
    return (series - mn) / (mx - mn)


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["ticker", "date", "rsi_14", "daily_return"]].copy()
    for col, norm_col in [
        ("close", "close_norm"),
        ("volume", "volume_norm"),
        ("ma_7", "ma_7_norm"),
        ("ma_21", "ma_21_norm"),
    ]:
        out[norm_col] = df.groupby("ticker")[col].transform(_normalize)
    return out[[
        "ticker", "date", "close_norm", "volume_norm",
        "ma_7_norm", "ma_21_norm", "rsi_14", "daily_return",
    ]].dropna()


def _pct_change(group: pd.DataFrame, n: int) -> float | None:
    if len(group) <= n:
        return None
    current = group.iloc[-1]["close"]
    prev = group.iloc[-(n + 1)]["close"]
    return (current - prev) / prev * 100


def _build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date").reset_index(drop=True)
        last = group.iloc[-1]
        rows.append({
            "ticker": ticker,
            "last_updated": last["date"],
            "last_close": float(last["close"]),
            "pct_change_1d": _pct_change(group, 1),
            "pct_change_7d": _pct_change(group, 7),
            "pct_change_30d": _pct_change(group, 30),
            "avg_volume_30d": float(group.tail(30)["volume"].mean()),
            "current_rsi": float(last["rsi_14"]) if pd.notna(last["rsi_14"]) else None,
        })
    return pd.DataFrame(rows)


def _create_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.features (
            ticker       VARCHAR NOT NULL,
            date         DATE NOT NULL,
            close_norm   DOUBLE,
            volume_norm  DOUBLE,
            ma_7_norm    DOUBLE,
            ma_21_norm   DOUBLE,
            rsi_14       DOUBLE,
            daily_return DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.summary (
            ticker          VARCHAR PRIMARY KEY,
            last_updated    DATE,
            last_close      DOUBLE,
            pct_change_1d   DOUBLE,
            pct_change_7d   DOUBLE,
            pct_change_30d  DOUBLE,
            avg_volume_30d  DOUBLE,
            current_rsi     DOUBLE
        )
    """)


def aggregate(conn=None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    setup_schemas(conn)
    _create_tables(conn)
    silver = conn.execute("SELECT * FROM silver.prices ORDER BY ticker, date").df()
    if silver.empty:
        logger.warning("silver.prices is empty — nothing to aggregate")
        if own_conn:
            conn.close()
        return
    features_df = _build_features(silver)
    summary_df = _build_summary(silver)
    conn.execute("DELETE FROM gold.features")
    conn.execute("""
        INSERT INTO gold.features
        SELECT ticker, date, close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return
        FROM features_df
    """)
    conn.execute("DELETE FROM gold.summary")
    conn.execute("""
        INSERT INTO gold.summary
        SELECT ticker, last_updated, last_close, pct_change_1d, pct_change_7d,
               pct_change_30d, avg_volume_30d, current_rsi
        FROM summary_df
    """)
    logger.info(
        "Aggregated %d feature rows and %d summary rows into gold",
        len(features_df),
        len(summary_df),
    )
    if own_conn:
        conn.close()


if __name__ == "__main__":
    aggregate()
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/pipeline/test_aggregate.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/aggregate.py tests/pipeline/test_aggregate.py
git commit -m "feat: add gold layer aggregation and feature normalization"
```

---

## Task 6: run.py — pipeline runner + full test suite

**Files:**
- Create: `pipeline/run.py`

- [ ] **Step 1: Implement run.py**

`pipeline/run.py`:
```python
from pipeline.aggregate import aggregate
from pipeline.ingest import ingest
from pipeline.transform import transform
from pipeline.utils import get_connection, get_logger

logger = get_logger(__name__)


def run() -> None:
    conn = get_connection()
    try:
        logger.info("Pipeline started")
        ingest(conn=conn)
        transform(conn=conn)
        aggregate(conn=conn)
        logger.info("Pipeline complete")
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: `25 passed` (7 utils + 6 ingest + 6 transform + 6 aggregate)

- [ ] **Step 3: Push to GitHub**

```bash
git add pipeline/run.py
git commit -m "feat: add pipeline runner chaining ingest, transform, aggregate"
git push -u origin master
```

Expected: branch pushed to `git@github.com:tutorres/Financial-Intelligence-Dashboard.git`

- [ ] **Step 4: Verify smoke test (optional — hits real network)**

```bash
python pipeline/run.py
```

Expected log output:
```
... [INFO] pipeline.run: Pipeline started
... [INFO] pipeline.ingest: Ingested N rows for AAPL
... [INFO] pipeline.ingest: Ingested N rows for MSFT
... [INFO] pipeline.ingest: Ingested N rows for NVDA
... [INFO] pipeline.ingest: Ingested N rows for BTC-USD
... [INFO] pipeline.transform: Transformed N rows into silver.prices
... [INFO] pipeline.aggregate: Aggregated N feature rows and 4 summary rows into gold
... [INFO] pipeline.run: Pipeline complete
```
