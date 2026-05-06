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
