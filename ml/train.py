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
