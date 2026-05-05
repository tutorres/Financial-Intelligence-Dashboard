# Medallion Architecture Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce single-responsibility per pipeline layer — silver cleans only, gold computes indicators and aggregations, a new features layer normalizes for ML input.

**Architecture:** Bronze → Silver (clean OHLCV) → Gold (OHLCV + indicators + summary) → Features (normalized model input). Each layer is one Python file, one DuckDB schema, one responsibility.

**Tech Stack:** Python 3.11, DuckDB, pandas, pytest

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `pipeline/utils.py` | Add `features` schema |
| Modify | `pipeline/transform.py` | OHLCV-only silver (null drop + dedup) |
| Modify | `pipeline/aggregate.py` | Absorb indicators, write `gold.prices` + `gold.summary` |
| Create | `pipeline/ml_features.py` | Normalize `gold.prices` → `features.model_input` |
| Modify | `tests/pipeline/test_utils.py` | Assert `features` schema exists |
| Modify | `tests/pipeline/test_transform.py` | Rewrite for OHLCV-only silver |
| Modify | `tests/pipeline/test_aggregate.py` | OHLCV-only silver fixture, test `gold.prices` |
| Create | `tests/pipeline/test_ml_features.py` | Test new features layer |

---

## Task 1: Register `features` schema in utils

**Files:**
- Modify: `pipeline/utils.py:18`
- Modify: `tests/pipeline/test_utils.py:19-30`

- [ ] **Step 1: Update the failing test — add assertion for `features` schema**

  In `tests/pipeline/test_utils.py`, replace `test_setup_schemas_creates_all_three`:

  ```python
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
      assert "features" in schemas
      conn.close()
  ```

- [ ] **Step 2: Run the test to confirm it fails**

  ```
  pytest tests/pipeline/test_utils.py::test_setup_schemas_creates_all_three -v
  ```
  Expected: FAIL — `assert "features" in schemas`

- [ ] **Step 3: Add `features` to `setup_schemas` in `pipeline/utils.py`**

  Replace the `setup_schemas` function body (line 18-19):

  ```python
  def setup_schemas(conn: duckdb.DuckDBPyConnection) -> None:
      for schema in ("bronze", "silver", "gold", "features"):
          conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
  ```

- [ ] **Step 4: Run the test to confirm it passes**

  ```
  pytest tests/pipeline/test_utils.py -v
  ```
  Expected: all PASS

- [ ] **Step 5: Commit**

  ```bash
  git add pipeline/utils.py tests/pipeline/test_utils.py
  git commit -m "feat: register features schema in setup_schemas"
  ```

---

## Task 2: Rewrite silver layer — null drop and dedup only

**Files:**
- Modify: `tests/pipeline/test_transform.py` (full rewrite)
- Modify: `pipeline/transform.py` (full rewrite)

