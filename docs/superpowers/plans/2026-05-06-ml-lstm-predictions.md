# ML LSTM Predictions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PyTorch LSTM that predicts UP/DOWN/NEUTRAL trend per ticker and surfaces the signal + probability bars in a new Predictions tab in the dashboard.

**Architecture:** Single LSTM trained on all tickers combined using `features.model_input`. Weights committed as `ml/model.pt` and loaded at runtime by `ml/predict.py`, which writes one row per ticker to `gold.predictions`. The dashboard reads `gold.predictions` to render the tab. Training is always local; Streamlit Cloud only runs inference.

**Tech Stack:** PyTorch 2.x (CPU), DuckDB, Streamlit + Plotly

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `ml/__init__.py` | package marker |
| Create | `ml/dataset.py` | `StockSequenceDataset` — builds (sequence, label) pairs |
| Create | `ml/model.py` | `LSTMClassifier` definition |
| Create | `ml/train.py` | training script, saves `ml/model.pt` |
| Create | `ml/predict.py` | inference, writes `gold.predictions` |
| Modify | `pipeline/run.py` | add `predict(conn=conn)` as final step |
| Modify | `dashboard/app.py` | add `load_prediction`, `fig_prediction_probs` |
| Modify | `dashboard/pages/1_Dashboard.py` | add Predictions tab |
| Modify | `requirements.txt` | add torch (CPU index) |
| Create | `tests/ml/__init__.py` | package marker |
| Create | `tests/ml/test_model.py` | model output shape |
| Create | `tests/ml/test_dataset.py` | sequence shape, count, feature cols |
| Create | `tests/ml/test_predict.py` | no-op when no model, writes predictions |

---

## Task 1: Dependencies and package skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `ml/__init__.py`
- Create: `tests/ml/__init__.py`

- [ ] **Step 1: Add torch to requirements.txt**

Replace the existing `requirements.txt` with:

```
--extra-index-url https://download.pytorch.org/whl/cpu
duckdb>=0.10.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
pytest>=8.0.0
streamlit>=1.32.0
plotly>=5.20.0
torch>=2.0.0
```

The `--extra-index-url` installs the CPU-only wheel (~250 MB vs 2 GB for CUDA).

- [ ] **Step 2: Create package markers**

`ml/__init__.py` — empty file.

`tests/ml/__init__.py` — empty file.

- [ ] **Step 3: Verify torch installs**

```bash
pip install -r requirements.txt
python -c "import torch; print(torch.__version__)"
```

Expected: prints a version string like `2.5.1+cpu`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt ml/__init__.py tests/ml/__init__.py
git commit -m "feat: add torch dependency and ml package skeleton"
```

---

## Task 2: LSTMClassifier (TDD)

**Files:**
- Create: `tests/ml/test_model.py`
- Create: `ml/model.py`

- [ ] **Step 1: Write failing tests**

`tests/ml/test_model.py`:

```python
import torch
import pytest
from ml.model import LSTMClassifier


def test_output_shape_batch():
    model = LSTMClassifier()
    x = torch.randn(4, 30, 6)  # batch=4, seq=30, features=6
    logits = model(x)
    assert logits.shape == (4, 3)


def test_output_shape_single():
    model = LSTMClassifier()
    x = torch.randn(1, 30, 6)
    logits = model(x)
    assert logits.shape == (1, 3)


def test_custom_hidden_size():
    model = LSTMClassifier(input_size=6, hidden_size=32, num_layers=1)
    x = torch.randn(2, 30, 6)
    logits = model(x)
    assert logits.shape == (2, 3)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/ml/test_model.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `ml.model`

- [ ] **Step 3: Implement `ml/model.py`**

```python
import torch.nn as nn


class LSTMClassifier(nn.Module):
    def __init__(self, input_size=6, hidden_size=64, num_layers=2, num_classes=3, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        _, (hidden, _) = self.lstm(x)
        # hidden: (num_layers, batch, hidden_size) — take last layer
        return self.classifier(hidden[-1])
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/ml/test_model.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add ml/model.py tests/ml/test_model.py
git commit -m "feat: add LSTMClassifier"
```

---

## Task 3: StockSequenceDataset (TDD)

**Files:**
- Create: `tests/ml/test_dataset.py`
- Create: `ml/dataset.py`

