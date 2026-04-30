# tests/dashboard/test_style.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.style import inject_global_css, inject_dashboard_css


def test_inject_global_css_is_style_tag():
    css = inject_global_css()
    assert css.startswith("<style>")
    assert css.endswith("</style>")


def test_inject_global_css_contains_dark_bg():
    css = inject_global_css()
    assert "#0d0d0d" in css


def test_inject_global_css_contains_green_accent():
    css = inject_global_css()
    assert "#00ff88" in css


def test_inject_dashboard_css_is_style_tag():
    css = inject_dashboard_css()
    assert css.startswith("<style>")
    assert css.endswith("</style>")


def test_inject_dashboard_css_styles_metric_container():
    css = inject_dashboard_css()
    assert "metric-container" in css
    assert "#141414" in css


def test_inject_dashboard_css_styles_tabs():
    css = inject_dashboard_css()
    assert "tab" in css
    assert "#00ff88" in css
