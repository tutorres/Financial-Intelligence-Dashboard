# UI Redesign — Design Spec

## Goal

Redesign the Streamlit landing page and dashboard to use a clean minimal dark theme that looks professional and tech-forward to recruiters.

## Color System

```
--bg:      #0d0d0d   (page background)
--surface: #141414   (card/panel background)
--border:  #252525   (borders, dividers)
--white:   #f8fafc   (primary text, prices, titles)
--muted:   #94a3b8   (secondary text — slate-400, readable on dark)
--green:   #00ff88   (accent: up, active, CTA, section labels)
--red:     #ff4d4d   (accent: down, negative)
```

All text is either `--white` (primary) or `--muted` (secondary). No other gray values. Hierarchy is achieved through font size and weight, not color variation.

## Typography

- Font: `'Courier New', monospace` throughout (terminal aesthetic)
- Titles: bold, large, `--white`
- Labels/descriptions: `--muted`
- Accents/section markers: `--green`

## Landing Page (`dashboard/app.py`)

Injected via `st.markdown("<style>...", unsafe_allow_html=True)` + `st.markdown(html, unsafe_allow_html=True)`.

### Sections (top to bottom)

**Nav bar**
- Logo: `FID_` in green, monospace
- Links: Overview, Pipeline, Dashboard, GitHub — in `--muted`

**Hero** (two columns)
- Left: terminal path line → command line → large H1 (`Financial Intelligence Dashboard`, last word in green) → 4 stack lines with green arrow + muted tag chips → green CTA button styled as `$ streamlit run █`
- Right: "live market snapshot" label + 4 stat cards (AAPL, MSFT, NVDA, BTC-USD), each showing ticker, last close price, mini bar chart, % change. Green left border for up days, red for down.

**Pipeline section**
- Label: `// data pipeline` in green
- 4 boxes: Bronze → Silver → Gold → Dashboard, connected by `→` arrows in green
- Last box has green left border and green title

**Tech Stack section**
- Label: `// tech stack`
- 3×2 grid of cells separated by `--border` lines
- Each cell: green layer label, white tech name, muted description

**Covered Assets section**
- Label: `// covered assets`
- 4×2 grid of asset tags, white text, hover → green

**Footer**
- Left: "Arthur Torres · Computer Engineering" in `--muted`
- Right: GitHub, LinkedIn links

## Dashboard Page (`dashboard/pages/1_Dashboard.py`)

Apply matching dark CSS via injected `<style>` block. Key changes:
- Streamlit default white background → `--bg`
- Metric cards styled with `--surface` background, `--border` borders, green left accent on positive delta
- Chart background set to `#0d0d0d` via `plotly` layout template
- Tab styling: dark background, green active indicator
- Captions use `--muted` color

## Implementation Approach

Streamlit does not expose a full CSS framework, but accepts injected styles via:
```python
st.markdown("<style>css here</style>", unsafe_allow_html=True)
```

All custom styling goes through this mechanism. A shared `dashboard/style.py` module exposes:
- `inject_global_css()` — injects the color system and base overrides
- `inject_landing_css()` — landing-specific layout styles
- `inject_dashboard_css()` — dashboard-specific card and tab styles

Plotly figures updated with `fig.update_layout(paper_bgcolor="#0d0d0d", plot_bgcolor="#141414", font_color="#f8fafc")`.

The live stat cards on the landing page pull real data from the gold layer if available; fall back to static placeholder values if the DB is empty (landing page should never block on data).

## Files Modified

- `dashboard/style.py` — new: shared CSS injection helpers
- `dashboard/app.py` — landing page rebuilt with new HTML/CSS structure
- `dashboard/pages/1_Dashboard.py` — inject dark CSS, update Plotly theme
- `dashboard/app.py` (chart functions) — update `fig.update_layout` in all 4 chart builders
