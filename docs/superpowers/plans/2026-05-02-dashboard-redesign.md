# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the torres.dev design system to the Financial Intelligence Dashboard — new typography (Geist Sans + Geist Mono), updated color tokens, and a rebuilt landing page HTML — without changing any functionality.

**Architecture:** Pure visual change across two files. `style.py` is fully replaced with new CSS that imports Geist fonts and updates all Streamlit component overrides. `app.py` gets its landing HTML helper functions and `build_landing_html` rebuilt, plus a one-line font swap in each `fig_*` chart function. `1_Dashboard.py` is untouched — it inherits everything from `style.py` automatically.

**Tech Stack:** Streamlit CSS injection via `st.markdown(unsafe_allow_html=True)`, Google Fonts CDN, Plotly `update_layout`, pytest

---

## File Map

| File | Action | What changes |
|---|---|---|
| `tests/dashboard/test_app.py` | Modify line 159–163 | Rename test; expect `#8d8d8d` not `#ff4d4d` for negative stat card |
| `dashboard/style.py` | Full replacement | Geist font import, updated CSS overrides for all Streamlit components |
| `dashboard/app.py` | Modify | `_stat_card_html`, `_pipeline_step_html`, `_tech_cell_html`, `build_landing_html` rebuilt; font string in `fig_*` functions updated |

---

## Task 1: Update failing test for negative stat card color

**Files:**
- Modify: `tests/dashboard/test_app.py:159–163`

The current test asserts `#ff4d4d` (red) for negative changes. The redesign uses `#8d8d8d` (muted gray) — no red for down states. Update the test first so it fails against existing code; implementing the change in Task 3 will make it pass.

- [ ] **Step 1: Update the test**

Replace lines 159–163 in `tests/dashboard/test_app.py`:

```python
# OLD (remove):
def test_stat_card_html_down_shows_red_and_down_arrow():
    html = _stat_card_html("MSFT", 415.20, -0.42)
    assert "#ff4d4d" in html
    assert "▼" in html
    assert "415.20" in html

# NEW (replace with):
def test_stat_card_html_down_shows_muted_and_down_arrow():
    html = _stat_card_html("MSFT", 415.20, -0.42)
    assert "#8d8d8d" in html
    assert "#ff4d4d" not in html
    assert "▼" in html
    assert "415.20" in html
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/dashboard/test_app.py::test_stat_card_html_down_shows_muted_and_down_arrow -v
```

Expected: `FAILED` — current `_stat_card_html` still emits `#ff4d4d`, and the new `assert "#ff4d4d" not in html` will catch it.

- [ ] **Step 3: Commit the failing test**

```
git add tests/dashboard/test_app.py
git commit -m "test: update stat card test — expect muted gray for negative change, not red"
```

---

## Task 2: Rebuild `style.py`

**Files:**
- Modify: `dashboard/style.py` (full replacement)

Replaces the entire file. Adds a Google Fonts `@import` for Geist, updates all color values from `#94a3b8` → `#8d8d8d`, updates every font reference from `'Courier New', monospace` → `'Geist', sans-serif` (prose) or `'Geist Mono', monospace` (labels), and adds `border-radius: 6px` + `box-shadow` to metric containers. The two-function split (`inject_global_css` / `inject_dashboard_css`) is preserved so all existing tests continue to pass.

- [ ] **Step 1: Replace `dashboard/style.py` entirely**

