# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit dashboard with three tabs (Overview, Price & Volume, Technical Indicators) reading from the existing DuckDB pipeline output.

**Architecture:** Single `dashboard/app.py`. Query functions accept an explicit `conn` parameter for testability. Chart builders return `go.Figure` objects. All Streamlit UI lives inside `main()`, called only under `if __name__ == "__main__":` so tests import query functions cleanly without triggering Streamlit.

**Tech Stack:** Python 3.11+, streamlit>=1.32.0, plotly>=5.20.0, duckdb, pandas

---

## File Map

| File | Role |
|------|------|
| `requirements.txt` | Add streamlit and plotly |
| `dashboard/__init__.py` | Makes dashboard a package |
| `dashboard/app.py` | Query functions, chart builders, Streamlit `main()` |
| `tests/dashboard/__init__.py` | Makes tests/dashboard a package |
| `tests/dashboard/test_app.py` | Tests for query functions and helpers |

---

## Task 1: Dependencies + bootstrap

**Files:**
- Modify: `requirements.txt`
- Create: `dashboard/__init__.py`
- Create: `tests/dashboard/__init__.py`

- [ ] **Step 1: Update requirements.txt**

Replace contents with:

```
duckdb>=0.10.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
pytest>=8.0.0
streamlit>=1.32.0
plotly>=5.20.0
```

- [ ] **Step 2: Create empty package init files**

Create `dashboard/__init__.py` — empty.
Create `tests/dashboard/__init__.py` — empty.

- [ ] **Step 3: Install new dependencies**

```bash
pip install streamlit plotly
```

Expected: both install without errors.

- [ ] **Step 4: Verify imports**

```bash
python -c "import streamlit; import plotly; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt dashboard/__init__.py tests/dashboard/__init__.py
git commit -m "chore: add streamlit and plotly dependencies"
```

---

## Task 2: Query functions + tests

**Files:**
- Create: `tests/dashboard/test_app.py`
- Create: `dashboard/app.py` (stub — query functions only)

- [ ] **Step 1: Write failing tests**

`tests/dashboard/test_app.py`:
```python
from datetime import date, timedelta

import duckdb
import pandas as pd
import pytest

from dashboard.app import fmt_volume, load_prices, load_summary, rsi_signal


def _make_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA gold")
    conn.execute("""
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
    conn.execute("CREATE SCHEMA silver")
    conn.execute("""
        CREATE TABLE silver.prices (
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
    return conn


@pytest.fixture
def conn():
    c = _make_conn()
    yield c
    c.close()


@pytest.fixture
def conn_with_data():
    c = _make_conn()
    c.execute("""
        INSERT INTO gold.summary VALUES
        ('AAPL', '2024-01-03', 185.0, 1.5, 3.2, 5.0, 1050000.0, 55.0)
    """)
    today = date.today()
    for i in range(60):
        d = (today - timedelta(days=i)).isoformat()
        c.execute("""
            INSERT INTO silver.prices VALUES
            ('AAPL', ?, 100.0, 102.0, 99.0, 101.0, 1000000,
             0.01, 100.5, 100.3, 100.1, 55.0, 0.5, 0.4, 0.1, 0.015)
        """, [d])
    yield c
    c.close()


# --- load_summary ---

def test_load_summary_returns_dict(conn_with_data):
    result = load_summary(conn_with_data, "AAPL")
    assert result is not None
    assert isinstance(result, dict)


def test_load_summary_correct_values(conn_with_data):
    result = load_summary(conn_with_data, "AAPL")
    assert abs(result["last_close"] - 185.0) < 1e-9
    assert abs(result["current_rsi"] - 55.0) < 1e-9


def test_load_summary_returns_none_for_unknown_ticker(conn_with_data):
    assert load_summary(conn_with_data, "BADTICKER") is None


def test_load_summary_returns_none_when_empty(conn):
    assert load_summary(conn, "AAPL") is None


# --- load_prices ---

def test_load_prices_returns_dataframe(conn_with_data):
    result = load_prices(conn_with_data, "AAPL", 30)
    assert isinstance(result, pd.DataFrame)


def test_load_prices_filters_by_ticker(conn_with_data):
    assert load_prices(conn_with_data, "MSFT", 365).empty


def test_load_prices_filters_by_days(conn_with_data):
    result_30 = load_prices(conn_with_data, "AAPL", 30)
    result_60 = load_prices(conn_with_data, "AAPL", 60)
    assert len(result_30) < len(result_60)


def test_load_prices_ordered_by_date(conn_with_data):
    result = load_prices(conn_with_data, "AAPL", 60)
    dates = result["date"].tolist()
    assert dates == sorted(dates)


# --- rsi_signal ---

def test_rsi_signal_overbought():
    assert rsi_signal(75.0) == "Overbought"


def test_rsi_signal_oversold():
    assert rsi_signal(25.0) == "Oversold"


def test_rsi_signal_neutral():
    assert rsi_signal(55.0) == "Neutral"


def test_rsi_signal_none():
    assert rsi_signal(None) == "N/A"


# --- fmt_volume ---

def test_fmt_volume_millions():
    assert fmt_volume(2_500_000.0) == "2.5M"


def test_fmt_volume_thousands():
    assert fmt_volume(750_000.0) == "750.0K"


def test_fmt_volume_none():
    assert fmt_volume(None) == "N/A"
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
pytest tests/dashboard/test_app.py -v
```

