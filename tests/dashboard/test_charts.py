import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from dashboard.app import fig_candlestick, fig_volume, fig_rsi, fig_macd


def _make_df(n: int = 30, all_nan_ma50: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=n).date
    close = 100 + np.cumsum(rng.standard_normal(n))
    open_ = close * 0.99
    return pd.DataFrame({
        "date": dates,
        "open": open_,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        "rsi_14": rng.uniform(20, 80, n),
        "ma_7": pd.Series(close).rolling(7).mean().values,
        "ma_21": pd.Series(close).rolling(21).mean().values,
        "ma_50": float("nan") if all_nan_ma50 else pd.Series(close).rolling(50).mean().values,
        "macd": rng.standard_normal(n) * 0.5,
        "macd_signal": rng.standard_normal(n) * 0.4,
        "macd_hist": rng.standard_normal(n) * 0.1,
    })


# --- fig_candlestick ---

def test_fig_candlestick_returns_figure():
    assert isinstance(fig_candlestick(_make_df()), go.Figure)


def test_fig_candlestick_has_candlestick_trace():
    fig = fig_candlestick(_make_df())
    types = [type(t).__name__ for t in fig.data]
    assert "Candlestick" in types


def test_fig_candlestick_all_nan_ma50_skips_trace():
    df_full = _make_df(60)
    df_nan = _make_df(60, all_nan_ma50=True)
    fig_full = fig_candlestick(df_full)
    fig_nan = fig_candlestick(df_nan)
    # MA50 trace is skipped when all values are NaN, so fewer traces
    assert len(fig_full.data) > len(fig_nan.data)


# --- fig_volume ---

def test_fig_volume_returns_figure():
    assert isinstance(fig_volume(_make_df()), go.Figure)


def test_fig_volume_green_when_close_above_open():
    df = _make_df(5)
    df["close"] = df["open"] + 1  # close always > open
    fig = fig_volume(df)
    bar = fig.data[0]
    assert all(c == "#22c55e" for c in bar.marker.color)


def test_fig_volume_red_when_close_below_open():
    df = _make_df(5)
    df["close"] = df["open"] - 1  # close always < open
    fig = fig_volume(df)
    bar = fig.data[0]
    assert all(c == "#ef4444" for c in bar.marker.color)


# --- fig_rsi ---

def test_fig_rsi_returns_figure():
    assert isinstance(fig_rsi(_make_df()), go.Figure)


def test_fig_rsi_has_one_scatter_trace():
    fig = fig_rsi(_make_df())
    scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
    assert len(scatter_traces) == 1


def test_fig_rsi_has_two_hlines():
    fig = fig_rsi(_make_df())
    # hlines are stored as shapes in the layout
    assert len(fig.layout.shapes) == 2
    y_values = {s.y0 for s in fig.layout.shapes}
    assert 30 in y_values
    assert 70 in y_values


# --- fig_macd ---

def test_fig_macd_returns_figure():
    assert isinstance(fig_macd(_make_df()), go.Figure)


def test_fig_macd_has_three_traces():
    fig = fig_macd(_make_df())
    assert len(fig.data) == 3


def test_fig_macd_first_trace_is_bar():
    fig = fig_macd(_make_df())
    assert isinstance(fig.data[0], go.Bar)
