import numpy as np
import polars as pl
from engine.layers.l1_market_context import classify_regime, compute_vol_z_diurnal
from models.enums import Regime


def test_range_bound_when_flat_prices():
    df = pl.DataFrame({"close": [100.0] * 100})
    regime, conf = classify_regime(df)
    assert regime == Regime.RANGE_BOUND.value


def test_trending_up_clear_uptrend():
    close = np.linspace(100, 110, 100) + np.random.normal(0, 0.5, 100)
    df = pl.DataFrame({"close": close})
    regime, _ = classify_regime(df)
    assert regime == Regime.TRENDING_UP.value


def test_trending_down_clear_downtrend():
    close = np.linspace(110, 100, 100) + np.random.normal(0, 0.3, 100)
    df = pl.DataFrame({"close": close})
    regime, _ = classify_regime(df)
    assert regime == Regime.TRENDING_DOWN.value


def test_small_slope_low_vol_is_range_bound():
    close = 100 + np.sin(np.linspace(0, 6 * np.pi, 100)) * 0.0005
    df = pl.DataFrame({"close": close})
    regime, _ = classify_regime(df)
    assert regime == Regime.RANGE_BOUND.value

def test_vol_z_diurnal_returns_float():
    import polars as pl
    import numpy as np
    from engine.layers.l1_market_context import compute_vol_z_diurnal
    np.random.seed(42)
    n_bars = 20 * 75  # 20 days
    close = 100 + np.cumsum(np.random.normal(0, 1, n_bars))
    df = pl.DataFrame({"close": close})
    result = compute_vol_z_diurnal(df, current_bucket=40, n_buckets=75)
    assert isinstance(result, float)