- [ ] **Step 1: Write failing tests**

`tests/ml/test_dataset.py`:

```python
import pytest
import duckdb
import torch
from datetime import date, timedelta

from ml.dataset import StockSequenceDataset, FEATURE_COLS


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
    c.execute("CREATE TABLE gold.prices (ticker VARCHAR, date DATE, close DOUBLE)")

    start = date(2024, 1, 1)
    for ticker in ["AAPL", "MSFT"]:
        for i in range(50):
            d = start + timedelta(days=i)
            c.execute(
                "INSERT INTO features.model_input VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [ticker, d, 0.5, 0.5, 0.5, 0.5, 50.0, 0.01],
            )
            c.execute(
                "INSERT INTO gold.prices VALUES (?, ?, ?)",
                [ticker, d, 100.0 + i],  # rising → all UP labels
            )
    yield c
    c.close()


def test_sequence_shape(conn):
    ds = StockSequenceDataset(conn, sequence_len=30, forward_days=5)
    x, y = ds[0]
    assert x.shape == (30, 6)
    assert x.dtype == torch.float32
    assert y.shape == ()   # scalar tensor
    assert y.dtype == torch.long


def test_sample_count(conn):
    # n=50, seq_len=30, forward_days=5
    # valid windows per ticker: n - seq_len - forward_days + 1 = 16
    # 2 tickers → 32 total
    ds = StockSequenceDataset(conn, sequence_len=30, forward_days=5)
    assert len(ds) == 32


def test_feature_cols(conn):
    ds = StockSequenceDataset(conn)
    assert ds.feature_cols == FEATURE_COLS
    assert len(ds.feature_cols) == 6
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/ml/test_dataset.py -v
```

Expected: `ImportError` for `ml.dataset`

- [ ] **Step 3: Implement `ml/dataset.py`**

```python
import numpy as np
import torch
from torch.utils.data import Dataset

FEATURE_COLS = ["close_norm", "volume_norm", "ma_7_norm", "ma_21_norm", "rsi_14", "daily_return"]


class StockSequenceDataset(Dataset):
    def __init__(self, conn, sequence_len=30, forward_days=5, up_threshold=0.01, down_threshold=-0.01):
        self.sequence_len = sequence_len
        self.feature_cols = FEATURE_COLS

        features = conn.execute(
            "SELECT ticker, date, close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return "
            "FROM features.model_input ORDER BY ticker, date"
        ).df()

        prices = conn.execute(
            "SELECT ticker, date, close FROM gold.prices ORDER BY ticker, date"
        ).df()

        sequences, labels = [], []

        for ticker, feat_group in features.groupby("ticker"):
            feat_group = feat_group.reset_index(drop=True)
            price_group = prices[prices["ticker"] == ticker].sort_values("date").reset_index(drop=True)

            price_dates = price_group["date"].tolist()
            price_by_date = price_group.set_index("date")["close"].to_dict()
            date_to_idx = {d: i for i, d in enumerate(price_dates)}

            n = len(feat_group)
            for i in range(n - sequence_len + 1):
                window = feat_group.iloc[i : i + sequence_len]
                last_date = window.iloc[-1]["date"]

                current_close = price_by_date.get(last_date)
                if not current_close:
                    continue

                last_price_idx = date_to_idx.get(last_date)
                if last_price_idx is None:
                    continue
                future_price_idx = last_price_idx + forward_days
                if future_price_idx >= len(price_dates):
                    continue

                future_close = price_by_date[price_dates[future_price_idx]]
                ret = (future_close - current_close) / current_close

                if ret > up_threshold:
                    label = 2
                elif ret < down_threshold:
                    label = 0
                else:
                    label = 1

                sequences.append(window[FEATURE_COLS].values.astype(np.float32))
                labels.append(label)

        self.sequences = [torch.tensor(s) for s in sequences]
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/ml/test_dataset.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add ml/dataset.py tests/ml/test_dataset.py
git commit -m "feat: add StockSequenceDataset"
```

---

## Task 4: predict.py (TDD)

**Files:**
- Create: `tests/ml/test_predict.py`
- Create: `ml/predict.py`

- [ ] **Step 1: Write failing tests**

`tests/ml/test_predict.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/ml/test_predict.py -v
```

Expected: `ImportError` for `ml.predict`