```python
# dashboard/style.py

def inject_global_css() -> str:
    return """\
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600;700&display=swap');
.stApp,[data-testid="stAppViewContainer"]{background-color:#0d0d0d!important}
.main,.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{background-color:#0d0d0d!important;padding:0!important;max-width:100%!important}
section[data-testid="stMain"]>div:first-child{padding:0!important}
[data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"]{gap:0!important;padding:0!important}
[data-testid="stMarkdownContainer"]>div{width:100%!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background-color:#141414!important;border-right:1px solid #252525!important}
[data-testid="stSidebar"] *{font-family:'Geist Mono',monospace!important;color:#8d8d8d!important}
[data-testid="stSidebarNavLink"]{color:#8d8d8d!important}
[data-testid="stSidebarNavLink"][aria-current="page"]{color:#00ff88!important;border-left:2px solid #00ff88!important}
body,p,span{font-family:'Geist',sans-serif!important}
</style>"""


def inject_dashboard_css() -> str:
    return """\
<style>
[data-testid="metric-container"]{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;padding:1rem!important;box-shadow:0 1px 4px rgba(0,0,0,.35)!important}
[data-testid="stMetricLabel"]{color:#8d8d8d!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important;font-family:'Geist Mono',monospace!important}
[data-testid="stMetricValue"]{color:#fcfcfc!important;font-size:24px!important;font-weight:700!important;font-family:'Geist',sans-serif!important}
[data-testid="stMetricDelta"]{font-family:'Geist',sans-serif!important}
.stTabs [data-baseweb="tab-list"]{background-color:#141414!important;border-bottom:1px solid #252525!important;gap:0!important}
.stTabs [data-baseweb="tab"]{color:#8d8d8d!important;font-family:'Geist',sans-serif!important;font-size:13px!important;padding:10px 22px!important}
.stTabs [aria-selected="true"]{color:#00ff88!important;border-bottom:2px solid #00ff88!important;background:transparent!important}
.stTabs [data-baseweb="tab-panel"]{background-color:#0d0d0d!important;padding-top:1.5rem!important}
[data-testid="stSelectbox"]>div>div{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;color:#fcfcfc!important;font-family:'Geist Mono',monospace!important}
.stRadio>label,.stSelectbox>label{color:#8d8d8d!important;font-family:'Geist Mono',monospace!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#8d8d8d!important;font-size:12px!important;font-family:'Geist Mono',monospace!important}
.stCaption{color:#8d8d8d!important;font-family:'Geist',sans-serif!important;font-size:12px!important}
[data-testid="stAlert"]{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;color:#8d8d8d!important}
h1,h2,h3{color:#fcfcfc!important;font-family:'Geist',sans-serif!important}
.stMarkdown p{color:#fcfcfc!important;font-family:'Geist',sans-serif!important}
</style>"""
```

- [ ] **Step 2: Run `test_style.py` — all must pass**

```
pytest tests/dashboard/test_style.py -v
```

Expected: all 8 tests `PASSED`. The tests check for `#0d0d0d`, `#00ff88`, `#141414`, `metric-container`, `tab`, `stSidebar` separation — all present in the new CSS.

- [ ] **Step 3: Commit**

```
git add dashboard/style.py
git commit -m "feat: rebuild style.py — Geist fonts, updated color tokens, 6px radius on metric cards"
```

---

## Task 3: Rebuild landing page HTML functions in `app.py`

**Files:**
- Modify: `dashboard/app.py` (functions `_stat_card_html`, `_pipeline_step_html`, `_tech_cell_html`, `build_landing_html`)

Replaces the four HTML-generating functions. Typography switches to Geist Sans (prose) + Geist Mono (labels/badges). Negative stat cards drop `#ff4d4d` — down changes use `#8d8d8d` (muted) and a neutral border. Pipeline arrows change from green to `#8d8d8d`. Cards gain `border-radius:6px` and a subtle `box-shadow`. Section labels, nav, footer, hero, and all other structural elements are updated to match the approved design.

- [ ] **Step 1: Replace `_stat_card_html`**

Find and replace the entire `_stat_card_html` function (lines 166–192 in the original):

```python
def _stat_card_html(ticker: str, price, change) -> str:
    if change is None:
        border, fg, arrow = "#252525", "#8d8d8d", "—"
    elif change >= 0:
        border, fg, arrow = "#00ff88", "#00ff88", "▲"
    else:
        border, fg, arrow = "#252525", "#8d8d8d", "▼"
    price_str = f"${price:,.2f}" if price is not None else "—"
    change_str = f"{arrow} {abs(change):.2f}%" if change is not None else "—"
    bar_color = "#00ff88" if (change is not None and change >= 0) else "#252525"
    bars_html = "".join(
        f'<div style="flex:1;height:{h};background:{bar_color};border-radius:1px"></div>'
        for h in ["40%", "65%", "50%", "80%", "70%", "100%"]
    )
    return (
        f'<div style="background:#141414;border:1px solid #252525;border-left:3px solid {border};'
        f'border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.4);'
        f'padding:14px 18px;display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">'
        f'<div><div style="font-family:\'Geist Mono\',monospace;font-size:10px;color:#8d8d8d;'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">{ticker}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:20px;color:#fcfcfc;font-weight:700">{price_str}</div></div>'
        f'<div style="width:56px;height:28px;display:flex;align-items:flex-end;gap:2px">{bars_html}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:13px;font-weight:600;color:{fg}">{change_str}</div></div>'
    )
```

- [ ] **Step 2: Replace `_pipeline_step_html`**

Find and replace the entire `_pipeline_step_html` function:

```python
def _pipeline_step_html(label: str, name: str, desc: str, highlight: bool = False) -> str:
    left_border = "border-left:3px solid #00ff88;" if highlight else ""
    name_color = "#00ff88" if highlight else "#fcfcfc"
    return (
        f'<div style="background:#141414;border:1px solid #252525;{left_border}'
        f'border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.3);padding:20px 22px;flex:1">'
        f'<div style="font-family:\'Geist Mono\',monospace;font-size:9px;color:#8d8d8d;'
        f'letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">{label}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:16px;color:{name_color};'
        f'font-weight:600;margin-bottom:6px">{name}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:12px;color:#8d8d8d;line-height:1.6">{desc}</div></div>'
    )
```

