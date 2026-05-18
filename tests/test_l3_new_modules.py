import pandas as pd
import numpy as np
import pytest
from engine.layers.l3_indicators import compute_indicators_single_tf
from engine.layers.l3_reference_levels import compute_floor_pivots, compute_cpr_levels
from engine.layers.l3_volume_seasonality import adjust_volume, compute_volume_confirm
from engine.layers.l3_options import compute_iv_percentile, compute_expected_range, compute_rv_iv_ratio


def test_indicators_single_tf():
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "open": np.random.uniform(995, 1005, n),
        "high": np.random.uniform(1000, 1010, n),
        "low": np.random.uniform(990, 1000, n),
        "close": np.random.uniform(995, 1005, n),
        "volume": np.random.randint(10000, 50000, n),
    })
    result = compute_indicators_single_tf(df, "5m")
    assert "ema_9_5m" in result.columns
    assert "supertrend_5m" in result.columns
    assert "adx_5m" in result.columns
    assert "rsi_5m" in result.columns
    assert "atr_pctile_5m" in result.columns


def test_floor_pivots():
    levels = compute_floor_pivots(prev_high=110, prev_low=90, prev_close=100)
    assert levels["pivot"] == 100.0
    assert levels["r1"] == 110.0
    assert levels["s1"] == 90.0


def test_cpr():
    levels = compute_cpr_levels(prev_high=110, prev_low=90, prev_close=100)
    assert levels["pivot"] == 100.0
    assert levels["bc"] == 100.0


def test_volume_confirm():
    assert compute_volume_confirm(v_adj=2.0, median_adj=1.0) is True
    assert compute_volume_confirm(v_adj=1.2, median_adj=1.0) is False


def test_iv_percentile():
    assert compute_iv_percentile(16, [10, 15, 20, 25]) == 0.5  # 2/4 = 0.5


def test_expected_range():
    import math
    er = compute_expected_range(atm=1000, iv=0.20)
    assert er["expected_move"] == pytest.approx(1000 * 0.20 / math.sqrt(252), rel=0.01)


def test_rv_iv_ratio():
    assert compute_rv_iv_ratio(20, 25) == 0.8
    assert compute_rv_iv_ratio(25, 20) == 1.25
    assert compute_rv_iv_ratio(20, 0) == 1.0
