# ML LSTM Predictions — Design Spec

**Date:** 2026-05-06
**Status:** Approved

---

## Overview

Add a PyTorch LSTM trend classifier to the Financial Intelligence Dashboard. The model is trained locally and committed as `ml/model.pt`. Streamlit Cloud only runs inference. The dashboard gains a Predictions tab showing the current UP/DOWN/NEUTRAL signal and class probability bars for the selected ticker.

---

## Data Flow

```
features.model_input  ──►  ml/dataset.py  ──►  ml/train.py  ──►  ml/model.pt
                                                                        │
features.model_input  ──►  ml/predict.py  ◄────────────────────────────┘
                                │
                                ▼
                        gold.predictions   ──►  Dashboard: Predictions tab
```

---

## Labels

For each row at date T in `features.model_input`, look up `close` at T+5 in `gold.prices`:

- `return = (close[T+5] - close[T]) / close[T]`
- UP if return > +0.01
- DOWN if return < -0.01
- NEUTRAL otherwise

Rows where T+5 does not exist (the last 5 dates per ticker) are excluded from training and used as the inference window.

Classes: `DOWN=0, NEUTRAL=1, UP=2`

---

## Model Architecture

```
Input:  (batch, 30, 6)
        features: [close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return]

LSTM(input_size=6, hidden_size=64, num_layers=2, dropout=0.2, batch_first=True)
        ↓ last hidden state
Linear(64, 3)
        ↓
Softmax → [P(DOWN), P(NEUTRAL), P(UP)]
```

- Loss: CrossEntropyLoss
- Optimizer: Adam, lr=1e-3
- Train/val split: 80/20 chronological (no shuffle)
- Early stopping: patience=10, max_epochs=100
- Saved artefact: `ml/model.pt` — `{state_dict, feature_cols, sequence_len, hidden_size, num_layers}`

---

## File Structure

```
ml/
  __init__.py
  dataset.py     — StockSequenceDataset: builds (sequence, label) pairs from features.model_input
  model.py       — LSTMClassifier definition
  train.py       — training script, saves ml/model.pt
  predict.py     — inference script, writes gold.predictions
```

---

## `ml/dataset.py`

`StockSequenceDataset(conn, sequence_len=30, forward_days=5, thresholds=(0.01, -0.01))`

- Loads `features.model_input` joined with `gold.prices` for forward close lookup
- Feature columns: `[close_norm, volume_norm, ma_7_norm, ma_21_norm, rsi_14, daily_return]`
- Builds sliding windows of length 30 over the labelled rows
- Returns `(tensor[30, 6], label_int)` pairs
- Exposes `feature_cols` list for artefact saving

---

## `ml/model.py`

`LSTMClassifier(input_size=6, hidden_size=64, num_layers=2, num_classes=3, dropout=0.2)`

- Standard `nn.LSTM` + `nn.Linear` head
- `forward(x)` takes `(batch, seq, features)`, returns `(batch, 3)` logits

---

## `ml/train.py`

1. Connect to DuckDB, instantiate `StockSequenceDataset`
2. Chronological 80/20 split → `DataLoader` (batch=32)
3. Training loop with early stopping
4. Print per-epoch train/val loss
5. Save `ml/model.pt`:
   ```python
   torch.save({
       "state_dict": model.state_dict(),
       "feature_cols": dataset.feature_cols,
       "sequence_len": 30,
       "hidden_size": 64,
       "num_layers": 2,
   }, "ml/model.pt")
   ```

---

## `ml/predict.py`

`predict(conn=None) -> None`

1. Return silently if `ml/model.pt` does not exist
2. Load artefact, reconstruct `LSTMClassifier`, set `eval()`
3. For each ticker, take the most recent 30 rows from `features.model_input`
4. Run forward pass → softmax probabilities
5. `signal = argmax` → label string; `confidence = max(probs)`
6. Create `gold.predictions` table if needed, upsert one row per ticker:
   `(ticker, signal, confidence, p_down, p_neutral, p_up, predicted_at)`

---

## `pipeline/run.py` changes

Add `predict()` as the final step:

```python
from ml.predict import predict

def run():
    ...
    ml_features(conn=conn)
    predict(conn=conn)   # no-op if ml/model.pt absent
    ...
```

---

## Dashboard — Predictions Tab

New fourth tab in `dashboard/pages/1_Dashboard.py`.

**If no prediction row exists for ticker:**
```
No prediction available — train the model locally first:
  python ml/train.py
```

**If prediction exists:**

- `st.metric` row: signal label | confidence | predicted_at
- Signal colors (no red/green): UP → `#e5e5e5`, NEUTRAL → `#737373`, DOWN → `#525252`
- Horizontal Plotly bar chart for `[P(DOWN), P(NEUTRAL), P(UP)]` styled via `apply_theme()`

---

## Testing

- `tests/ml/test_dataset.py` — verify sequence shape, label distribution, no data leakage past last 5 rows
- `tests/ml/test_model.py` — verify forward pass output shape `(batch, 3)`, logits sum correctly after softmax
- `tests/ml/test_predict.py` — verify `gold.predictions` schema and that predict() is a no-op when model.pt absent

---

## Constraints

- `torch` added to `requirements.txt`
- `ml/model.pt` committed to git (binary, ~200 KB for this architecture)
- Training runs locally only; Streamlit Cloud never calls `train.py`
- predict() is always a no-op if model.pt is absent — no exceptions surfaced to the dashboard