Expected: `ModuleNotFoundError: No module named 'dashboard.app'`

- [ ] **Step 3: Implement dashboard/app.py (query functions only)**

`dashboard/app.py`:
```python
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.utils import get_connection as _get_conn


@st.cache_resource
def _get_db_connection():
    return _get_conn()


def load_summary(conn, ticker: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM gold.summary WHERE ticker = ?", [ticker]
    ).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def load_prices(conn, ticker: str, days: int) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    return conn.execute(
        """SELECT * FROM silver.prices
           WHERE ticker = ? AND date >= ?
           ORDER BY date""",
        [ticker, cutoff],
    ).df()


def rsi_signal(rsi) -> str:
    if pd.isna(rsi):
        return "N/A"
    if rsi > 70:
        return "Overbought"
    if rsi < 30:
        return "Oversold"
    return "Neutral"


def fmt_volume(v) -> str:
    if pd.isna(v):
        return "N/A"
    v = float(v)
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(int(v))


if __name__ == "__main__":
    pass  # main() added in Task 4
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/dashboard/test_app.py -v
```

Expected: `15 passed`

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py tests/dashboard/__init__.py tests/dashboard/test_app.py
git commit -m "feat: add dashboard query functions and helpers"
```

---

## Task 3: Chart builder functions

**Files:**
- Modify: `dashboard/app.py` (add four `fig_*` functions before the `if __name__` guard)

- [ ] **Step 1: Add chart builder functions to dashboard/app.py**

Insert the four functions below `fmt_volume` and above the `if __name__ == "__main__": pass` line:

```python
def fig_candlestick(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC",
    ))
    for col, color, name in [
        ("ma_7", "#f59e0b", "MA7"),
        ("ma_21", "#10b981", "MA21"),
        ("ma_50", "#6366f1", "MA50"),
    ]:
        valid = df[["date", col]].dropna()
        fig.add_trace(go.Scatter(
            x=valid["date"], y=valid[col],
            name=name, line=dict(color=color, width=1.5),
        ))
    fig.update_layout(xaxis_rangeslider_visible=False, height=400)
    return fig


def fig_volume(df: pd.DataFrame) -> go.Figure:
    colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(df["close"], df["open"])
    ]
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["volume"], marker_color=colors, name="Volume",
    ))
    fig.update_layout(height=200, showlegend=False)
    return fig


def fig_rsi(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "rsi_14"]].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["rsi_14"],
        name="RSI", line=dict(color="#6366f1"),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444",
                  annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#22c55e",
                  annotation_text="Oversold (30)")
    fig.update_layout(height=300, yaxis=dict(range=[0, 100]), title="RSI (14)")
    return fig


def fig_macd(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "macd", "macd_signal", "macd_hist"]].dropna()
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in valid["macd_hist"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valid["date"], y=valid["macd_hist"],
        marker_color=colors, name="Histogram",
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd"],
        name="MACD", line=dict(color="#6366f1"),
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd_signal"],
        name="Signal", line=dict(color="#f59e0b"),
    ))
    fig.update_layout(height=300, title="MACD (12/26/9)")
    return fig
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
pytest tests/dashboard/test_app.py -v
```

Expected: `15 passed`

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: add plotly chart builders for dashboard tabs"
```