- [ ] **Step 3: Replace `_tech_cell_html`**

Find and replace the entire `_tech_cell_html` function:

```python
def _tech_cell_html(layer: str, name: str, desc: str) -> str:
    return (
        f'<div style="background:#141414;padding:24px 26px">'
        f'<div style="font-family:\'Geist Mono\',monospace;font-size:9px;color:#00ff88;'
        f'letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">{layer}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:15px;color:#fcfcfc;'
        f'font-weight:600;margin-bottom:6px">{name}</div>'
        f'<div style="font-family:\'Geist\',sans-serif;font-size:12px;color:#8d8d8d;line-height:1.6">{desc}</div></div>'
    )
```

- [ ] **Step 4: Replace `build_landing_html`**

Find and replace the entire `build_landing_html` function:

```python
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
        '<span style="color:#8d8d8d;font-size:18px;display:flex;align-items:center;'
        'padding:0 12px;flex-shrink:0">→</span>'
    )
    pipeline = arrow.join([
        _pipeline_step_html("Layer 01", "Bronze", "Raw OHLCV ingestion via yfinance. Stored with ingestion timestamp. No transformations."),
        _pipeline_step_html("Layer 02", "Silver", "RSI, MACD, moving averages (7/21/50d), volatility, deduplication, null handling."),
        _pipeline_step_html("Layer 03", "Gold", "Per-ticker aggregated stats. Normalized feature sets ready for LSTM input."),
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
        f'<div style="background:#141414;border:1px solid #252525;border-radius:6px;'
        f'padding:14px 18px;font-family:\'Geist Mono\',monospace;font-size:13px;'
        f'color:#fcfcfc;letter-spacing:1px;text-align:center">{t}</div>'
        for t in ["AAPL", "MSFT", "GOOGL", "NVDA", "PETR4.SA", "VALE3.SA", "BTC-USD", "ETH-USD"]
    )
    return f"""
<div style="font-family:'Geist',sans-serif;background:#0d0d0d;color:#fcfcfc;width:100%;margin:0;padding:0;box-sizing:border-box">
  <nav style="border-bottom:1px solid #252525;padding:16px 48px;display:flex;align-items:center;justify-content:space-between">
    <span style="font-family:'Geist Mono',monospace;color:#00ff88;font-size:14px;font-weight:600;letter-spacing:2px">FID_</span>
    <div style="display:flex;gap:32px">
      <a href="#pipeline" style="font-family:'Geist',sans-serif;color:#8d8d8d;font-size:13px;text-decoration:none">Pipeline</a>
      <a href="#stack" style="font-family:'Geist',sans-serif;color:#8d8d8d;font-size:13px;text-decoration:none">Stack</a>
      <a href="#assets" style="font-family:'Geist',sans-serif;color:#8d8d8d;font-size:13px;text-decoration:none">Assets</a>
    </div>
  </nav>
  <div style="display:flex;align-items:flex-start;gap:64px;padding:72px 48px 64px;border-bottom:1px solid #252525">
    <div style="flex:1.1">
      <div style="font-family:'Geist Mono',monospace;color:#8d8d8d;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px">~/<span style="color:#00ff88">financial-intelligence-dashboard</span></div>
      <div style="font-family:'Geist',sans-serif;font-size:44px;font-weight:700;line-height:1.1;color:#fcfcfc;margin-bottom:24px;letter-spacing:-0.5px">Financial<br>Intelligence<br><span style="color:#00ff88">Dashboard</span></div>
      <div style="margin-bottom:36px">
        <div style="font-size:13px;color:#8d8d8d;margin-bottom:8px;line-height:1.5"><span style="color:#00ff88">▸</span> Bronze → Silver → Gold <span style="font-family:'Geist Mono',monospace;background:#141414;border:1px solid #252525;padding:2px 7px;border-radius:4px;font-size:10px;color:#8d8d8d;margin-left:4px">DuckDB</span></div>
        <div style="font-size:13px;color:#8d8d8d;margin-bottom:8px;line-height:1.5"><span style="color:#00ff88">▸</span> RSI · MACD · MA 7/21/50 <span style="font-family:'Geist Mono',monospace;background:#141414;border:1px solid #252525;padding:2px 7px;border-radius:4px;font-size:10px;color:#8d8d8d;margin-left:4px">pandas</span></div>
        <div style="font-size:13px;color:#8d8d8d;margin-bottom:8px;line-height:1.5"><span style="color:#00ff88">▸</span> LSTM trend classifier <span style="font-family:'Geist Mono',monospace;background:#141414;border:1px solid #252525;padding:2px 7px;border-radius:4px;font-size:10px;color:#8d8d8d;margin-left:4px">PyTorch</span></div>
        <div style="font-size:13px;color:#8d8d8d;line-height:1.5"><span style="color:#00ff88">▸</span> Natural language queries <span style="font-family:'Geist Mono',monospace;background:#141414;border:1px solid #252525;padding:2px 7px;border-radius:4px;font-size:10px;color:#8d8d8d;margin-left:4px">Groq LLM</span></div>
      </div>
      <a href="/Dashboard" target="_self" style="display:inline-flex;align-items:center;background:#00ff88;color:#0d0d0d;font-family:'Geist Mono',monospace;font-size:13px;font-weight:700;padding:12px 24px;border-radius:6px;letter-spacing:0.5px;text-decoration:none">$ streamlit run &#9608;</a>
    </div>
    <div style="flex:1">
      <div style="font-family:'Geist Mono',monospace;font-size:10px;color:#8d8d8d;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px">live market snapshot</div>
      {cards}
    </div>
  </div>
  <div id="pipeline" style="padding:64px 48px;border-bottom:1px solid #252525">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// data pipeline</div>
    <div style="display:flex;align-items:stretch">{pipeline}</div>
  </div>
  <div id="stack" style="padding:64px 48px;border-bottom:1px solid #252525">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// tech stack</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#252525;border:1px solid #252525;border-radius:6px;overflow:hidden">{tech}</div>
  </div>
  <div id="assets" style="padding:64px 48px;border-bottom:1px solid #252525">
    <div style="font-family:'Geist Mono',monospace;font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">// covered assets</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">{assets}</div>
  </div>
  <div style="padding:32px 48px;display:flex;justify-content:space-between;align-items:center">
    <span style="font-family:'Geist',sans-serif;font-size:13px;color:#8d8d8d">Arthur Torres · Computer Engineering</span>
    <a href="https://github.com/tutorres/Financial-Intelligence-Dashboard" style="font-family:'Geist Mono',monospace;font-size:11px;color:#8d8d8d;text-decoration:none;letter-spacing:1px">GitHub</a>
  </div>
</div>
"""
```

