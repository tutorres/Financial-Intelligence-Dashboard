# Financial Intelligence Dashboard

End-to-end financial data pipeline with interactive analytics, technical indicators, LSTM trend prediction, and a natural language query interface.

**[Live Demo →](https://share.streamlit.io)** *(replace with your Streamlit Cloud URL)*

---

## Stack

| Layer | Tech |
|---|---|
| Data ingestion | yfinance |
| Storage | DuckDB (Bronze → Silver → Gold) |
| Indicators | pandas (RSI, MACD, MA 7/21/50, volatility) |
| Charts | Plotly |
| UI | Streamlit |
| ML | PyTorch LSTM |
| LLM | Groq API (llama3 / mixtral) |

## Assets covered

`AAPL` `MSFT` `GOOGL` `NVDA` `PETR4.SA` `VALE3.SA` `BTC-USD` `ETH-USD`

## Architecture

```
yfinance → Bronze (raw OHLCV) → Silver (indicators) → Gold (aggregated)
                                                            ↓
                                           Streamlit Dashboard + LSTM + Groq Chat
```

## Run locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
echo "GROQ_API_KEY=your_key" > .env

# 3. Run the data pipeline
python pipeline/run.py

# 4. Launch the dashboard
streamlit run dashboard/app.py
```

## Tests

```bash
pytest
```

---

Built by [Arthur Torres](https://github.com/tutorres) · Computer Engineering
