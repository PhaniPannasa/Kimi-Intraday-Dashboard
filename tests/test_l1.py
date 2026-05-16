import pytest
import polars as pl
from layers.l1_market_context import L1MarketContext, classify_regime
from models.enums import Regime


def make_nifty_df(trend="up"):
    closes = list(range(100, 200)) if trend == "up" else list(range(200, 100, -1))
    return pl.DataFrame({
        "close": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
    })


def test_classify_regime_trending_up():
    df = make_nifty_df("up")
    regime, conf = classify_regime(df)
    assert regime == Regime.TRENDING_UP.value


def test_classify_regime_trending_down():
    df = make_nifty_df("down")
    regime, conf = classify_regime(df)
    assert regime == Regime.TRENDING_DOWN.value


def test_l1_compute():
    l1 = L1MarketContext()
    nifty = make_nifty_df("up")
    result = l1.compute(nifty, 20.0, {})
    assert result.regime == Regime.TRENDING_UP.value
