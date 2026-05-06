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