- [ ] **Step 1: Rewrite `tests/pipeline/test_transform.py`**

  Replace the entire file:

  ```python
  import numpy as np
  import pandas as pd
  import pytest

  from pipeline.transform import transform
  from pipeline.utils import get_connection, setup_schemas


  def _make_bronze_df(ticker: str = "AAPL", n: int = 10) -> pd.DataFrame:
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
          "ingested_at": pd.Timestamp.utcnow(),
      })


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
      conn.execute("INSERT OR REPLACE INTO bronze.prices SELECT * FROM df")


  @pytest.fixture
  def conn():
      c = get_connection(":memory:")
      setup_schemas(c)
      yield c
      c.close()


  def test_transform_populates_silver(conn):
      _insert_bronze(conn, _make_bronze_df("AAPL", 10))
      transform(conn=conn)
      count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
      assert count == 10


  def test_transform_silver_has_only_ohlcv_columns(conn):
      _insert_bronze(conn, _make_bronze_df("AAPL", 10))
      transform(conn=conn)
      cols = {
          row[0]
          for row in conn.execute(
              "SELECT column_name FROM information_schema.columns "
              "WHERE table_schema='silver' AND table_name='prices'"
          ).fetchall()
      }
      assert cols == {"ticker", "date", "open", "high", "low", "close", "volume"}


  def test_transform_drops_null_close(conn):
      df = _make_bronze_df("AAPL", 10)
      df.loc[0, "close"] = None
      _insert_bronze(conn, df)
      transform(conn=conn)
      count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
      assert count == 9


  def test_transform_deduplicates(conn):
      # Create bronze without PK to allow duplicate (ticker, date) pairs
      conn.execute("""
          CREATE TABLE bronze.prices (
              ticker      VARCHAR,
              date        DATE,
              open        DOUBLE,
              high        DOUBLE,
              low         DOUBLE,
              close       DOUBLE,
              volume      BIGINT,
              ingested_at TIMESTAMP
          )
      """)
      df = pd.DataFrame([
          {
              "ticker": "AAPL",
              "date": pd.Timestamp("2023-01-03").date(),
              "open": 99.0, "high": 101.0, "low": 98.0,
              "close": 100.0, "volume": 1_000_000,
              "ingested_at": pd.Timestamp("2023-01-03 10:00:00"),
          },
          {
              "ticker": "AAPL",
              "date": pd.Timestamp("2023-01-03").date(),
              "open": 99.5, "high": 101.5, "low": 98.5,
              "close": 100.5, "volume": 1_100_000,
              "ingested_at": pd.Timestamp("2023-01-03 11:00:00"),
          },
      ])
      conn.execute("INSERT INTO bronze.prices SELECT * FROM df")
      transform(conn=conn)
      count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
      assert count == 1
      close = conn.execute("SELECT close FROM silver.prices WHERE ticker='AAPL'").fetchone()[0]
      assert abs(close - 100.5) < 1e-9


  def test_transform_is_idempotent(conn):
      _insert_bronze(conn, _make_bronze_df("AAPL", 10))
      transform(conn=conn)
      transform(conn=conn)
      count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
      assert count == 10


  def test_transform_multiple_tickers(conn):
      _insert_bronze(conn, pd.concat([_make_bronze_df("AAPL", 10), _make_bronze_df("MSFT", 10)]))
      transform(conn=conn)
      count = conn.execute("SELECT COUNT(*) FROM silver.prices").fetchone()[0]
      assert count == 20
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  pytest tests/pipeline/test_transform.py -v
  ```
  Expected: several FAIL — `test_transform_silver_has_only_ohlcv_columns` fails because silver currently has indicator columns; `test_transform_drops_null_close` fails because current code doesn't drop nulls on close.

- [ ] **Step 3: Rewrite `pipeline/transform.py`**

  Replace the entire file:

  ```python
  from pipeline.utils import get_connection, get_logger, setup_schemas

  logger = get_logger(__name__)


  def _create_table(conn) -> None:
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
      clean = bronze.dropna(subset=["close"])
      clean = (
          clean.sort_values("ingested_at")
          .drop_duplicates(subset=["ticker", "date"], keep="last")
      )
      conn.execute("DELETE FROM silver.prices")
      conn.execute("""
          INSERT INTO silver.prices
          SELECT ticker, date, open, high, low, close, volume
          FROM clean
      """)
      logger.info("Transformed %d rows into silver.prices", len(clean))
      if own_conn:
          conn.close()


  if __name__ == "__main__":
      transform()
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```
  pytest tests/pipeline/test_transform.py -v
  ```
  Expected: all PASS

- [ ] **Step 5: Commit**

  ```bash
  git add pipeline/transform.py tests/pipeline/test_transform.py
  git commit -m "refactor: silver layer — null drop and dedup only, remove indicators"
  ```

---

## Task 3: Rewrite gold layer — absorb indicators, add `gold.prices`

**Files:**
- Modify: `tests/pipeline/test_aggregate.py` (full rewrite)
- Modify: `pipeline/aggregate.py` (full rewrite)

- [ ] **Step 1: Rewrite `tests/pipeline/test_aggregate.py`**

  Replace the entire file:

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
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  pytest tests/pipeline/test_aggregate.py -v
  ```
  Expected: FAIL — `test_aggregate_creates_gold_prices` fails because `gold.prices` does not exist.

