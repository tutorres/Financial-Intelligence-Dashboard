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
    assert "#0a0a0a" in css


def test_inject_global_css_contains_primary_text():
    css = inject_global_css()
    assert "#e5e5e5" in css


def test_inject_dashboard_css_is_style_tag():
    css = inject_dashboard_css()
    assert css.startswith("<style>")
    assert css.endswith("</style>")


def test_inject_dashboard_css_styles_metric_container():
    css = inject_dashboard_css()
    assert "metric-container" in css
    assert "#111111" in css


def test_inject_dashboard_css_styles_tabs():
    css = inject_dashboard_css()
    assert "tab" in css
    assert "#e5e5e5" in css


def test_inject_global_css_does_not_contain_metric_container():
    css = inject_global_css()
    assert "metric-container" not in css


def test_inject_dashboard_css_does_not_contain_sidebar():
    css = inject_dashboard_css()
    assert "stSidebar" not in css
