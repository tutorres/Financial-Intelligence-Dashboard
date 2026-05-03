# Dashboard Redesign — Design Spec

**Date:** 2026-05-02  
**Scope:** Visual redesign only — no functionality changes  
**Reference:** torres.dev design system

---

## Summary

Apply the torres.dev design system to the Financial Intelligence Dashboard (Streamlit app). The redesign updates typography, color tokens, component styling, and the landing page HTML. No pipeline logic, ML code, chart data, or test files are touched.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Brand color | Keep `#00ff88` terminal green | FID's signature identity; torres.dev monochromatic base with one accent |
| Typography | Geist Sans (prose/UI) + Geist Mono (labels/code) | torres.dev spec; more readable than all-Courier-New |
| Background depth | `#0d0d0d` near-black | Retains the terminal depth the app has now |
| Card surfaces | `#141414` with `1px solid #252525` borders | Current style kept; `6px` radius and subtle shadow added |
| Chart colors | Unchanged | Chart data colors are exempt per torres.dev rules |

---

## Scope — Files Changed

**`dashboard/style.py`** — full replacement  
**`dashboard/app.py`** — landing HTML rebuilt + chart font strings updated  
**`dashboard/pages/1_Dashboard.py`** — no changes (inherits from `style.py`)

No other files change.

---

## Color Tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#0d0d0d` | Page background |
| `--surface` | `#141414` | Card / component surfaces |
| `--border` | `#252525` | All borders |
| `--fg` | `#fcfcfc` | Primary text |
| `--muted` | `#8d8d8d` | Secondary / label text |
| `--accent` | `#00ff88` | Active states, CTAs, positive values, highlights |

---

## Typography

Fonts loaded via `@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600;700&display=swap')` injected into Streamlit via `st.markdown(..., unsafe_allow_html=True)`.

| Role | Font | Applied to |
|---|---|---|
| Prose / headings | Geist Sans | `body`, `p`, `h1–h3`, metric values, captions, tab labels, descriptions |
| Technical labels | Geist Mono | Nav brand `FID_`, section labels, metric label text, selectbox, radio, badges, chart font, sidebar links |

---

## `style.py` — inject_global_css()

Injects:
1. `@import` for Geist fonts
2. CSS custom properties (`--bg`, `--surface`, `--border`, `--fg`, `--muted`, `--accent`)
3. Streamlit app background overrides (`#0d0d0d`)
4. Sidebar: Geist Mono, `#8d8d8d` text, `#00ff88` active nav link with left border
5. Body font: Geist Sans
6. Hides Streamlit default header/footer/main menu

## `style.py` — inject_dashboard_css()

Injects overrides for:

| Component | Changes |
|---|---|
| `[data-testid="metric-container"]` | `#141414` bg, `1px solid #252525` border, `border-radius: 6px`, `box-shadow: 0 1px 4px rgba(0,0,0,.35)` |
| `[data-testid="stMetricLabel"]` | Geist Mono, `10px`, uppercase, `#8d8d8d` |
| `[data-testid="stMetricValue"]` | Geist Sans, `24px`, `700`, `#fcfcfc` |
| `[data-testid="stMetricDelta"]` | Geist Sans |
| Tab list | `background: #141414`, `border-bottom: 1px solid #252525` |
| Tab item | Geist Sans, `#8d8d8d` |
| Active tab | `color: #00ff88`, `border-bottom: 2px solid #00ff88` |
| Tab panel | `background: #0d0d0d`, `padding-top: 1.5rem` |
| Selectbox | `#141414` bg, `1px solid #252525` border, `border-radius: 6px`, Geist Mono |
| Radio / selectbox labels | Geist Mono, `10px`, uppercase, `#8d8d8d` |
| Captions | Geist Sans, `#8d8d8d` |
| Alert/info/warning | `#141414` bg, `1px solid #252525` border, `border-radius: 6px`, `#8d8d8d` text |
| `h1–h3` | Geist Sans, `#fcfcfc` |
| `.stMarkdown p` | Geist Sans, `#fcfcfc` |

---

## Landing Page HTML (`app.py` — `build_landing_html`)

Full rebuild of the HTML string. Structure unchanged (same sections, same data). Visual changes:

- **Nav:** `FID_` in Geist Mono + green; links in Geist Sans; border-bottom `#252525`
- **Hero eyebrow:** Geist Mono, `11px`, `#8d8d8d`, uppercase, `letter-spacing: 3px`; `~/financial-intelligence-dashboard` with green path
- **Hero title:** Geist Sans, `44px`, `700`; "Dashboard" in `#00ff88`
- **Bullet list:** Geist Sans prose + Geist Mono inline badges (`#141414` bg, `1px solid #252525`, `4px` radius)
- **CTA button:** Geist Mono, `#00ff88` bg, `#0d0d0d` text, `6px` radius
- **Stat cards:** `#141414` bg, `1px solid #252525` border, `border-radius: 6px`, `box-shadow: 0 1px 4px rgba(0,0,0,.4)`. Positive cards: `border-left: 3px solid #00ff88`; negative cards: `border-left: 3px solid #252525` (neutral, no red). Ticker in Geist Mono; price in Geist Sans `700`; change in Geist Sans (`#00ff88` if positive, `#8d8d8d` if negative). Mini-bars: `#00ff88` for positive cards, `#252525` for negative cards — red is not used for down states anywhere
- **Section labels:** Geist Mono, `11px`, `#00ff88`, `letter-spacing: 3px`, `// prefix`
- **Pipeline steps:** `#141414` bg, `1px solid #252525`, `border-radius: 6px`, `box-shadow`. Layer label in Geist Mono `9px` `#8d8d8d`; name in Geist Sans `16px` `600`; desc in Geist Sans `12px` `#8d8d8d`. "Dashboard" step: `border-left: 3px solid #00ff88`, name in `#00ff88`. Arrows between steps: `#8d8d8d` (not green)
- **Tech grid:** 3-column grid, `1px` gaps on `#252525` bg. Cells `#141414`. Layer label in Geist Mono `#00ff88`; name in Geist Sans `15px` `600`; desc in Geist Sans `12px` `#8d8d8d`
- **Assets grid:** 4-column, `#141414` cards, `1px solid #252525`, `6px` radius, Geist Mono ticker text
- **Footer:** Geist Sans name; Geist Mono GitHub link

---

## Chart Font Update (`app.py` — `fig_*` functions)

All `font=dict(family="'Courier New', monospace")` → `font=dict(family="'Geist Mono', monospace")`.

Chart data colors (`#f59e0b`, `#10b981`, `#6366f1`, `#22c55e`, `#ef4444`) are **not changed**.

---

## What Does Not Change

- All pipeline logic (`pipeline/`)
- All ML code (`ml/`)
- All chat logic (`chat/`)
- All tests (`tests/`)
- Plotly chart structure and data colors
- `dashboard/pages/1_Dashboard.py` structure and logic
- `pipeline/utils.py`, `TICKERS`, `get_connection`