---

## Task 4: Wire up Streamlit main() + smoke test

**Files:**
- Modify: `dashboard/app.py` (replace `if __name__ == "__main__": pass` with full `main()`)

- [ ] **Step 1: Replace the placeholder guard with the full main()**

Replace:
```python
if __name__ == "__main__":
    pass  # main() added in Task 4
```

With:
```python
def main() -> None:
    st.set_page_config(page_title="Financial Intelligence Dashboard", layout="wide")
    st.title("Financial Intelligence Dashboard")

    conn = _get_db_connection()

    col1, col2 = st.columns([1, 3])
    with col1:
        ticker = st.selectbox("Ticker", ["AAPL", "MSFT", "NVDA", "BTC-USD"])
    with col2:
        time_options = {"30d": 30, "90d": 90, "180d": 180, "1Y": 365}
        selected = st.radio("Time Range", list(time_options.keys()), horizontal=True)
        days = time_options[selected]

    try:
        df = load_prices(conn, ticker, days)
        summary = load_summary(conn, ticker)
    except Exception:
        st.warning("No data found. Run `python pipeline/run.py` first.")
        st.stop()
        return

    if df.empty and summary is None:
        st.warning("No data found. Run `python pipeline/run.py` first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Overview", "Price & Volume", "Technical Indicators"])

    with tab1:
        if summary is None:
            st.info("No summary data available for this ticker.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Last Close", f"${summary['last_close']:.2f}")
            c2.metric("1-day Change",
                      f"{summary['pct_change_1d']:.2f}%"
                      if pd.notna(summary["pct_change_1d"]) else "N/A")
            c3.metric("7-day Change",
                      f"{summary['pct_change_7d']:.2f}%"
                      if pd.notna(summary["pct_change_7d"]) else "N/A")
            c4.metric("30-day Change",
                      f"{summary['pct_change_30d']:.2f}%"
                      if pd.notna(summary["pct_change_30d"]) else "N/A")
            c5, c6 = st.columns(2)
            c5.metric("Avg Volume (30d)", fmt_volume(summary["avg_volume_30d"]))
            rsi_val = summary["current_rsi"]
            c6.metric(
                "RSI",
                f"{rsi_val:.1f} — {rsi_signal(rsi_val)}"
                if pd.notna(rsi_val) else "N/A",
            )

    with tab2:
        if df.empty:
            st.info("No data available for this period.")
        else:
            st.plotly_chart(fig_candlestick(df), use_container_width=True)
            st.plotly_chart(fig_volume(df), use_container_width=True)

    with tab3:
        if df.empty:
            st.info("No data available for this period.")
        else:
            st.plotly_chart(fig_rsi(df), use_container_width=True)
            st.plotly_chart(fig_macd(df), use_container_width=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: `40 passed` (25 pipeline + 15 dashboard)

- [ ] **Step 3: Populate the database (if not already done)**

```bash
python pipeline/run.py
```

Expected: log lines showing ingested rows for AAPL, MSFT, NVDA, BTC-USD. Skip if `data/financial.duckdb` already contains data.

- [ ] **Step 4: Smoke test the dashboard**

```bash
streamlit run dashboard/app.py
```

Expected: browser opens at `http://localhost:8501`. Verify:
- Ticker selectbox shows AAPL / MSFT / NVDA / BTC-USD
- Time range radio (30d / 90d / 180d / 1Y) switches work
- Overview tab shows 6 metric cards with real values
- Price & Volume tab shows candlestick + MA lines + volume bars
- Technical Indicators tab shows RSI (with 30/70 reference lines) and MACD

Stop the server with `Ctrl+C`.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: add streamlit dashboard with overview, price, and indicator tabs"
```

---

## Task 5: Push to GitHub

- [ ] **Step 1: Run full test suite one final time**

```bash
pytest tests/ -v
```

Expected: `40 passed`

- [ ] **Step 2: Push**

```bash
git push
```

Expected: branch pushed to `git@github.com:tutorres/Financial-Intelligence-Dashboard.git`
