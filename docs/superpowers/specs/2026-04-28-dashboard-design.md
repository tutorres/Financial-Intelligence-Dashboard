# Dashboard Design — Financial Intelligence Dashboard

**Date:** 2026-04-28
**Subsystem:** Dashboard (Phase 2)
**Status:** Approved

---

## Overview

A single-page Streamlit dashboard that reads from the DuckDB gold/silver layers and displays interactive Plotly charts for the 4 pipeline tickers. Ticker picker and time range at the top; three tabs below for Overview, Price & Volume, and Technical Indicators.

---

## Scope

**Tickers:** `AAPL`, `MSFT`, `NVDA`, `BTC-USD`
**Time ranges:** 30d / 90d / 180d / 1Y (radio buttons)
**Data sources:** `silver.prices` (charts), `gold.summary` (overview metrics)
**Out of scope:** LSTM predictions, LLM chat, scheduler, auto-refresh

---

## Folder Structure

```
dashboard/
└── app.py
```

No `__init__.py` needed — Streamlit runs `app.py` directly.

---

## Architecture

`dashboard/app.py` is a single Streamlit file. Two focused query functions:

- `load_summary(conn, ticker)` — queries `gold.summary` for the overview metric row
- `load_prices(conn, ticker, days)` — queries `silver.prices` for OHLCV + all indicators, filtered to the last N days

The DuckDB connection is opened once and cached with `@st.cache_resource` so it is not re-opened on every rerender. All queries run on ticker/time-range change — data volume is small enough that no further caching is needed.

---

## UI Layout

### Global Controls (above tabs)

Two controls, rendered side by side:
- `st.selectbox` — ticker selector: `["AAPL", "MSFT", "NVDA", "BTC-USD"]`
- `st.radio` (horizontal) — time range: `{"30d": 30, "90d": 90, "180d": 180, "1Y": 365}`

Both affect all three tabs simultaneously.

### Tab 1 — Overview

Four `st.metric` cards in one row:

| Metric | Source column |
|--------|--------------|
| Last Close | `last_close` |
| 1-day Change % | `pct_change_1d` |
| 7-day Change % | `pct_change_7d` |
| 30-day Change % | `pct_change_30d` |

Second row — two metrics:

| Metric | Source column | Note |
|--------|--------------|------|
| Avg Volume (30d) | `avg_volume_30d` | Formatted with `K`/`M` suffix |
| Current RSI | `current_rsi` | Labeled: `< 30` → Oversold, `> 70` → Overbought, else Neutral |

### Tab 2 — Price & Volume

Two stacked Plotly charts:

1. **Candlestick** — `open`, `high`, `low`, `close` from `silver.prices`. MA7, MA21, MA50 overlaid as colored lines. Legend shows all four series.
2. **Volume bars** — daily volume, bars colored green if `close >= open`, red otherwise.

### Tab 3 — Technical Indicators

Two stacked Plotly charts:

1. **RSI** — 14-period RSI line (0–100 range), dashed horizontal reference lines at 30 and 70.
2. **MACD** — `macd_hist` as bars, `macd` line and `macd_signal` line on the same subplot.

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| DB file missing or `silver`/`gold` tables empty | `st.warning("No data found. Run python pipeline/run.py first.")` then `st.stop()` |
| No rows for ticker in selected time range | `st.info("No data available for this period.")` inside affected tab only |

No other error handling — the pipeline guarantees clean data in silver/gold.

---

## Data Flow

```
financial.duckdb
  ├── silver.prices  →  load_prices()  →  Tab 2 (candlestick + volume)
  │                                    →  Tab 3 (RSI + MACD)
  └── gold.summary   →  load_summary() →  Tab 1 (metric cards)
```

---

## Dependencies Added

```
streamlit>=1.32.0
plotly>=5.20.0
```

Both added to `requirements.txt`.

---

## Run Command

```bash
streamlit run dashboard/app.py
```
