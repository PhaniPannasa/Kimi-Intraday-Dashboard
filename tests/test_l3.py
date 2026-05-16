import pytest
import pandas as pd
import numpy as np
from layers.l3_signals import compute_indicators, ema_aligned


def make_ohlc(n=100):
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.random.randint(1000, 10000, n)
    })


def test_compute_indicators():
    df = make_ohlc(50)
    result = compute_indicators(df)
    assert "ema_9" in result.columns
    assert "rsi" in result.columns
    assert "adx" in result.columns


def test_ema_aligned():
    df = make_ohlc(50)
    df = compute_indicators(df)
    aligned = ema_aligned(df)
    assert isinstance(aligned, bool)
