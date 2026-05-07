# Chat Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Groq-powered Chat tab to the Financial Intelligence Dashboard that answers natural language questions about the selected ticker by calling tools against live DuckDB gold tables and streaming the response.

**Architecture:** `chat/agent.py` exposes `ask(ticker, messages, conn) -> Iterator[str]`. It makes a non-streaming Groq call with tools to resolve data lookups, then a second streaming call for the final answer. The dashboard fifth tab manages per-ticker message history in `st.session_state` and renders via `st.write_stream()`.

**Tech Stack:** `groq>=0.9.0`, `python-dotenv>=1.0.0`, DuckDB, Streamlit `st.write_stream` / `st.chat_input`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `requirements.txt` | Modify | Add groq, python-dotenv |
| `chat/__init__.py` | Create | Package marker |
| `chat/agent.py` | Create | Groq client, tool functions, ask() |
| `tests/chat/__init__.py` | Create | Package marker |
| `tests/chat/test_agent.py` | Create | Tests for tool functions and ask() |
| `dashboard/pages/1_Dashboard.py` | Modify lines 98, 199–201 | Add 5th Chat tab |

---

### Task 1: Dependencies and package skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `chat/__init__.py`
- Create: `tests/chat/__init__.py`

- [ ] **Step 1: Update requirements.txt**

Replace the full file with:

```
--extra-index-url https://download.pytorch.org/whl/cpu
duckdb>=0.10.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
pytest>=8.0.0
streamlit>=1.32.0
plotly>=5.20.0
torch>=2.0.0
groq>=0.9.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Install new dependencies**

```bash
pip install groq python-dotenv
```

Expected: packages install without error. `python -c "import groq; import dotenv; print('ok')"` prints `ok`.

- [ ] **Step 3: Create empty package markers**

`chat/__init__.py` — empty file.

`tests/chat/__init__.py` — empty file.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt chat/__init__.py tests/chat/__init__.py
git commit -m "feat: add groq + python-dotenv deps and chat package skeleton"
```

---

### Task 2: Tool functions (TDD)

**Files:**
- Create: `tests/chat/test_agent.py`
- Create: `chat/agent.py` (tool functions only for now)

- [ ] **Step 1: Write the failing tests**

`tests/chat/test_agent.py`:

```python
from datetime import date, timedelta

import duckdb
import pytest


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA gold")
    c.execute("""
        CREATE TABLE gold.summary (
            ticker         VARCHAR PRIMARY KEY,
            last_updated   DATE,
            last_close     DOUBLE,
            pct_change_1d  DOUBLE,
            pct_change_7d  DOUBLE,
            pct_change_30d DOUBLE,
            avg_volume_30d DOUBLE,
            current_rsi    DOUBLE
        )
    """)
    c.execute("""
        CREATE TABLE gold.prices (
            ticker        VARCHAR NOT NULL,
            date          DATE NOT NULL,
            open          DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            volume        BIGINT,
            daily_return  DOUBLE, ma_7 DOUBLE, ma_21 DOUBLE, ma_50 DOUBLE,
            rsi_14        DOUBLE, macd DOUBLE, macd_signal DOUBLE,
            macd_hist     DOUBLE, volatility_21 DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)
    yield c
    c.close()


def test_get_summary_tool(conn):
    conn.execute("""
        INSERT INTO gold.summary VALUES
        ('AAPL', '2024-01-03', 185.0, 1.5, 3.2, 5.0, 1050000.0, 55.0)
    """)
    from chat.agent import _get_summary
    result = _get_summary(conn, "AAPL")
    assert result["ticker"] == "AAPL"
    assert abs(result["last_close"] - 185.0) < 1e-9
    assert "pct_change_1d" in result
    assert "current_rsi" in result


def test_get_summary_tool_unknown_ticker(conn):
    from chat.agent import _get_summary
    result = _get_summary(conn, "UNKNOWN")
    assert result == {"error": "no data"}


def test_get_recent_prices_tool_capped_at_30(conn):
    today = date.today()
    for i in range(60):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute("""
            INSERT INTO gold.prices VALUES
            ('AAPL', ?, 100.0, 102.0, 99.0, 101.0, 1000000,
             0.01, 100.5, 100.3, 100.1, 55.0, 0.5, 0.4, 0.1, 0.015)
        """, [d])
    from chat.agent import _get_recent_prices
    result = _get_recent_prices(conn, "AAPL", days=365)
    assert len(result) <= 30
    assert all("date" in row and "close" in row for row in result)


def test_get_prediction_tool_no_table(conn):
    from chat.agent import _get_prediction
    result = _get_prediction(conn, "AAPL")
    assert result == {"error": "no prediction available"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/chat/test_agent.py -v
```

