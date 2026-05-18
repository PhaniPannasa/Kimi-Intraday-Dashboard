import pytest
from layers.l5_scoring import L5Scoring, compute_f1_trend, compute_raw_score
from models.enums import Regime


def test_compute_f1_trend():
    assert compute_f1_trend(True, True, 30) >= 85
    assert compute_f1_trend(False, False, 10) == 5


def test_compute_raw_score():
    factors = {"f1": 100, "f2": 100, "f3": 100, "f4": 100, "f5": 100, "f6": 100, "f7": 100}
    raw = compute_raw_score(factors, Regime.TRENDING_UP.value)
    assert 90 < raw <= 100


def test_l5_scoring():
    l5 = L5Scoring()
    result = l5.compute(
        {"symbol": "RELIANCE", "ema_aligned": True, "supertrend_bull": True, "adx": 30,
         "rsi": 55, "macd_divergence": True, "roc_z": 1.0, "above_vwap": True,
         "vol_z": 2.0, "vol_confirm": True, "direction": "LONG"},
        Regime.TRENDING_UP.value,
        {"rank": 1, "tailwind": True},
        {"classification": "Long Buildup"}
    )
    assert result["score"] > 0
    assert "factors" in result