- [ ] **Step 3: Rewrite `pipeline/aggregate.py`**

  Replace the entire file:

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
          CREATE TABLE IF NOT EXISTS gold.prices (
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
      results = []
      for ticker in silver["ticker"].unique():
          results.append(_compute_indicators(silver[silver["ticker"] == ticker]))
      gold_df = pd.concat(results, ignore_index=True)
      summary_df = _build_summary(gold_df)
      conn.execute("DELETE FROM gold.prices")
      conn.execute("""
          INSERT INTO gold.prices
          SELECT ticker, date, open, high, low, close, volume,
                 daily_return, ma_7, ma_21, ma_50, rsi_14,
                 macd, macd_signal, macd_hist, volatility_21
          FROM gold_df
      """)
      conn.execute("DELETE FROM gold.summary")
      conn.execute("""
          INSERT INTO gold.summary
          SELECT ticker, last_updated, last_close, pct_change_1d, pct_change_7d,
                 pct_change_30d, avg_volume_30d, current_rsi
          FROM summary_df
      """)
      logger.info(
          "Aggregated %d price rows and %d summary rows into gold",
          len(gold_df),
          len(summary_df),
      )
      if own_conn:
          conn.close()


  if __name__ == "__main__":
      aggregate()
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```
  pytest tests/pipeline/test_aggregate.py -v
  ```
  Expected: all PASS

- [ ] **Step 5: Commit**

  ```bash
  git add pipeline/aggregate.py tests/pipeline/test_aggregate.py
  git commit -m "refactor: gold layer — absorb indicators from silver, add gold.prices table"
  ```

---

## Task 4: Create features layer — ML normalization

**Files:**
- Create: `tests/pipeline/test_ml_features.py`
- Create: `pipeline/ml_features.py`

- [ ] **Step 1: Create `tests/pipeline/test_ml_features.py`**

  ```python
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
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```
  pytest tests/pipeline/test_ml_features.py -v
  ```
  Expected: ERROR — `ModuleNotFoundError: No module named 'pipeline.ml_features'`

- [ ] **Step 3: Create `pipeline/ml_features.py`**

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


  def _create_table(conn) -> None:
      conn.execute("""
          CREATE TABLE IF NOT EXISTS features.model_input (
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


  def ml_features(conn=None) -> None:
      own_conn = conn is None
      if own_conn:
          conn = get_connection()
      setup_schemas(conn)
      _create_table(conn)
      gold = conn.execute("SELECT * FROM gold.prices ORDER BY ticker, date").df()
      if gold.empty:
          logger.warning("gold.prices is empty — nothing to compute")
          if own_conn:
              conn.close()
          return
      features_df = _build_features(gold)
      conn.execute("DELETE FROM features.model_input")
      conn.execute("""
          INSERT INTO features.model_input
          SELECT ticker, date, close_norm, volume_norm,
                 ma_7_norm, ma_21_norm, rsi_14, daily_return
          FROM features_df
      """)
      logger.info("Computed %d ML feature rows into features.model_input", len(features_df))
      if own_conn:
          conn.close()


  if __name__ == "__main__":
      ml_features()
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```
  pytest tests/pipeline/test_ml_features.py -v
  ```
  Expected: all PASS

- [ ] **Step 5: Commit**

  ```bash
  git add pipeline/ml_features.py tests/pipeline/test_ml_features.py
  git commit -m "feat: add features layer — ml_features.py normalizes gold.prices into features.model_input"
  ```

---

## Task 5: Migrate the live database and update consumer references

**Files:**
- Maybe modify: `dashboard/app.py` (if it reads `silver.prices` indicator columns or `gold.features`)
- Maybe modify: `ml/dataset.py` (if it reads `gold.features`)

- [ ] **Step 1: Find all references to old table names**

  ```bash
  grep -rn "silver\.prices\|gold\.features" dashboard/ ml/ --include="*.py"
  ```

  Any file that reads columns like `silver.prices.ma_7` or `silver.prices.rsi_14` must now read from `gold.prices` instead. Any file that reads `gold.features` must now read from `features.model_input`.

- [ ] **Step 2: Update any files found in step 1**

  For each file reading `silver.prices` with indicator columns, change the source table to `gold.prices`.
  For each file reading `gold.features`, change the source table to `features.model_input`.
  Run `pytest` after each file to catch regressions.

- [ ] **Step 3: Drop `gold.features` from the live database**

  This removes the stale table that no longer has a writer. Run this once against the actual database file:

  ```bash
  python -c "
  from pipeline.utils import get_connection
  conn = get_connection()
  conn.execute('DROP TABLE IF EXISTS gold.features')
  conn.close()
  print('gold.features dropped')
  "
  ```

- [ ] **Step 4: Run the full test suite**

  ```
  pytest -v
  ```
  Expected: all PASS

- [ ] **Step 5: Commit**

  ```bash
  git add .
  git commit -m "refactor: update consumer references from gold.features to features.model_input"
  ```
