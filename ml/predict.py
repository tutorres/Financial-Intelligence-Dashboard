import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch

from ml.model import LSTMClassifier
from pipeline.utils import get_connection, get_logger, setup_schemas

MODEL_PATH = Path(__file__).parent / "model.pt"
LABELS = {0: "DOWN", 1: "NEUTRAL", 2: "UP"}
logger = get_logger(__name__)


def _create_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold.predictions (
            ticker       VARCHAR NOT NULL PRIMARY KEY,
            signal       VARCHAR NOT NULL,
            confidence   DOUBLE  NOT NULL,
            p_down       DOUBLE  NOT NULL,
            p_neutral    DOUBLE  NOT NULL,
            p_up         DOUBLE  NOT NULL,
            predicted_at TIMESTAMP NOT NULL
        )
    """)


def predict(conn=None) -> None:
    if not MODEL_PATH.exists():
        logger.info("ml/model.pt not found — skipping predictions")
        return

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    setup_schemas(conn)
    _create_table(conn)

    artefact = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    model = LSTMClassifier(
        input_size=len(artefact["feature_cols"]),
        hidden_size=artefact["hidden_size"],
        num_layers=artefact["num_layers"],
    )
    model.load_state_dict(artefact["state_dict"])
    model.eval()

    feature_cols = artefact["feature_cols"]
    seq_len = artefact["sequence_len"]

    features = conn.execute(
        "SELECT ticker, date, close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return "
        "FROM features.model_input ORDER BY ticker, date"
    ).df()

    now = datetime.now(timezone.utc)
    rows = []

    for ticker, group in features.groupby("ticker"):
        if len(group) < seq_len:
            logger.warning("Not enough rows for %s (%d < %d) — skipping", ticker, len(group), seq_len)
            continue

        window = group.iloc[-seq_len:][feature_cols].values.astype(np.float32)
        x = torch.tensor(window).unsqueeze(0)  # (1, seq_len, features)

        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=-1).squeeze().numpy()

        signal_idx = int(np.argmax(probs))
        rows.append(
            {
                "ticker": ticker,
                "signal": LABELS[signal_idx],
                "confidence": float(probs[signal_idx]),
                "p_down": float(probs[0]),
                "p_neutral": float(probs[1]),
                "p_up": float(probs[2]),
                "predicted_at": now,
            }
        )

    if rows:
        conn.execute("DELETE FROM gold.predictions")
        df = pd.DataFrame(rows)
        conn.execute("INSERT INTO gold.predictions SELECT * FROM df")
        logger.info("Wrote %d prediction rows to gold.predictions", len(rows))

    if own_conn:
        conn.close()


if __name__ == "__main__":
    predict()
