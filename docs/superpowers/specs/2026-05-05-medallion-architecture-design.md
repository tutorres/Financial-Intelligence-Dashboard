# Medallion Architecture Redesign

**Date:** 2026-05-05
**Status:** Approved

## Problem

The current pipeline violates single-responsibility per layer:

- **Silver** (`transform.py`) computes technical indicators (MA, RSI, MACD, volatility) — analytics work, not cleaning.
- **Gold** (`aggregate.py`) mixes business aggregations with ML feature engineering (normalization).

## Goal

Each layer has exactly one job:

- **Bronze**: receive raw data as-is
- **Silver**: clean and format data only
- **Gold**: compute indicators and business aggregations
- **Features**: prepare ML-ready normalized input

## Layer Responsibilities

| Layer | File | DuckDB Schema | Responsibility |
|---|---|---|---|
| Bronze | `pipeline/ingest.py` | `bronze` | Raw OHLCV + `ingested_at`. No changes. |
| Silver | `pipeline/transform.py` | `silver` | Null handling + deduplication only. |
| Gold | `pipeline/aggregate.py` | `gold` | Technical indicators + business aggregations. |
| Features | `pipeline/ml_features.py` *(new)* | `features` | Min-max normalization for LSTM input. |

## Pipeline Execution Order

```
ingest → transform → aggregate → ml_features
```

## Layer Details

### Silver — `transform.py`

**Input:** `bronze.prices`
**Output:** `silver.prices`

Logic:
1. Drop rows where `close` is null
2. Deduplicate on `(ticker, date)`, keeping the latest `ingested_at`
3. Write clean OHLCV to `silver.prices`

Schema:
```sql
ticker  VARCHAR NOT NULL,
date    DATE NOT NULL,
open    DOUBLE,
high    DOUBLE,
low     DOUBLE,
close   DOUBLE,
volume  BIGINT,
PRIMARY KEY (ticker, date)
```

**Removed:** all indicator columns (`daily_return`, `ma_*`, `rsi_14`, `macd*`, `volatility_21`).

### Gold — `aggregate.py`

**Input:** `silver.prices`
**Output:** `gold.prices` (new), `gold.summary` (unchanged)

Logic:
1. Compute per-ticker indicators: `daily_return`, `ma_7/21/50`, `rsi_14`, `macd/signal/hist`, `volatility_21`
2. Write enriched rows to `gold.prices`
3. Compute per-ticker summary stats (pct_change 1d/7d/30d, avg_volume_30d, current_rsi)
4. Write to `gold.summary`

`gold.prices` schema:
```sql
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
```

**Moved in:** `_rsi()` helper and `_compute_indicators()` from `transform.py`.
**Moved out:** `_build_features()` normalization logic to `ml_features.py`.

### Features — `ml_features.py` (new)

**Input:** `gold.prices`
**Output:** `features.model_input`

Logic:
1. Read from `gold.prices`
2. Apply min-max normalization per ticker for: `close`, `volume`, `ma_7`, `ma_21`
3. Keep `rsi_14` and `daily_return` as-is (already bounded ranges)
4. Drop rows with nulls (rolling window warm-up rows)
5. Write to `features.model_input`

`features.model_input` schema:
```sql
ticker       VARCHAR NOT NULL,
date         DATE NOT NULL,
close_norm   DOUBLE,
volume_norm  DOUBLE,
ma_7_norm    DOUBLE,
ma_21_norm   DOUBLE,
rsi_14       DOUBLE,
daily_return DOUBLE,
PRIMARY KEY (ticker, date)
```

**Renamed from:** `gold.features`.

## What Changes

| Item | Before | After |
|---|---|---|
| `silver.prices` columns | OHLCV + 9 indicator columns | OHLCV only |
| `gold.prices` | Does not exist | New table with OHLCV + indicators |
| `gold.features` | Normalized ML features | Dropped — replaced by `features.model_input` |
| `features.model_input` | Does not exist | New table in new schema |
| `_compute_indicators()` | Lives in `transform.py` | Moves to `aggregate.py` |
| `_build_features()` | Lives in `aggregate.py` | Moves to `ml_features.py` |

## Migration Notes

- `utils.py` (`setup_schemas`) must register the new `features` schema so DuckDB creates it on startup.
- The existing `gold.features` table in the database should be dropped after the migration (it is superseded by `features.model_input`).
- Any code in `ml/` or `dashboard/` reading from `gold.features` must be updated to read from `features.model_input`.

## What Does Not Change

- `bronze.prices` — no changes
- `gold.summary` — no changes
- All indicator formulas — same logic, just relocated
- Normalization logic — same min-max scaling, just in a new file
- Dashboard and ML code reading from `gold.summary` — unaffected
- ML code reading normalized features updates its source from `gold.features` to `features.model_input`
