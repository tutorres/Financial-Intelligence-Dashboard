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
        FROM gold.prices
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


def apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0a0a0a",
        font=dict(family="Geist, DM Sans, sans-serif", color="#737373", size=12),
        xaxis=dict(gridcolor="#1a1a1a", linecolor="#1a1a1a", tickfont=dict(color="#525252", size=11), zeroline=False),
        yaxis=dict(gridcolor="#1a1a1a", linecolor="#1a1a1a", tickfont=dict(color="#525252", size=11), zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color="#737373", size=11)),
        margin=dict(l=0, r=0, t=32, b=0),
    )
    return fig


def fig_candlestick(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC",
        increasing=dict(line=dict(color="#4a9463"), fillcolor="#4a9463"),
        decreasing=dict(line=dict(color="#8b3a3a"), fillcolor="#8b3a3a"),
    ))
    for col, color, name in [
        ("ma_7", "#e5e5e5", "MA7"),
        ("ma_21", "#737373", "MA21"),
        ("ma_50", "#525252", "MA50"),
    ]:
        valid = df[["date", col]].dropna()
        if valid.empty:
            continue
        fig.add_trace(go.Scatter(
            x=valid["date"], y=valid[col],
            name=name, line=dict(color=color, width=1.5),
        ))
    fig.update_layout(xaxis_rangeslider_visible=False, height=800)
    return apply_theme(fig)


def fig_volume(df: pd.DataFrame) -> go.Figure:
    colors = [
        "#4a9463" if c >= o else "#8b3a3a"
        for c, o in zip(df["close"], df["open"])
    ]
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["volume"], marker_color=colors, name="Volume",
    ))
    fig.update_layout(height=480, showlegend=False)
    return apply_theme(fig)


def fig_rsi(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "rsi_14"]].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["rsi_14"],
        name="RSI", line=dict(color="#737373"),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="#525252",
                  annotation_text="Overbought (70)",
                  annotation_font=dict(color="#525252"))
    fig.add_hline(y=30, line_dash="dash", line_color="#525252",
                  annotation_text="Oversold (30)",
                  annotation_font=dict(color="#525252"))
    fig.update_layout(
        height=600,
        yaxis=dict(range=[0, 100]),
        title=dict(text="RSI (14)", font=dict(color="#737373")),
    )
    return apply_theme(fig)


def fig_macd(df: pd.DataFrame) -> go.Figure:
    valid = df[["date", "macd", "macd_signal", "macd_hist"]].dropna()
    colors = ["#4a9463" if v >= 0 else "#8b3a3a" for v in valid["macd_hist"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valid["date"], y=valid["macd_hist"],
        marker_color=colors, name="Histogram",
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd"],
        name="MACD", line=dict(color="#e5e5e5"),
    ))
    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid["macd_signal"],
        name="Signal", line=dict(color="#737373"),
    ))
    fig.update_layout(
        height=600,
        title=dict(text="MACD (12/26/9)", font=dict(color="#737373")),
    )
    return apply_theme(fig)


def _stat_card_html(ticker: str, price, change) -> str:
    if change is None:
        left_border, fg, arrow = "#1a1a1a", "#525252", "—"
    elif change >= 0:
        left_border, fg, arrow = "#525252", "#737373", "▲"
    else:
        left_border, fg, arrow = "#1a1a1a", "#525252", "▼"
    price_str = f"${price:,.2f}" if price is not None else "—"
    change_str = f"{arrow} {abs(change):.2f}%" if change is not None else "—"
    bars_html = "".join(
        f'<div style="flex:1;height:{h};background:#525252;border-radius:1px"></div>'
        for h in ["40%", "65%", "50%", "80%", "70%", "100%"]
    )
    return (
        f'<div style="background:#111111;border:1px solid #1a1a1a;border-left:3px solid {left_border};'
        f'border-radius:6px;'
        f'padding:14px 18px;display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">'
        f'<div><div style="font-family:\'Geist Mono\',monospace;font-size:10px;color:#737373;'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">{ticker}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:20px;color:#e5e5e5;font-weight:600">{price_str}</div></div>'
        f'<div style="width:56px;height:28px;display:flex;align-items:flex-end;gap:2px">{bars_html}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:13px;font-weight:500;color:{fg}">{change_str}</div></div>'
    )


def _pipeline_step_html(label: str, name: str, desc: str, highlight: bool = False) -> str:
    left_border = "border-left:3px solid #525252;" if highlight else ""
    return (
        f'<div style="background:#111111;border:1px solid #1a1a1a;{left_border}'
        f'border-radius:6px;padding:20px 22px;flex:1">'
        f'<div style="font-family:\'Geist Mono\',monospace;font-size:9px;color:#525252;'
        f'letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">{label}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:16px;color:#e5e5e5;'
        f'font-weight:600;margin-bottom:6px">{name}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:12px;color:#737373;line-height:1.6">{desc}</div></div>'
    )