- [ ] **Step 3: Implement `ml/predict.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/ml/test_predict.py -v
```

Expected: 2 passed

- [ ] **Step 5: Run full test suite — no regressions**

```bash
python -m pytest -v
```

Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add ml/predict.py tests/ml/test_predict.py
git commit -m "feat: add predict() — inference writes to gold.predictions"
```

---

## Task 5: train.py

**Files:**
- Create: `ml/train.py`

No unit test for the training loop — it touches the full pipeline and is validated by running it in Task 8.

- [ ] **Step 1: Implement `ml/train.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from ml.dataset import StockSequenceDataset
from ml.model import LSTMClassifier
from pipeline.utils import get_connection, get_logger

MODEL_PATH = Path(__file__).parent / "model.pt"
logger = get_logger(__name__)


def train() -> None:
    conn = get_connection()
    try:
        dataset = StockSequenceDataset(conn)
    finally:
        conn.close()

    if len(dataset) == 0:
        logger.error("Dataset is empty — run the pipeline first: python -m pipeline.run")
        return

    n = len(dataset)
    split = int(n * 0.8)
    train_ds = Subset(dataset, list(range(split)))
    val_ds = Subset(dataset, list(range(split, n)))

    logger.info("Dataset: %d total, %d train, %d val", n, len(train_ds), len(val_ds))

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=32)

    model = LSTMClassifier()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    best_val_loss = float("inf")
    patience, no_improve = 10, 0

    for epoch in range(1, 101):
        model.train()
        train_loss = sum(
            _step(model, criterion, optimizer, X, y) * len(X)
            for X, y in train_loader
        ) / len(train_ds)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X, y in val_loader:
                val_loss += criterion(model(X), y).item() * len(X)
        val_loss /= len(val_ds)

        logger.info("Epoch %3d  train=%.4f  val=%.4f", epoch, train_loss, val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            no_improve = 0
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "feature_cols": dataset.feature_cols,
                    "sequence_len": dataset.sequence_len,
                    "hidden_size": 64,
                    "num_layers": 2,
                },
                MODEL_PATH,
            )
        else:
            no_improve += 1
            if no_improve >= patience:
                logger.info("Early stopping at epoch %d", epoch)
                break

    logger.info("Done. Best val loss: %.4f. Saved to %s", best_val_loss, MODEL_PATH)


def _step(model, criterion, optimizer, X, y) -> float:
    optimizer.zero_grad()
    loss = criterion(model(X), y)
    loss.backward()
    optimizer.step()
    return loss.item()


if __name__ == "__main__":
    train()
```

- [ ] **Step 2: Commit**

```bash
git add ml/train.py
git commit -m "feat: add train.py — LSTM training with early stopping"
```

---

## Task 6: Wire predict into pipeline/run.py

**Files:**
- Modify: `pipeline/run.py`

- [ ] **Step 1: Update `pipeline/run.py`**

Replace the full file contents:

```python
from ml.predict import predict
from pipeline.aggregate import aggregate
from pipeline.ingest import ingest
from pipeline.ml_features import ml_features
from pipeline.transform import transform
from pipeline.utils import get_connection, get_logger

logger = get_logger(__name__)


def run() -> None:
    conn = get_connection()
    try:
        logger.info("Pipeline started")
        ingest(conn=conn)
        transform(conn=conn)
        aggregate(conn=conn)
        ml_features(conn=conn)
        predict(conn=conn)
        logger.info("Pipeline complete")
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run pipeline end-to-end — verify no errors**

```bash
python -m pipeline.run
```

Expected output (model.pt absent at this point):
```
[INFO] pipeline.run: Pipeline started
[INFO] pipeline.ingest: Ingested N rows for AAPL
...
[INFO] pipeline.ml_features: Computed N ML feature rows...
[INFO] ml.predict: ml/model.pt not found — skipping predictions
[INFO] pipeline.run: Pipeline complete
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/run.py
git commit -m "feat: wire predict() into pipeline run — no-op until model.pt exists"
```

---

## Task 7: Dashboard Predictions tab

**Files:**
- Modify: `dashboard/app.py` — add `load_prediction`, `fig_prediction_probs`
- Modify: `dashboard/pages/1_Dashboard.py` — add Predictions tab

- [ ] **Step 1: Add `load_prediction` and `fig_prediction_probs` to `dashboard/app.py`**