Expected: 4 errors — `ImportError: cannot import name '_get_summary' from 'chat.agent'`

- [ ] **Step 3: Create chat/agent.py with tool functions**

```python
import json
import os
from collections.abc import Iterator
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

_GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
try:
    from groq import Groq
    _client = Groq(api_key=_GROQ_API_KEY) if _GROQ_API_KEY else None
except Exception:
    _client = None


def is_available() -> bool:
    return _client is not None


def _get_summary(conn, ticker: str) -> dict:
    row = conn.execute(
        "SELECT ticker, last_close, pct_change_1d, pct_change_7d, pct_change_30d, "
        "avg_volume_30d, current_rsi FROM gold.summary WHERE ticker = ?",
        [ticker],
    ).fetchdf()
    if row.empty:
        return {"error": "no data"}
    return row.iloc[0].to_dict()


def _get_recent_prices(conn, ticker: str, days: int = 30) -> list:
    cutoff = date.today() - timedelta(days=days)
    df = conn.execute(
        "SELECT date, open, high, low, close, volume, daily_return, "
        "ma_7, ma_21, ma_50, rsi_14, macd, macd_signal, macd_hist, volatility_21 "
        "FROM gold.prices WHERE ticker = ? AND date >= ? "
        "ORDER BY date DESC LIMIT 30",
        [ticker, cutoff],
    ).df()
    return df.to_dict(orient="records")


def _get_prediction(conn, ticker: str) -> dict:
    try:
        row = conn.execute(
            "SELECT signal, confidence, p_down, p_neutral, p_up, predicted_at "
            "FROM gold.predictions WHERE ticker = ?",
            [ticker],
        ).fetchdf()
    except Exception:
        return {"error": "no prediction available"}
    if row.empty:
        return {"error": "no prediction available"}
    return row.iloc[0].to_dict()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/chat/test_agent.py::test_get_summary_tool tests/chat/test_agent.py::test_get_summary_tool_unknown_ticker tests/chat/test_agent.py::test_get_recent_prices_tool_capped_at_30 tests/chat/test_agent.py::test_get_prediction_tool_no_table -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add chat/agent.py tests/chat/test_agent.py
git commit -m "feat: add chat tool functions — get_summary, get_recent_prices, get_prediction"
```

---

### Task 3: ask() function (TDD)

**Files:**
- Modify: `tests/chat/test_agent.py` (append one test)
- Modify: `chat/agent.py` (append `_SYSTEM_PROMPT`, `_TOOLS`, `_dispatch_tool`, `ask`)

- [ ] **Step 1: Append the failing test to tests/chat/test_agent.py**

```python
def test_ask_returns_iterator(monkeypatch):
    import chat.agent as agent

    class _FakeAssistant:
        content = "AAPL fechou em alta de 1.50% hoje."
        tool_calls = None

    class _FakeResponse:
        choices = [type("C", (), {"message": _FakeAssistant()})()]

    class _FakeCompletions:
        @staticmethod
        def create(**kwargs):
            return _FakeResponse()

    class _FakeClient:
        chat = type("Ch", (), {"completions": _FakeCompletions})()

    monkeypatch.setattr(agent, "_client", _FakeClient())

    conn = duckdb.connect(":memory:")
    messages = [{"role": "user", "content": "Como está o AAPL hoje?"}]
    result = list(agent.ask("AAPL", messages, conn))
    assert isinstance(result, list)
    assert all(isinstance(c, str) for c in result)
    assert "".join(result) == "AAPL fechou em alta de 1.50% hoje."
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/chat/test_agent.py::test_ask_returns_iterator -v
```

Expected: FAIL — `ImportError` or `AttributeError` (ask not yet defined)

- [ ] **Step 3: Append _SYSTEM_PROMPT, _TOOLS, _dispatch_tool, and ask() to chat/agent.py**

