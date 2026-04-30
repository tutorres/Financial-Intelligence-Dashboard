# Project Status

## Phases

### Phase 1 — Data Pipeline ✅ DONE
**Spec:** `docs/superpowers/specs/2026-04-23-data-pipeline-design.md`
**Plan:** `docs/superpowers/plans/2026-04-23-data-pipeline.md`

- Bronze layer: raw OHLCV ingestion via yfinance → `bronze.prices`
- Silver layer: technical indicators (RSI 14, MACD 12/26/9, MA 7/21/50, volatility 21d, daily return) → `silver.prices`
- Gold layer: per-ticker aggregated stats + normalized feature sets → `gold.summary`, `gold.features`
- `pipeline/run.py` chains all three stages
- Full pytest suite (utils, ingest, transform, aggregate)
- Auto-runs on Streamlit Cloud cold start when DB is empty

---

### Phase 2 — Dashboard ✅ DONE
**Spec:** `docs/superpowers/specs/2026-04-28-dashboard-design.md`
**Plan:** `docs/superpowers/plans/2026-04-28-dashboard.md`

- Streamlit multipage app (`dashboard/app.py` + `dashboard/pages/1_Dashboard.py`)
- Three tabs: Overview (metrics + summary), Price & Volume (candlestick + volume), Technical Indicators (RSI + MACD)
- Chart descriptions explaining how to read each indicator
- Full chart heights for readability
- Deployed to Streamlit Cloud, auto-pipeline on cold start

---

### Phase 3 — UI Redesign ✅ DONE
**Spec:** `docs/superpowers/specs/2026-04-29-ui-redesign-design.md`
**Plan:** `docs/superpowers/plans/2026-04-29-ui-redesign.md`

- Dark terminal theme across landing page and dashboard
  - Colors: `#0d0d0d` bg, `#f8fafc` text, `#94a3b8` muted, `#00ff88` green accent, `#ff4d4d` red
  - Font: `'Courier New', monospace` throughout
- Landing page rebuilt as full HTML: nav, hero with live market snapshot, pipeline diagram, tech stack grid, asset tags, footer
- `dashboard/style.py` with `inject_global_css()` and `inject_dashboard_css()` helpers
- All 4 Plotly chart builders updated with matching dark theme
- Green CTA button linking to dashboard in same tab
- 67 tests green

---

### Phase 4 — ML (LSTM Trend Classifier) 🔲 NOT STARTED
**Goal:** Train a PyTorch LSTM to classify the next-day trend (up / down / neutral) for each ticker.

**Scope:**
- `ml/dataset.py` — build 30-day sliding window sequences from `silver.prices` features: normalized close, volume, MA 7/21, RSI, daily return
- `ml/model.py` — LSTM architecture (input → hidden → dropout → linear → softmax, 3 classes)
- `ml/train.py` — training loop, checkpoint saving, validation split
- `ml/predict.py` — load checkpoint, run inference, write predictions to `gold.predictions`
- Show LSTM prediction badge (UP / DOWN / NEUTRAL + confidence) in the dashboard Overview tab

**Key decisions to make before planning:**
- Sequence length (30 days is the current spec — confirm)
- Hidden size and number of layers
- How to handle tickers with insufficient history (< 30 days)
- Whether to train one model per ticker or one shared model

---

### Phase 5 — LLM Chat Interface 🔲 NOT STARTED
**Goal:** Natural language queries over the gold DuckDB tables via Groq API.

**Scope:**
- `chat/agent.py` — Groq API client (llama3-8b-8192 or mixtral-8x7b), text-to-SQL or tool-calling over `gold.summary` and `gold.features`
- Supports questions in Portuguese and English
- Chat tab added to the dashboard
- Graceful fallback when `GROQ_API_KEY` is not set

**Key decisions to make before planning:**
- Tool-calling vs. text-to-SQL approach
- Whether to expose raw SQL results or format them as natural language answers
- How to handle questions outside the available data scope

---

### Phase 6 — Scheduling 🔲 NOT STARTED
**Goal:** Daily automatic data refresh after market close.

**Scope:**
- APScheduler or `schedule` library triggering `pipeline/run.py` at ~18:00 ET on weekdays
- On Streamlit Cloud this is handled by the cold-start auto-run; scheduling is relevant for a self-hosted deployment

---

## Current State

```
master @ 254b1da
Deployed: Streamlit Cloud (auto-deploys from master)
Tests: 67 passed
```

Next recommended step: **Phase 4 (ML)** — start with `/brainstorm` to finalize architecture decisions before writing the plan.
