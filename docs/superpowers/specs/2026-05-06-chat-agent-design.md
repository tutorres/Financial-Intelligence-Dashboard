# Chat Agent — Design Spec

**Date:** 2026-05-06
**Status:** Approved

---

## Overview

Add a Groq-powered natural language chat interface as a fifth tab in the Financial Intelligence Dashboard. Users ask questions about the currently selected ticker in Portuguese or English. The LLM answers using tool calls against the live DuckDB gold tables, then streams the response.

---

## Data Flow

```
User question
      │
      ▼
chat/agent.py ask(ticker, messages, conn)
      │
      ├─── Groq API call (non-streaming, tools enabled)
      │         │
      │         ▼
      │    LLM calls tool(s)?
      │    ├── yes → execute tool against DuckDB conn
      │    │         append tool result to messages
      │    │         second Groq call (streaming)
      │    └── no  → (rare) first response is already final
      │
      ▼
Iterator[str] chunks  ──►  st.write_stream()  ──►  Dashboard Chat tab
```

---

## File Structure

```
chat/
  __init__.py
  agent.py     — Groq client, tool definitions, ask() function

tests/chat/
  __init__.py
  test_agent.py
```

---

## `chat/agent.py`

### Tools

Three tools exposed to the LLM:

**`get_summary(ticker: str) -> dict`**
Queries `gold.summary`. Returns: `ticker, last_close, pct_change_1d, pct_change_7d, pct_change_30d, avg_volume_30d, current_rsi`.
Returns `{"error": "no data"}` if ticker not found.

**`get_recent_prices(ticker: str, days: int) -> list[dict]`**
Queries `gold.prices` for the last `days` calendar days. Returns at most 30 rows (most recent). Columns: `date, open, high, low, close, volume, daily_return, ma_7, ma_21, ma_50, rsi_14, macd, macd_signal, macd_hist, volatility_21`.
`days` defaults to 30 if not provided. Returns `[]` if no data.

**`get_prediction(ticker: str) -> dict`**
Queries `gold.predictions`. Returns: `signal, confidence, p_down, p_neutral, p_up, predicted_at`.
Returns `{"error": "no prediction available"}` if table doesn't exist or ticker not found.

### `ask(ticker, messages, conn) -> Iterator[str]`

```
ask(
    ticker:   str,
    messages: list[dict],   # OpenAI-style message dicts, mutable — function appends to it
    conn:     DuckDB connection,
) -> Iterator[str]
```

1. Build system prompt (see below)
2. POST to Groq: model `llama3-8b-8192`, tools enabled, `stream=False`
3. If response contains tool calls:
   - Append the assistant's tool-calls message (`response.choices[0].message`) to messages
   - Execute each tool, append `{"role": "tool", "tool_call_id": ..., "content": ...}` to messages
   - POST to Groq again: same model, `stream=True`, no tools
   - Yield chunks from `choice.delta.content`
4. If response has no tool calls (direct answer):
   - Yield the content string as a single chunk

### System Prompt

```
You are a financial data analyst assistant for the Financial Intelligence Dashboard.
The user is currently viewing ticker: {ticker}.
You have access to tools to look up real market data for any of the available tickers: AAPL, MSFT, GOOGL, NVDA, PETR4.SA, VALE3.SA, BTC-USD, ETH-USD.
Answer in the same language as the user's question (Portuguese or English).
Be concise and specific. When citing numbers, round to 2 decimal places.
If asked about something outside financial data, politely decline.
```

### Groq client

Instantiated once at module level:
```python
from groq import Groq
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
```

`GROQ_API_KEY` is loaded from `.env` via `python-dotenv` at import time (`load_dotenv()` called at top of module). If the key is absent, `_client` is `None` and `ask()` raises `RuntimeError("GROQ_API_KEY not set")`.

---

## Dashboard — Chat Tab

Fifth tab `"Chat"` added to `dashboard/pages/1_Dashboard.py`.

**Session state:**
```python
if ticker not in st.session_state.get("chat_messages", {}):
    st.session_state.setdefault("chat_messages", {})[ticker] = []
messages = st.session_state["chat_messages"][ticker]
```
Switching tickers moves to a different key — conversation resets automatically.

**Tab layout:**
1. If `GROQ_API_KEY` is absent: show `st.info("Set GROQ_API_KEY in your .env file to enable chat.")` and stop.
2. Render existing messages (user = `st.chat_message("user")`, assistant = `st.chat_message("assistant")`).
3. `prompt = st.chat_input("Ask about {ticker}…")`
4. On submit:
   - Append `{"role": "user", "content": prompt}` to `messages`
   - Display user bubble
   - Call `ask(ticker, messages, conn)` inside `st.chat_message("assistant"): st.write_stream(...)`
   - Collect streamed chunks into `full_response`
   - Append `{"role": "assistant", "content": full_response}` to `messages`

---

## `tests/chat/test_agent.py`

All tests use an in-memory DuckDB with gold schema populated. Groq client is monkeypatched.

- `test_get_summary_tool` — tool returns correct fields for known ticker
- `test_get_summary_tool_unknown_ticker` — returns `{"error": "no data"}`
- `test_get_recent_prices_tool_capped_at_30` — insert 60 rows, verify at most 30 returned
- `test_get_prediction_tool_no_table` — returns `{"error": "no prediction available"}` when table absent
- `test_ask_returns_iterator` — mock Groq client, verify `ask()` returns an iterable of strings

---

## Constraints

- `groq>=0.9.0` added to `requirements.txt`
- `python-dotenv>=1.0.0` added to `requirements.txt`
- `GROQ_API_KEY` in `.env` (documented, not committed)
- No streaming on the first Groq call (tool resolution); streaming only on the final answer call
- Tool calls always operate on the DuckDB connection passed in — no second DB connection opened
- `ask()` never catches Groq API errors — they propagate to the tab, which shows `st.error()`