```python
_SYSTEM_PROMPT = (
    "You are a financial data analyst assistant for the Financial Intelligence Dashboard.\n"
    "The user is currently viewing ticker: {ticker}.\n"
    "You have access to tools to look up real market data for any of the available tickers: "
    "AAPL, MSFT, GOOGL, NVDA, PETR4.SA, VALE3.SA, BTC-USD, ETH-USD.\n"
    "Answer in the same language as the user's question (Portuguese or English).\n"
    "Be concise and specific. When citing numbers, round to 2 decimal places.\n"
    "If asked about something outside financial data, politely decline."
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": (
                "Get the latest summary statistics for a ticker: last close price, "
                "1/7/30-day percentage changes, 30-day average volume, and RSI."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock or crypto ticker symbol, e.g. AAPL, BTC-USD",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_prices",
            "description": (
                "Get recent OHLCV data and technical indicators (MA7/21/50, RSI, MACD, "
                "volatility) for a ticker. Returns at most 30 rows ordered most-recent first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock or crypto ticker symbol",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Calendar days to look back (default 30)",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_prediction",
            "description": (
                "Get the LSTM model's latest trend prediction for a ticker: "
                "UP/DOWN/NEUTRAL signal, confidence score, and class probabilities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock or crypto ticker symbol",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
]


def _dispatch_tool(tool_call, conn) -> dict | list:
    args = json.loads(tool_call.function.arguments)
    name = tool_call.function.name
    if name == "get_summary":
        return _get_summary(conn, args["ticker"])
    if name == "get_recent_prices":
        return _get_recent_prices(conn, args["ticker"], args.get("days", 30))
    if name == "get_prediction":
        return _get_prediction(conn, args["ticker"])
    return {"error": f"unknown tool: {name}"}


def ask(ticker: str, messages: list[dict], conn) -> Iterator[str]:
    if _client is None:
        raise RuntimeError("GROQ_API_KEY not set")

    def _build(msgs: list) -> list:
        return [{"role": "system", "content": _SYSTEM_PROMPT.format(ticker=ticker)}, *msgs]

    response = _client.chat.completions.create(
        model="llama3-8b-8192",
        messages=_build(messages),
        tools=_TOOLS,
        stream=False,
    )
    assistant_msg = response.choices[0].message

    if not assistant_msg.tool_calls:
        yield assistant_msg.content or ""
        return

    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in assistant_msg.tool_calls
        ],
    })
    for tc in assistant_msg.tool_calls:
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(_dispatch_tool(tc, conn), default=str),
        })

    stream = _client.chat.completions.create(
        model="llama3-8b-8192",
        messages=_build(messages),
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
```

- [ ] **Step 4: Run all chat tests**

```bash
pytest tests/chat/test_agent.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Run the full suite to catch regressions**

```bash
pytest --tb=short -q
```

Expected: 85 passed (80 existing + 5 new)

- [ ] **Step 6: Commit**

```bash
git add chat/agent.py tests/chat/test_agent.py
git commit -m "feat: add ask() — Groq tool-calling + streaming chat agent"
```

---

### Task 4: Dashboard Chat tab

**Files:**
- Modify: `dashboard/pages/1_Dashboard.py`

Current state: line 98 has `tab1, tab2, tab3, tab4 = st.tabs(...)`. The `with tab4:` block ends at line 198. `main()` is called at line 201.

- [ ] **Step 1: Add import at the top of 1_Dashboard.py**

After the existing imports (after line 23 `from pipeline.utils import TICKERS, get_connection as _get_raw_conn`), add:

```python
from chat.agent import ask as _ask, is_available as _chat_available
```

- [ ] **Step 2: Expand the tab declaration (line 98)**

Replace:
```python
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Price & Volume", "Technical Indicators", "Predictions"])
```

With:
```python
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Price & Volume", "Technical Indicators", "Predictions", "Chat"])
```

- [ ] **Step 3: Add the Chat tab block after the closing of tab4 (after line 198)**

Insert between the `st.plotly_chart(fig_prediction_probs(pred)...)` line and the blank line before `main()`:

```python
    with tab5:
        if not _chat_available():
            st.info("Set GROQ_API_KEY in your .env file to enable chat.")
        else:
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = {}
            if ticker not in st.session_state.chat_messages:
                st.session_state.chat_messages[ticker] = []
            messages = st.session_state.chat_messages[ticker]

            for msg in messages:
                if msg.get("role") in ("user", "assistant") and msg.get("content"):
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            if prompt := st.chat_input(f"Ask about {ticker}…"):
                messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                try:
                    with st.chat_message("assistant"):
                        full_response = st.write_stream(_ask(ticker, messages, conn))
                    messages.append({"role": "assistant", "content": full_response})
                except Exception as exc:
                    st.error(f"Chat error: {exc}")
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest --tb=short -q
```

Expected: 85 passed

- [ ] **Step 5: Commit**

```bash
git add dashboard/pages/1_Dashboard.py
git commit -m "feat: add Chat tab — Groq LLM with streaming and per-ticker session history"
```
