# Data Pipeline Design — Financial Intelligence Dashboard

**Date:** 2026-04-23
**Subsystem:** Pipeline (Phase 1 — Foundation)
**Status:** Approved

---

## Overview

End-to-end financial data pipeline ingesting 1 year of OHLCV data from Yahoo Finance for 4 tickers, transforming it through Bronze → Silver → Gold layers stored in a single DuckDB file. Entirely deterministic — no AI in this subsystem. The gold layer is consumed by the ML model (Phase 4) and the LLM chat agent (Phase 4).

---

## Scope

**Tickers (Phase 1):** `AAPL`, `MSFT`, `NVDA`, `BTC-USD`
**Historical depth:** 1 year
**Execution:** Manual CLI only (no scheduler — deferred to Phase 3)
**TDD:** All pipeline logic implemented test-first using `pytest` and in-memory DuckDB

---

## Folder Structure

```
pipeline/
├── __init__.py
├── ingest.py       # yfinance → bronze.prices
├── transform.py    # bronze.prices → silver.prices
├── aggregate.py    # silver.prices → gold.features + gold.summary
├── run.py          # chains all three stages
└── utils.py        # DB connection, schema setup, logging, config

data/
└── financial.duckdb

tests/
└── pipeline/
    ├── test_ingest.py
    ├── test_transform.py
    ├── test_aggregate.py
    └── test_utils.py
```

---

## Module Responsibilities

### `utils.py`
Shared foundation for all pipeline scripts and future subsystems (ML, chat, dashboard).

- `get_connection(path=None)` — returns a DuckDB connection; defaults to `data/financial.duckdb`, accepts `:memory:` for tests
- `setup_schemas(conn)` — creates `bronze`, `silver`, `gold` schemas if they don't exist
- `get_logger(name)` — returns a configured `logging.Logger` writing to stdout
- `TICKERS: list[str]` — `["AAPL", "MSFT", "NVDA", "BTC-USD"]`
- `DATA_DIR: Path` — resolved path to `data/` directory

### `ingest.py`
Fetches 1 year of daily OHLCV data from Yahoo Finance and upserts into `bronze.prices`.

- Per-ticker error handling: if `yfinance` raises for a ticker, log `WARNING` and skip; continue with remaining tickers
- Upsert by `(ticker, date)` — safe to re-run without duplicates
- Sets `ingested_at` to current UTC timestamp

### `transform.py`
Reads `bronze.prices`, computes technical indicators, writes `silver.prices`. Full recompute on every run.

Indicators computed per ticker (using pandas, sorted by date):
- `daily_return` — `(close - prev_close) / prev_close`
- `ma_7`, `ma_21`, `ma_50` — rolling close price averages
- `rsi_14` — standard 14-period RSI
- `macd`, `macd_signal`, `macd_hist` — 12/26/9 EMA configuration
- `volatility_21` — 21-day rolling standard deviation of `daily_return`

### `aggregate.py`
Reads `silver.prices`, produces two gold tables. Full recompute on every run.

- `gold.features` — min-max normalized features for LSTM input, scaled to [0, 1] per ticker across the full history window
- `gold.summary` — one row per ticker with dashboard-ready aggregates

### `run.py`
Chains `ingest → transform → aggregate`. If any stage raises an exception, execution stops immediately and the error is logged. No partial state propagates forward.

---

## DuckDB Schema

### `bronze.prices`
```sql
CREATE TABLE bronze.prices (
    ticker       VARCHAR NOT NULL,
    date         DATE NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    volume       BIGINT,
    ingested_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (ticker, date)
);
```

### `silver.prices`
```sql
CREATE TABLE silver.prices (
    ticker         VARCHAR NOT NULL,
    date           DATE NOT NULL,
    open           DOUBLE,
    high           DOUBLE,
    low            DOUBLE,
    close          DOUBLE,
    volume         BIGINT,
    daily_return   DOUBLE,
    ma_7           DOUBLE,
    ma_21          DOUBLE,
    ma_50          DOUBLE,
    rsi_14         DOUBLE,
    macd           DOUBLE,
    macd_signal    DOUBLE,
    macd_hist      DOUBLE,
    volatility_21  DOUBLE,
    PRIMARY KEY (ticker, date)
);
```

### `gold.features`
```sql
CREATE TABLE gold.features (
    ticker       VARCHAR NOT NULL,
    date         DATE NOT NULL,
    close_norm   DOUBLE,
    volume_norm  DOUBLE,
    ma_7_norm    DOUBLE,
    ma_21_norm   DOUBLE,
    rsi_14       DOUBLE,
    daily_return DOUBLE,
    PRIMARY KEY (ticker, date)
);
```

### `gold.summary`
```sql
CREATE TABLE gold.summary (
    ticker           VARCHAR PRIMARY KEY,
    last_updated     DATE,
    last_close       DOUBLE,
    pct_change_1d    DOUBLE,
    pct_change_7d    DOUBLE,
    pct_change_30d   DOUBLE,
    avg_volume_30d   DOUBLE,
    current_rsi      DOUBLE
);
```

---

## Data Flow & Error Handling

```
run.py
  │
  ├── ingest()    → upsert bronze.prices  (skips failed tickers, warns)
  ├── transform() → replace silver.prices (full recompute)
  └── aggregate() → replace gold.*        (full recompute)
```

- **Re-run safety:** all stages are idempotent
- **Ticker failures:** isolated at ingest level; downstream stages process only what landed in bronze
- **Stage failures:** propagate immediately; no partial gold/silver data committed

---

## Test Strategy

All tests use `DuckDB :memory:` — no file I/O, fully isolated, fast.

| Test file | What it covers |
|-----------|---------------|
| `test_utils.py` | Connection factory, schema creation, logger |
| `test_ingest.py` | Mocks `yfinance.download`; asserts bronze schema, upsert, ticker-skip behavior |
| `test_transform.py` | Feeds known bronze rows; asserts indicator values (RSI, MA, MACD, volatility) |
| `test_aggregate.py` | Feeds known silver rows; asserts normalization bounds and summary stats |

**Test runner:** `pytest`
**Convention:** tests written before implementation (TDD)

---

## Repository

`git@github.com:tutorres/Financial-Intelligence-Dashboard.git`

Git history starts from day one. Commit convention: `feat:`, `fix:`, `data:`, `ml:`, `docs:` (conventional commits).

---

## Out of Scope (This Phase)

- Scheduler / automation (Phase 3)
- Additional tickers beyond the initial 4 (Phase 3)
- Log files / log rotation (Phase 3)
- Dashboard (Phase 2)
- ML model (Phase 4)
- LLM chat agent (Phase 4)
