# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Financial Intelligence Dashboard — an end-to-end financial data pipeline with ML-based trend prediction (PyTorch LSTM) and a natural language chat interface (Groq LLM). Built as a portfolio project by Arthur Torres (Computer Engineering student), currently in early development.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit dashboard
streamlit run dashboard/app.py

# Run pipeline stages individually
python pipeline/ingest.py      # Fetch raw data → bronze layer
python pipeline/transform.py   # Bronze → silver (indicators)
python pipeline/aggregate.py   # Silver → gold (model-ready)

# ML
python ml/train.py             # Train LSTM model
python ml/predict.py           # Run inference
```

Environment variables go in `.env` (loaded via `python-dotenv`). Required keys: `GROQ_API_KEY`.

## Architecture

Data flows through a **Bronze → Silver → Gold** warehouse pattern, all stored in **DuckDB** (`financial.duckdb`):

- **Bronze** (`pipeline/ingest.py`): Raw OHLCV + ingestion timestamp from `yfinance`. No transformations.
- **Silver** (`pipeline/transform.py`): Null handling, deduplication, and technical indicators — moving averages (7d/21d/50d), RSI, MACD, daily returns, volatility.
- **Gold** (`pipeline/aggregate.py`): Aggregated per-ticker metrics and feature-engineered datasets ready for LSTM input and dashboard consumption.

**ML** (`ml/`): PyTorch LSTM for stock trend classification (up/down/neutral). Input is 30-day sequences of: normalized close price, volume, 7d/21d MAs, RSI, daily return. `dataset.py` handles feature engineering, `model.py` defines the LSTM, `train.py` runs training, `predict.py` runs inference.

**Chat** (`chat/agent.py`): Groq API (llama3-8b-8192 or mixtral-8x7b) with text-to-SQL or tool-calling over the gold DuckDB tables. Supports questions in Portuguese or English.

**Dashboard** (`dashboard/app.py`): Streamlit app with Plotly charts. Displays price history, volume, technical indicators per ticker, LSTM predictions, and the chat interface.

**Scheduling**: APScheduler or `schedule` library for daily ingestion after market close.

## Conventions

- **Python 3.11+**, PEP8 style, type hints encouraged
- **Commits**: conventional commits — `feat:`, `fix:`, `data:`, `ml:`, `docs:`
- **Branching**: `main` (stable) + feature branches
- **Tickers in scope**: `AAPL`, `MSFT`, `GOOGL`, `NVDA`, `PETR4.SA`, `VALE3.SA`, `BTC-USD`, `ETH-USD`

## Key Design Decisions (from `context.yaml`)

- DuckDB is the primary storage engine (SQLite is an acceptable fallback if DuckDB causes friction)
- Groq is chosen for LLM because its free tier supports fast open-source model inference
- The pipeline is intentionally lightweight (no Airflow/Prefect) — plain Python scripts with a scheduler
- Deployment target is Streamlit Cloud (free tier)
