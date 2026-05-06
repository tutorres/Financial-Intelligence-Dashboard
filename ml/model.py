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