Add after the `rsi_signal` function (before `fmt_volume`):

```python
def load_prediction(conn, ticker: str) -> dict | None:
    try:
        row = conn.execute(
            "SELECT signal, confidence, p_down, p_neutral, p_up, predicted_at "
            "FROM gold.predictions WHERE ticker = ?",
            [ticker],
        ).fetchdf()
    except Exception:
        return None
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def fig_prediction_probs(pred: dict) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=[pred["p_down"], pred["p_neutral"], pred["p_up"]],
        y=["DOWN", "NEUTRAL", "UP"],
        orientation="h",
        marker_color=["#525252", "#737373", "#e5e5e5"],
        text=[f"{pred['p_down']*100:.1f}%", f"{pred['p_neutral']*100:.1f}%", f"{pred['p_up']*100:.1f}%"],
        textposition="outside",
        textfont=dict(color="#737373", size=12),
    ))
    fig.update_layout(
        height=200,
        xaxis=dict(range=[0, 1.2], tickformat=".0%", showgrid=False),
        yaxis=dict(showgrid=False),
    )
    return apply_theme(fig)
```

- [ ] **Step 2: Add Predictions tab to `dashboard/pages/1_Dashboard.py`**

Update the import from `dashboard.app` to include the two new functions:

```python
from dashboard.app import (
    _get_db_connection,
    fig_candlestick,
    fig_macd,
    fig_prediction_probs,
    fig_rsi,
    fig_volume,
    fmt_volume,
    load_prediction,
    load_prices,
    load_summary,
    rsi_signal,
)
```

Change the tabs line from:

```python
tab1, tab2, tab3 = st.tabs(["Overview", "Price & Volume", "Technical Indicators"])
```

to:

```python
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Price & Volume", "Technical Indicators", "Predictions"])
```

Add the new tab block after the `with tab3:` block:

```python
    with tab4:
        pred = load_prediction(conn, ticker)
        if pred is None:
            st.markdown(
                '<p style="color:#525252;font-family:\'Geist Mono\',monospace;font-size:12px;'
                'line-height:1.8;margin-top:1rem">'
                'No prediction available.<br>'
                'Train the model locally, then redeploy:<br>'
                '<code style="color:#737373">python ml/train.py</code></p>',
                unsafe_allow_html=True,
            )
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Signal", pred["signal"])
            c2.metric("Confidence", f"{pred['confidence'] * 100:.1f}%")
            c3.metric("Predicted", str(pred["predicted_at"])[:16])
            st.plotly_chart(fig_prediction_probs(pred), width="stretch")
```

- [ ] **Step 3: Verify no import errors**

```bash
python -c "from dashboard.app import load_prediction, fig_prediction_probs; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py dashboard/pages/1_Dashboard.py
git commit -m "feat: add Predictions tab — signal, confidence, probability bars"
```

---

## Task 8: Train model locally and commit weights

- [ ] **Step 1: Run the pipeline to ensure fresh data**

```bash
python -m pipeline.run
```

Expected: pipeline completes, all tickers ingested, no errors.

- [ ] **Step 2: Train the model**

```bash
python ml/train.py
```

Expected: prints per-epoch loss, stops early, saves `ml/model.pt`. Typical output:
```
[INFO] ml.train: Dataset: 752 total, 601 train, 151 val
[INFO] ml.train: Epoch   1  train=1.0891  val=1.0832
...
[INFO] ml.train: Early stopping at epoch N
[INFO] ml.train: Done. Best val loss: X.XXXX. Saved to ml/model.pt
```

- [ ] **Step 3: Verify inference works end-to-end**

```bash
python ml/predict.py
python -c "
from pipeline.utils import get_connection
conn = get_connection()
print(conn.execute('SELECT * FROM gold.predictions').fetchdf())
conn.close()
"
```

Expected: a DataFrame with 4 rows (one per ticker), each with a signal, confidence, and probabilities summing to 1.

- [ ] **Step 4: Add model.pt to git and commit**

```bash
git add ml/model.pt
git commit -m "ml: add trained LSTM weights (CPU, hidden=64, layers=2)"
git push
```

Expected: `ml/model.pt` committed (~200–400 KB binary).

- [ ] **Step 5: Run the full test suite one final time**

```bash
python -m pytest -v
```

Expected: all tests pass.