def _tech_cell_html(layer: str, name: str, desc: str) -> str:
    return (
        f'<div style="background:#111111;padding:24px 26px">'
        f'<div style="font-family:\'Geist Mono\',monospace;font-size:9px;color:#525252;'
        f'letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">{layer}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:15px;color:#e5e5e5;'
        f'font-weight:600;margin-bottom:6px">{name}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:12px;color:#737373;line-height:1.6">{desc}</div></div>'
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
    arrow = (
        '<span style="color:#525252;font-size:18px;display:flex;align-items:center;'
        'padding:0 12px;flex-shrink:0">→</span>'
    )
    pipeline = arrow.join([
        _pipeline_step_html("Layer 01", "Bronze", "Raw OHLCV ingestion via yfinance. Stored with ingestion timestamp. No transformations."),
        _pipeline_step_html("Layer 02", "Silver", "Null handling and deduplication. OHLCV-only output."),
        _pipeline_step_html("Layer 03", "Gold", "RSI, MACD, moving averages (7/21/50d), volatility. Per-ticker aggregated stats ready for LSTM input."),
        _pipeline_step_html("Output", "Dashboard", "Streamlit + Plotly charts. LSTM predictions. Groq natural language interface.", highlight=True),
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
        f'<div style="background:#111111;border:1px solid #1a1a1a;border-radius:6px;'
        f'padding:14px 18px;font-family:\'Geist Mono\',monospace;font-size:13px;'
        f'color:#e5e5e5;letter-spacing:1px;text-align:center">{t}</div>'
        for t in ["AAPL", "MSFT", "GOOGL", "NVDA", "PETR4.SA", "VALE3.SA", "BTC-USD", "ETH-USD"]
    )
    return f"""
<div style="font-family:'Geist',sans-serif;background:#0a0a0a;color:#e5e5e5;width:100%;margin:0;padding:0;box-sizing:border-box">
  <nav style="border-bottom:1px solid #1a1a1a;padding:16px 48px;display:flex;align-items:center;justify-content:space-between">
    <span style="font-family:'Geist Mono',monospace;color:#e5e5e5;font-size:14px;font-weight:600;letter-spacing:2px">FID_</span>
    <div style="display:flex;gap:32px">
      <a href="#pipeline" style="font-family:'Geist',sans-serif;color:#737373;font-size:13px;text-decoration:none">Pipeline</a>
      <a href="#stack" style="font-family:'Geist',sans-serif;color:#737373;font-size:13px;text-decoration:none">Stack</a>
      <a href="#assets" style="font-family:'Geist',sans-serif;color:#737373;font-size:13px;text-decoration:none">Assets</a>
    </div>
  </nav>
  <div style="display:flex;align-items:flex-start;gap:64px;padding:72px 48px 64px;border-bottom:1px solid #1a1a1a">
    <div style="flex:1.1">
      <div style="font-family:'Geist Mono',monospace;color:#737373;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px">~/financial-intelligence-dashboard</div>
      <div style="font-family:'Geist',sans-serif;font-size:44px;font-weight:700;line-height:1.1;color:#e5e5e5;margin-bottom:24px;letter-spacing:-0.5px">Financial<br>Intelligence<br>Dashboard</div>
      <div style="margin-bottom:36px">
        <div style="font-size:13px;color:#737373;margin-bottom:8px;line-height:1.5">▸ Bronze → Silver → Gold <span style="font-family:'Geist Mono',monospace;background:#111111;border:1px solid #1a1a1a;padding:2px 7px;border-radius:4px;font-size:10px;color:#737373;margin-left:4px">DuckDB</span></div>
        <div style="font-size:13px;color:#737373;margin-bottom:8px;line-height:1.5">▸ RSI · MACD · MA 7/21/50 <span style="font-family:'Geist Mono',monospace;background:#111111;border:1px solid #1a1a1a;padding:2px 7px;border-radius:4px;font-size:10px;color:#737373;margin-left:4px">pandas</span></div>
        <div style="font-size:13px;color:#737373;margin-bottom:8px;line-height:1.5">▸ LSTM trend classifier <span style="font-family:'Geist Mono',monospace;background:#111111;border:1px solid #1a1a1a;padding:2px 7px;border-radius:4px;font-size:10px;color:#737373;margin-left:4px">PyTorch</span></div>
        <div style="font-size:13px;color:#737373;line-height:1.5">▸ Natural language queries <span style="font-family:'Geist Mono',monospace;background:#111111;border:1px solid #1a1a1a;padding:2px 7px;border-radius:4px;font-size:10px;color:#737373;margin-left:4px">Groq LLM</span></div>
      </div>
      <a href="/Dashboard" target="_self" style="display:inline-flex;align-items:center;background:#e5e5e5;color:#0a0a0a;font-family:'Geist Mono',monospace;font-size:13px;font-weight:700;padding:12px 24px;border-radius:6px;letter-spacing:0.5px;text-decoration:none;transition:opacity 0.2s">$ streamlit run &#9608;</a>
    </div>
    <div style="flex:1">
      <div style="font-family:'Geist Mono',monospace;font-size:10px;color:#525252;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px">live market snapshot</div>
      {cards}
    </div>
  </div>
  <div id="pipeline" style="padding:64px 48px;border-bottom:1px solid #1a1a1a">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#525252;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// data pipeline</div>
    <div style="display:flex;align-items:stretch">{pipeline}</div>
  </div>
  <div id="stack" style="padding:64px 48px;border-bottom:1px solid #1a1a1a">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#525252;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// tech stack</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#1a1a1a;border:1px solid #1a1a1a;border-radius:6px;overflow:hidden">{tech}</div>
  </div>
  <div id="assets" style="padding:64px 48px;border-bottom:1px solid #1a1a1a">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#525252;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// covered assets</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">{assets}</div>
  </div>
  <div style="padding:32px 48px;display:flex;justify-content:space-between;align-items:center">
    <span style="font-family:'Geist',sans-serif;font-size:13px;color:#737373">Arthur Torres · Computer Engineering</span>
    <a href="https://github.com/tutorres/Financial-Intelligence-Dashboard" style="font-family:'Geist Mono',monospace;font-size:11px;color:#737373;text-decoration:none;letter-spacing:1px">GitHub</a>
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


if __name__ == "__main__":
    main()
