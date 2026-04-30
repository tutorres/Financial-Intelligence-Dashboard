import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.utils import TICKERS, get_connection as _get_conn


@st.cache_resource
def _get_db_connection():
    return _get_conn()


def load_summary(conn, ticker: str) -> dict | None:
    row = conn.execute("""
        SELECT ticker, last_updated, last_close,
               pct_change_1d, pct_change_7d, pct_change_30d,
               avg_volume_30d, current_rsi
        FROM gold.summary WHERE ticker = ?
    """, [ticker]).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def load_prices(conn, ticker: str, days: int) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    return conn.execute("""
        SELECT ticker, date, open, high, low, close, volume,
               daily_return, ma_7, ma_21, ma_50, rsi_14,
               macd, macd_signal, macd_hist, volatility_21
        FROM silver.prices
        WHERE ticker = ? AND date >= ?
        ORDER BY date
    """, [ticker, cutoff]).df()


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
        if valid.empty:
            continue
        fig.add_trace(go.Scatter(
            x=valid["date"], y=valid[col],
            name=name, line=dict(color=color, width=1.5),
        ))
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=600,
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#141414",
        font=dict(color="#f8fafc", family="'Courier New', monospace"),
        xaxis=dict(gridcolor="#252525", linecolor="#252525"),
        yaxis=dict(gridcolor="#252525", linecolor="#252525"),
    )
    return fig


def fig_volume(df: pd.DataFrame) -> go.Figure:
    colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(df["close"], df["open"])
    ]
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["volume"], marker_color=colors, name="Volume",
    ))
    fig.update_layout(
        height=350,
        showlegend=False,
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#141414",
        font=dict(color="#f8fafc", family="'Courier New', monospace"),
        xaxis=dict(gridcolor="#252525", linecolor="#252525"),
        yaxis=dict(gridcolor="#252525", linecolor="#252525"),
    )
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
    fig.update_layout(
        height=450,
        yaxis=dict(range=[0, 100], gridcolor="#252525", linecolor="#252525"),
        title=dict(text="RSI (14)", font=dict(color="#f8fafc")),
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#141414",
        font=dict(color="#f8fafc", family="'Courier New', monospace"),
        xaxis=dict(gridcolor="#252525", linecolor="#252525"),
    )
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
    fig.update_layout(
        height=450,
        title=dict(text="MACD (12/26/9)", font=dict(color="#f8fafc")),
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#141414",
        font=dict(color="#f8fafc", family="'Courier New', monospace"),
        xaxis=dict(gridcolor="#252525", linecolor="#252525"),
        yaxis=dict(gridcolor="#252525", linecolor="#252525"),
    )
    return fig


def _stat_card_html(ticker: str, price, change) -> str:
    if change is None:
        border, fg, arrow = "#252525", "#94a3b8", "—"
    elif change >= 0:
        border, fg, arrow = "#00ff88", "#00ff88", "▲"
    else:
        border, fg, arrow = "#ff4d4d", "#ff4d4d", "▼"
    price_str = f"${price:,.2f}" if price is not None else "—"
    change_str = f"{arrow} {abs(change):.2f}%" if change is not None else "—"
    if change is None:
        bars = [("40%","#3a3a3a"),("65%","#3a3a3a"),("50%","#3a3a3a"),
                ("80%","#3a3a3a"),("70%","#3a3a3a"),("100%","#3a3a3a")]
    else:
        bars = [("40%","#ff4d4d"),("65%","#00ff88"),("50%","#00ff88"),
                ("80%","#00ff88"),("70%","#ff4d4d"),("100%","#00ff88")]
    bars_html = "".join(
        f'<div style="flex:1;height:{h};background:{c};border-radius:1px"></div>'
        for h, c in bars
    )
    return (
        f'<div style="background:#141414;border:1px solid #252525;border-left:3px solid {border};'
        f'padding:16px 20px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">'
        f'<div><div style="font-size:11px;color:#94a3b8;letter-spacing:1px;margin-bottom:4px">{ticker}</div>'
        f'<div style="font-size:22px;color:#f8fafc;font-weight:700">{price_str}</div></div>'
        f'<div style="width:64px;height:32px;display:flex;align-items:flex-end;gap:3px">{bars_html}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{fg}">{change_str}</div></div>'
    )


