import json
import os
from collections.abc import Iterator
from datetime import date, timedelta

import duckdb
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
    ).df()
    if row.empty:
        return {"error": "no data"}
    return row.astype(object).iloc[0].to_dict()


def _get_recent_prices(conn, ticker: str, days: int = 30) -> list:
    cutoff = date.today() - timedelta(days=days)
    df = conn.execute(
        "SELECT date, open, high, low, close, volume, daily_return, "
        "ma_7, ma_21, ma_50, rsi_14, macd, macd_signal, macd_hist, volatility_21 "
        "FROM gold.prices WHERE ticker = ? AND date >= ? "
        "ORDER BY date DESC LIMIT 30",
        [ticker, cutoff],
    ).df()
    df["date"] = df["date"].astype(str)
    return df.to_dict(orient="records")


def _get_prediction(conn, ticker: str) -> dict:
    try:
        row = conn.execute(
            "SELECT signal, confidence, p_down, p_neutral, p_up, predicted_at "
            "FROM gold.predictions WHERE ticker = ? ORDER BY predicted_at DESC LIMIT 1",
            [ticker],
        ).df()
    except duckdb.CatalogException:
        return {"error": "no prediction available"}
    if row.empty:
        return {"error": "no prediction available"}
    d = row.astype(object).iloc[0].to_dict()
    d["predicted_at"] = str(d["predicted_at"])
    return d


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
