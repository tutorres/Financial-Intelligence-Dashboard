import pytest
import duckdb
import torch
from datetime import date, timedelta
from pathlib import Path

from ml.model import LSTMClassifier
from ml.predict import predict


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA features")
    c.execute("CREATE SCHEMA gold")
    c.execute("""
        CREATE TABLE features.model_input (
            ticker VARCHAR, date DATE,
            close_norm DOUBLE, volume_norm DOUBLE,
            ma_7_norm DOUBLE, ma_21_norm DOUBLE,
            rsi_14 DOUBLE, daily_return DOUBLE
        )
    """)
    start = date(2024, 1, 1)
    for i in range(35):
        d = start + timedelta(days=i)
        c.execute(
            "INSERT INTO features.model_input VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ["AAPL", d, 0.5, 0.5, 0.5, 0.5, 50.0, 0.01],
        )
    yield c
    c.close()


def test_noop_when_no_model_file(conn, tmp_path, monkeypatch):
    monkeypatch.setattr("ml.predict.MODEL_PATH", tmp_path / "nonexistent.pt")
    predict(conn=conn)
    # gold.predictions should not have been created
    with pytest.raises(Exception):
        conn.execute("SELECT * FROM gold.predictions").fetchdf()


def test_writes_predictions(conn, tmp_path, monkeypatch):
    model = LSTMClassifier()
    model_path = tmp_path / "model.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "feature_cols": ["close_norm", "volume_norm", "ma_7_norm", "ma_21_norm", "rsi_14", "daily_return"],
            "sequence_len": 30,
            "hidden_size": 64,
            "num_layers": 2,
        },
        model_path,
    )
    monkeypatch.setattr("ml.predict.MODEL_PATH", model_path)

    predict(conn=conn)

    result = conn.execute(
        "SELECT signal, confidence, p_down, p_neutral, p_up FROM gold.predictions WHERE ticker = 'AAPL'"
    ).fetchdf()
    assert len(result) == 1
    assert result.iloc[0]["signal"] in ("UP", "DOWN", "NEUTRAL")
    assert 0.0 <= result.iloc[0]["confidence"] <= 1.0
    total = result.iloc[0]["p_down"] + result.iloc[0]["p_neutral"] + result.iloc[0]["p_up"]
    assert abs(total - 1.0) < 1e-5