def _pipeline_step_html(label: str, name: str, desc: str, highlight: bool = False) -> str:
    border = "border-left:3px solid #00ff88;" if highlight else ""
    name_color = "#00ff88" if highlight else "#f8fafc"
    return (
        f'<div style="background:#141414;border:1px solid #252525;{border}padding:24px 28px;flex:1">'
        f'<div style="font-size:10px;color:#94a3b8;letter-spacing:2px;margin-bottom:10px">{label}</div>'
        f'<div style="font-size:18px;color:{name_color};font-weight:700;margin-bottom:8px">{name}</div>'
        f'<div style="font-size:12px;color:#94a3b8;line-height:1.7">{desc}</div></div>'
    )


def _tech_cell_html(layer: str, name: str, desc: str) -> str:
    return (
        f'<div style="background:#0d0d0d;padding:28px 32px">'
        f'<div style="font-size:10px;color:#00ff88;letter-spacing:2px;margin-bottom:10px;text-transform:uppercase">{layer}</div>'
        f'<div style="font-size:18px;color:#f8fafc;font-weight:700;margin-bottom:8px">{name}</div>'
        f'<div style="font-size:13px;color:#94a3b8;line-height:1.7">{desc}</div></div>'
    )


def build_landing_html(stats: list) -> str:
    placeholders = [
        {"ticker": "AAPL", "last_close": None, "pct_change_1d": None},
        {"ticker": "MSFT", "last_close": None, "pct_change_1d": None},
        {"ticker": "NVDA", "last_close": None, "pct_change_1d": None},
        {"ticker": "BTC-USD", "last_close": None, "pct_change_1d": None},
    ]
    display = stats[:4] if stats else placeholders
    cards = "".join(
        _stat_card_html(s["ticker"], s.get("last_close"), s.get("pct_change_1d"))
        for s in display
    )
    arrow = '<span style="color:#00ff88;font-size:22px;display:flex;align-items:center;padding:0 12px;flex-shrink:0">→</span>'
    pipeline = arrow.join([
        _pipeline_step_html("LAYER 01", "Bronze", "Raw OHLCV ingestion via yfinance. Stored with ingestion timestamp. No transformations."),
        _pipeline_step_html("LAYER 02", "Silver", "RSI, MACD, moving averages (7/21/50d), volatility, deduplication, null handling."),
        _pipeline_step_html("LAYER 03", "Gold", "Per-ticker aggregated stats. Normalized feature sets ready for LSTM input."),
        _pipeline_step_html("OUTPUT", "Dashboard", "Streamlit + Plotly charts. LSTM predictions. Groq natural language interface.", highlight=True),
    ])
    tech = "".join([
        _tech_cell_html("Data Ingestion", "yfinance + DuckDB", "Daily OHLCV for 8 assets. Columnar storage with Bronze / Silver / Gold warehouse pattern."),
        _tech_cell_html("Analytics", "pandas + numpy", "RSI (14d), MACD (12/26/9), MA 7/21/50, volatility (21d), daily returns."),
        _tech_cell_html("Machine Learning", "PyTorch LSTM", "30-day sequence classification. Predicts up / down / neutral trend direction."),
        _tech_cell_html("UI & Charts", "Streamlit + Plotly", "Candlestick, volume, RSI, MACD charts. Multi-page with landing page."),
        _tech_cell_html("LLM Interface", "Groq API", "Natural language queries over gold tables. llama3 and mixtral models."),
        _tech_cell_html("Deployment", "Streamlit Cloud", "Free tier. Auto-deploys from GitHub. Pipeline runs on cold start automatically."),
    ])
    assets = "".join(
        f'<div style="background:#141414;border:1px solid #252525;padding:16px 20px;font-size:14px;color:#f8fafc;letter-spacing:1.5px">{t}</div>'
        for t in ["AAPL", "MSFT", "GOOGL", "NVDA", "PETR4.SA", "VALE3.SA", "BTC-USD", "ETH-USD"]
    )
    return f"""
<div style="font-family:'Courier New',monospace;background:#0d0d0d;color:#f8fafc">
  <nav style="border-bottom:1px solid #252525;padding:18px 64px;display:flex;align-items:center;justify-content:space-between">
    <span style="color:#00ff88;font-size:16px;font-weight:700;letter-spacing:3px">FID_</span>
    <div style="display:flex;gap:40px">
      <a href="#pipeline" style="color:#94a3b8;font-size:12px;text-decoration:none;letter-spacing:1.5px">PIPELINE</a>
      <a href="#stack" style="color:#94a3b8;font-size:12px;text-decoration:none;letter-spacing:1.5px">STACK</a>
      <a href="#assets" style="color:#94a3b8;font-size:12px;text-decoration:none;letter-spacing:1.5px">ASSETS</a>
    </div>
  </nav>
  <div style="display:flex;align-items:center;gap:80px;padding:96px 64px 80px;border-bottom:1px solid #252525">
    <div style="flex:1.1">
      <div style="color:#94a3b8;font-size:13px;margin-bottom:20px">~/<span style="color:#00ff88">financial-intelligence-dashboard</span></div>
      <div style="color:#94a3b8;font-size:13px;margin-bottom:24px"><span style="color:#00ff88">$ </span>python pipeline/run.py --all-tickers</div>
      <div style="font-size:52px;font-weight:700;line-height:1.1;color:#f8fafc;margin-bottom:28px;letter-spacing:-1px">Financial<br>Intelligence<br><span style="color:#00ff88">Dashboard</span></div>
      <div style="margin-bottom:40px">
        <div style="font-size:13px;color:#94a3b8;margin-bottom:8px"><span style="color:#00ff88">▸</span> Bronze → Silver → Gold <span style="background:#141414;border:1px solid #252525;padding:1px 8px;border-radius:2px;font-size:11px;color:#94a3b8;margin-left:4px">DuckDB</span></div>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:8px"><span style="color:#00ff88">▸</span> RSI · MACD · MA 7/21/50 <span style="background:#141414;border:1px solid #252525;padding:1px 8px;border-radius:2px;font-size:11px;color:#94a3b8;margin-left:4px">pandas</span></div>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:8px"><span style="color:#00ff88">▸</span> LSTM trend classifier <span style="background:#141414;border:1px solid #252525;padding:1px 8px;border-radius:2px;font-size:11px;color:#94a3b8;margin-left:4px">PyTorch</span></div>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:8px"><span style="color:#00ff88">▸</span> Natural language queries <span style="background:#141414;border:1px solid #252525;padding:1px 8px;border-radius:2px;font-size:11px;color:#94a3b8;margin-left:4px">Groq LLM</span></div>
      </div>
    </div>
    <div style="flex:1">
      <div style="font-size:10px;color:#94a3b8;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px">live market snapshot</div>
      {cards}
    </div>
  </div>
  <div id="pipeline" style="padding:80px 64px;border-bottom:1px solid #252525">
    <div style="font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:32px">// data pipeline</div>
    <div style="display:flex;align-items:stretch">{pipeline}</div>
  </div>
  <div id="stack" style="padding:80px 64px;border-bottom:1px solid #252525">
    <div style="font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:32px">// tech stack</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#252525;border:1px solid #252525">{tech}</div>
  </div>
  <div id="assets" style="padding:80px 64px;border-bottom:1px solid #252525">
    <div style="font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:32px">// covered assets</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">{assets}</div>
  </div>
  <div style="padding:40px 64px;display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:13px;color:#94a3b8">Arthur Torres · Computer Engineering</span>
    <a href="https://github.com/tutorres/Financial-Intelligence-Dashboard" style="font-size:11px;color:#94a3b8;text-decoration:none;letter-spacing:1px">GitHub</a>
  </div>
</div>
"""


def main() -> None:
    st.set_page_config(
        page_title="Financial Intelligence Dashboard",
        page_icon="📈",
        layout="wide",
    )
    from dashboard.style import inject_global_css
    st.markdown(inject_global_css(), unsafe_allow_html=True)

    stats: list = []
    try:
        conn = _get_db_connection()
        df = conn.execute("""
            SELECT ticker, last_close, pct_change_1d FROM gold.summary
            WHERE ticker IN ('AAPL','MSFT','NVDA','BTC-USD')
            ORDER BY CASE ticker
                WHEN 'AAPL' THEN 1 WHEN 'MSFT' THEN 2
                WHEN 'NVDA' THEN 3 WHEN 'BTC-USD' THEN 4 END
        """).fetchdf()
        stats = df.to_dict("records")
    except Exception:
        pass

    st.markdown(build_landing_html(stats), unsafe_allow_html=True)
    st.page_link("pages/1_Dashboard.py", label="→ Open Dashboard", icon="🚀")


if __name__ == "__main__":
    main()