- [ ] **Step 5: Run full `test_app.py` — all must pass**

```
pytest tests/dashboard/test_app.py -v
```

Expected: all tests `PASSED`, including `test_stat_card_html_down_shows_muted_and_down_arrow` which now passes because `_stat_card_html` no longer emits `#ff4d4d`.

- [ ] **Step 6: Commit**

```
git add dashboard/app.py
git commit -m "feat: rebuild landing HTML — Geist fonts, muted negative states, 6px radius cards"
```

---

## Task 4: Update chart font strings in `app.py`

**Files:**
- Modify: `dashboard/app.py` — `fig_candlestick`, `fig_volume`, `fig_rsi`, `fig_macd`

Each `fig_*` function calls `fig.update_layout(font=dict(..., family="'Courier New', monospace"))`. Change the family string to `'Geist Mono', monospace` in all four. Chart data colors (`#f59e0b`, `#10b981`, `#6366f1`, `#22c55e`, `#ef4444`) are not changed.

- [ ] **Step 1: Update font family in all four chart functions**

In `fig_candlestick` (around line 83):
```python
# Before:
font=dict(color="#f8fafc", family="'Courier New', monospace"),
# After:
font=dict(color="#f8fafc", family="'Geist Mono', monospace"),
```

In `fig_volume` (around line 103):
```python
# Before:
font=dict(color="#f8fafc", family="'Courier New', monospace"),
# After:
font=dict(color="#f8fafc", family="'Geist Mono', monospace"),
```

In `fig_rsi` (around line 126):
```python
# Before:
font=dict(color="#f8fafc", family="'Courier New', monospace"),
# After:
font=dict(color="#f8fafc", family="'Geist Mono', monospace"),
```

In `fig_macd` (around line 154):
```python
# Before:
font=dict(color="#f8fafc", family="'Courier New', monospace"),
# After:
font=dict(color="#f8fafc", family="'Geist Mono', monospace"),
```

- [ ] **Step 2: Run `test_charts.py` — all must pass**

```
pytest tests/dashboard/test_charts.py -v
```

Expected: all 12 tests `PASSED`. Chart tests don't check font values — only trace types, colors, and layout background colors, which are all unchanged.

- [ ] **Step 3: Run full test suite — zero regressions**

```
pytest tests/ -v
```

Expected: all tests `PASSED`.

- [ ] **Step 4: Commit**

```
git add dashboard/app.py
git commit -m "feat: update chart font to Geist Mono across all fig_ functions"
```
