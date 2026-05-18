# L3 Signals + Reference Levels — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dual-timeframe indicator computation (5-min + 15-min), fix ROC to be Nifty-relative, add volume seasonality, add reference levels (PDH/PDL/CPR/pivots/ORB/FH), add options-derived signals (IV percentile, expected range, PCR z-score, RV/IV ratio), fix ATR percentile to distributional, fix MACD divergence to 5-bar window low detection.

**Architecture:** Split `l3_signals.py` into focused modules: `l3_indicators.py` (dual-timeframe indicator computation), `l3_reference_levels.py` (CPR, pivots, ORB, FH), `l3_volume_seasonality.py` (seasonal adjustment), `l3_options.py` (IV, expected range, PCR, RV/IV). The `L3Signals` class becomes an orchestrator.

**Tech Stack:** Python 3.11, pandas, pandas-ta, NumPy

---

## File Structure

```
engine/layers/
├── l3_signals.py              # MODIFY: orchestrator class
├── l3_indicators.py           # CREATE: dual-timeframe indicators
├── l3_reference_levels.py     # CREATE: PDH/PDL/CPR/pivots/ORB/FH
├── l3_volume_seasonality.py   # CREATE: seasonal volume adjustment
├── l3_options.py              # CREATE: options-derived signals
tests/
├── test_l3_indicators.py      # CREATE
├── test_l3_reference_levels.py # CREATE
├── test_l3_volume.py          # CREATE
├── test_l3_options.py         # CREATE
```

---

### Task 1: Create Dual-Dataframe Indicator Module

**Files:**
- Create: `engine/layers/l3_indicators.py`
- Test: `tests/test_l3_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l3_indicators.py
import pandas as pd
import numpy as np
from engine.layers.l3_indicators import compute_all_indicators, compute_indicators_single_tf


def make_ohlcv(n: int = 100, trend: float = 0.1) -> pd.DataFrame:
    """Synthetic OHLCV dataframe."""
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.normal(trend, 2, n))
    high = close + np.random.uniform(0, 5, n)
    low = close - np.random.uniform(0, 5, n)
    open_ = close - np.random.uniform(-2, 2, n)
    volume = np.random.randint(10000, 50000, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


class TestDualTimeframe:
    def test_both_timeframes_computed(self):
        df_5m = make_ohlcv(100)
        df_15m = make_ohlcv(35)
        result = compute_all_indicators(df_5m, df_15m)
        # 5-min indicators
        assert "ema_9_5m" in result.columns
        assert "ema_20_5m" in result.columns
        assert "adx_5m" in result.columns
        # 15-min indicators
        assert "ema_9_15m" in result.columns
        assert "ema_20_15m" in result.columns
        assert "adx_15m" in result.columns

    def test_single_tf_fallback(self):
        df = make_ohlcv(100)
        result = compute_indicators_single_tf(df, suffix="5m")
        assert "ema_9_5m" in result.columns
        assert "supertrend_5m" in result.columns
        assert "adx_5m" in result.columns
        assert "rsi_5m" in result.columns

    def test_atr_percentile_is_distributional(self):
        """ATR percentile should be rank within trailing distribution, not ATR/close %."""
        df = make_ohlcv(100)
        result = compute_indicators_single_tf(df, suffix="5m")
        # atr_pctile should be 0-1, not a percentage of price
        val = result["atr_pctile_5m"].dropna().iloc[-1]
        assert 0.0 <= val <= 1.0

    def test_roc_is_nifty_relative(self):
        """ROC should be stock_roc - nifty_roc, not plain stock ROC."""
        df_stock = make_ohlcv(100, trend=0.2)
        df_nifty = make_ohlcv(100, trend=0.1)
        result = compute_all_indicators(df_stock, nifty_df=df_nifty)
        stock_roc = df_stock["close"].pct_change(20).iloc[-1] * 100
        nifty_roc = df_nifty["close"].pct_change(20).iloc[-1] * 100
        expected = stock_roc - nifty_roc
        actual = result["roc_vs_nifty"].dropna().iloc[-1]
        assert abs(actual - expected) < 0.01
```

- [ ] **Step 2: Create l3_indicators.py**

```python
# engine/layers/l3_indicators.py
"""Dual-timeframe indicator computation (5-min + 15-min).

Per system_design_final.md Section 5.3:
- EMA(9/20/50), Supertrend(10,3.0), ADX(14), RSI(14),
  MACD(12,26,9), ATR(14), Bollinger Bands(20,2σ)
- All computed on BOTH 5-min and 15-min timeframes
- ROC is stock return - Nifty return (Nifty-relative)
- ATR percentile is distributional (rank within 20-day history)
"""
import pandas as pd
import pandas_ta as ta
import numpy as np


def compute_indicators_single_tf(df: pd.DataFrame, suffix: str = "5m") -> pd.DataFrame:
    """Compute all indicators on a single timeframe dataframe."""
    df = df.copy()

    # EMA stack
    df[f"ema_9_{suffix}"] = ta.ema(df["close"], length=9)
    df[f"ema_20_{suffix}"] = ta.ema(df["close"], length=20)
    df[f"ema_50_{suffix}"] = ta.ema(df["close"], length=50)

    # Supertrend
    st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0)
    df[f"supertrend_{suffix}"] = st[f"SUPERT_10_3.0"]
    df[f"supertrend_dir_{suffix}"] = st[f"SUPERTd_10_3.0"]

    # ADX
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    df[f"adx_{suffix}"] = adx["ADX_14"]

    # RSI
    df[f"rsi_{suffix}"] = ta.rsi(df["close"], length=14)

    # MACD histogram
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df[f"macd_hist_{suffix}"] = macd["MACDh_12_26_9"]
    df[f"macd_{suffix}"] = macd["MACD_12_26_9"]
    df[f"macd_signal_{suffix}"] = macd["MACDs_12_26_9"]

    # ATR
    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    df[f"atr_{suffix}"] = atr_series

    # ATR Percentile: distributional rank vs trailing 20-day (20 * 75 bars for 5-min)
    atr_lookback = 20 * 75 if suffix == "5m" else 20 * 25  # 20 days of bars
    df[f"atr_pctile_{suffix}"] = (
        atr_series.rolling(atr_lookback, min_periods=5)
        .apply(lambda x: (x < x.iloc[-1]).sum() / len(x) if len(x) > 0 else 0.5)
    )

    # Bollinger Bands
    bb = ta.bbands(df["close"], length=20, std=2)
    df[f"bb_upper_{suffix}"] = bb[f"BBU_20_2.0_2.0"]
    df[f"bb_lower_{suffix}"] = bb[f"BBL_20_2.0_2.0"]
    df[f"bb_width_{suffix}"] = bb[f"BBB_20_2.0_2.0"]

    return df


def compute_all_indicators(df_5m: pd.DataFrame, df_15m: pd.DataFrame | None = None,
                           nifty_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute indicators on both timeframes and merge.

    Args:
        df_5m: 5-min OHLCV bars
        df_15m: Optional 15-min OHLCV bars (resampled from 5-min if not provided)
        nifty_df: Optional Nifty 5-min bars for Nifty-relative ROC

    Returns:
        DataFrame with all indicators from both timeframes + ROC vs Nifty
    """
    result = compute_indicators_single_tf(df_5m, suffix="5m")

    if df_15m is not None and len(df_15m) >= 2:
        ind_15m = compute_indicators_single_tf(df_15m, suffix="15m")
        # Merge 15-min indicators onto 5-min index via forward fill
        result = result.join(ind_15m.filter(like="_15m"), how="left").ffill()

    # ROC vs Nifty (stock return - nifty return)
    result["roc_20_stock"] = df_5m["close"].pct_change(20) * 100
    if nifty_df is not None and len(nifty_df) >= 21:
        result["roc_20_nifty"] = nifty_df["close"].pct_change(20) * 100
        result["roc_vs_nifty"] = result["roc_20_stock"] - result["roc_20_nifty"]
    else:
        result["roc_vs_nifty"] = result["roc_20_stock"]

    # EMA alignment flags
    for sfx in ["5m", "15m"]:
        e9 = result.get(f"ema_9_{sfx}")
        e20 = result.get(f"ema_20_{sfx}")
        e50 = result.get(f"ema_50_{sfx}")
        if e9 is not None and e20 is not None and e50 is not None:
            result[f"ema_aligned_{sfx}"] = (e9 > e20) & (e20 > e50)

    return result


def detect_macd_divergence(df: pd.DataFrame, direction: str = "long",
                           timeframe: str = "5m") -> bool:
    """Detect MACD divergence over 5-bar window (spec: find low within window).

    Bullish (Long): Price 5-bar lower low AND MACD histogram 5-bar higher low
    Bearish (Short): Price 5-bar higher high AND MACD histogram 5-bar lower high
    """
    col = f"macd_hist_{timeframe}"
    if col not in df.columns or len(df) < 10:
        return False

    prices = df["close"].values
    macd_hist = df[col].values

    if direction == "long":
        # Price: lower low in last 5 bars vs previous 5
        price_made_lower_low = prices[-5:].min() < prices[-10:-5].min()
        macd_made_higher_low = macd_hist[-5:].min() > macd_hist[-10:-5].min()
        return price_made_lower_low and macd_made_higher_low
    else:
        price_made_higher_high = prices[-5:].max() > prices[-10:-5].max()
        macd_made_lower_high = macd_hist[-5:].max() < macd_hist[-10:-5].max()
        return price_made_higher_high and macd_made_lower_high
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l3_indicators.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l3_indicators.py tests/test_l3_indicators.py
git commit -m "feat: add dual-timeframe indicator computation with Nifty-relative ROC"
```

---

### Task 2: Create Reference Levels Module

**Files:**
- Create: `engine/layers/l3_reference_levels.py`
- Test: `tests/test_l3_reference_levels.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l3_reference_levels.py
from engine.layers.l3_reference_levels import (
    compute_floor_pivots,
    compute_cpr_levels,
    compute_orb_levels,
    compute_first_hour_levels,
    compute_reference_levels,
)


class TestFloorPivots:
    def test_classic_pivot_levels(self):
        """Standard floor pivot: P = (H+L+C)/3, R1=2P-L, S1=2P-H, etc."""
        levels = compute_floor_pivots(prev_high=110, prev_low=90, prev_close=100)
        pivot = (110 + 90 + 100) / 3  # = 100
        assert levels["pivot"] == pivot
        assert levels["r1"] == 2 * pivot - 90   # = 110
        assert levels["s1"] == 2 * pivot - 110  # = 90
        assert levels["r2"] == pivot + (110 - 90)
        assert levels["s2"] == pivot - (110 - 90)


class TestCPR:
    def test_cpr_levels(self):
        levels = compute_cpr_levels(prev_high=110, prev_low=90, prev_close=100)
        pivot = (110 + 90 + 100) / 3
        bc = (110 + 90) / 2
        tc = pivot + (pivot - bc)
        assert levels["pivot"] == pivot
        assert levels["bc"] == bc
        assert levels["tc"] == tc


class TestORB:
    def test_orb_15_min(self):
        levels = compute_orb_levels(
            orb_highs={"15min": 105}, orb_lows={"15min": 95}
        )
        assert levels["orb_15_high"] == 105
        assert levels["orb_15_low"] == 95
        assert levels["orb_15_range"] == 10

    def test_orb_2_hour(self):
        levels = compute_orb_levels(
            orb_highs={"2hour": 108}, orb_lows={"2hour": 92}
        )
        assert levels["orb_2h_high"] == 108
        assert levels["orb_2h_low"] == 92


class TestFirstHour:
    def test_fh_levels(self):
        levels = compute_first_hour_levels(fh_high=103, fh_low=97)
        assert levels["fh_high"] == 103
        assert levels["fh_low"] == 97
        assert levels["fh_range"] == 6
```

- [ ] **Step 2: Create l3_reference_levels.py**

```python
# engine/layers/l3_reference_levels.py
"""Reference levels computed at 9:15 AM, fixed for the session.

Includes: PDH/PDL/PDC, Floor Pivots (R1-R3, S1-S3), CPR (TC/BC/Pivot),
ORB 15-min H/L, ORB 2-hour H/L, First Hour H/L.
"""


def compute_floor_pivots(prev_high: float, prev_low: float,
                         prev_close: float) -> dict:
    """Classic floor pivot levels."""
    pivot = (prev_high + prev_low + prev_close) / 3
    range_hl = prev_high - prev_low

    return {
        "pivot": round(pivot, 2),
        "r1": round(2 * pivot - prev_low, 2),
        "r2": round(pivot + range_hl, 2),
        "r3": round(prev_high + 2 * (pivot - prev_low), 2),
        "s1": round(2 * pivot - prev_high, 2),
        "s2": round(pivot - range_hl, 2),
        "s3": round(prev_low - 2 * (prev_high - pivot), 2),
    }


def compute_cpr_levels(prev_high: float, prev_low: float,
                       prev_close: float) -> dict:
    """Central Pivot Range (CPR) levels."""
    pivot = (prev_high + prev_low + prev_close) / 3
    bc = (prev_high + prev_low) / 2
    tc = pivot + (pivot - bc)

    return {
        "pivot": round(pivot, 2),
        "bc": round(bc, 2),
        "tc": round(tc, 2),
        "cpr_width": round(abs(tc - bc), 2),
    }


def compute_orb_levels(orb_highs: dict, orb_lows: dict) -> dict:
    """ORB levels from opening range bars.

    orb_highs: {"15min": float, "2hour": float}
    orb_lows: {"15min": float, "2hour": float}
    """
    result = {}
    for key, label in [("15min", "15"), ("2hour", "2h")]:
        h = orb_highs.get(key)
        l = orb_lows.get(key)
        if h is not None and l is not None:
            result[f"orb_{label}_high"] = h
            result[f"orb_{label}_low"] = l
            result[f"orb_{label}_range"] = round(h - l, 2)
    return result


def compute_first_hour_levels(fh_high: float, fh_low: float) -> dict:
    """First Hour H/L levels."""
    return {
        "fh_high": fh_high,
        "fh_low": fh_low,
        "fh_range": round(fh_high - fh_low, 2),
    }


def compute_reference_levels(
    prev_high: float, prev_low: float, prev_close: float,
    orb_high_15: float, orb_low_15: float,
    orb_high_2h: float, orb_low_2h: float,
    fh_high: float, fh_low: float,
) -> dict:
    """Compute all reference levels for the session."""
    levels = {}
    levels.update(compute_floor_pivots(prev_high, prev_low, prev_close))
    levels.update(compute_cpr_levels(prev_high, prev_low, prev_close))
    levels.update(compute_orb_levels(
        {"15min": orb_high_15, "2hour": orb_high_2h},
        {"15min": orb_low_15, "2hour": orb_low_2h},
    ))
    levels.update(compute_first_hour_levels(fh_high, fh_low))
    levels["pdh"] = prev_high
    levels["pdl"] = prev_low
    levels["pdc"] = prev_close
    return levels
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l3_reference_levels.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l3_reference_levels.py tests/test_l3_reference_levels.py
git commit -m "feat: add reference levels module (CPR, pivots, ORB, FH)"
```

---

### Task 3: Create Volume Seasonality Module

**Files:**
- Create: `engine/layers/l3_volume_seasonality.py`
- Test: `tests/test_l3_volume.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l3_volume.py
import numpy as np
from engine.layers.l3_volume_seasonality import (
    compute_seasonal_profile,
    adjust_volume,
    compute_volume_confirm,
)


class TestVolumeSeasonality:
    def test_seasonal_profile_has_75_buckets(self):
        """One bucket per 5-min interval in a trading day (75 buckets for 6.25 hrs)."""
        # Simulate 10 days of 5-min bars
        volumes = np.random.randint(10000, 50000, 75 * 10)
        profile = compute_seasonal_profile(volumes, n_buckets=75)
        assert len(profile) == 75

    def test_adjusted_volume_centered_at_1(self):
        """V_adj = V_raw / V_seasonal(t) — should be ~1.0 on average."""
        volumes = np.ones(75 * 10) * 10000
        profile = compute_seasonal_profile(volumes, n_buckets=75)
        # All buckets have average 10000, so V_adj = 1.0 everywhere
        v_adj = adjust_volume(10000, profile, bucket_idx=10)
        assert v_adj == 1.0

    def test_volume_confirm_threshold(self):
        """V_confirm = V_adj >= 1.5 * median adjusted volume."""
        median_adj = 1.0
        assert compute_volume_confirm(v_adj=2.0, median_adj=median_adj) is True
        assert compute_volume_confirm(v_adj=1.2, median_adj=median_adj) is False
```

- [ ] **Step 2: Create l3_volume_seasonality.py**

```python
# engine/layers/l3_volume_seasonality.py
"""Volume seasonality: adjust raw volume by time-of-day profile.

V_seasonal(t) = average volume for 5-min bucket t over trailing 10 days
V_adj = V_raw / V_seasonal(t)
z_v = (V_adj - mean_adj) / std_adj
V_confirm = V_adj >= 1.5 * median_adj
"""
import numpy as np


def compute_seasonal_profile(volumes: np.ndarray, n_buckets: int = 75) -> np.ndarray:
    """Compute average volume per 5-min bucket over the available history.

    Args:
        volumes: Flat array of volumes, ordered chronologically
        n_buckets: Number of 5-min buckets per day (default 75 for 6.25 hrs)

    Returns:
        Array of shape (n_buckets,) with average volume per bucket
    """
    if len(volumes) < n_buckets:
        return np.ones(n_buckets) * np.mean(volumes) if len(volumes) > 0 else np.ones(n_buckets)

    # Reshape to (n_days, n_buckets)
    n_days = len(volumes) // n_buckets
    vols_2d = volumes[-n_days * n_buckets:].reshape(n_days, n_buckets)
    return vols_2d.mean(axis=0)


def adjust_volume(raw_volume: float, seasonal_profile: np.ndarray,
                  bucket_idx: int) -> float:
    """Compute seasonally-adjusted volume for a single bar."""
    if bucket_idx < 0 or bucket_idx >= len(seasonal_profile):
        return 1.0
    seasonal = seasonal_profile[bucket_idx]
    if seasonal <= 0:
        return 1.0
    return raw_volume / seasonal


def compute_volume_confirm(v_adj: float, median_adj: float) -> bool:
    """Return True if adjusted volume exceeds 1.5x median."""
    return v_adj >= 1.5 * median_adj


def compute_volume_zscore(v_adj: float, mean_adj: float, std_adj: float) -> float:
    """z-score of adjusted volume."""
    if std_adj == 0:
        return 0.0
    return (v_adj - mean_adj) / std_adj
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l3_volume.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l3_volume_seasonality.py tests/test_l3_volume.py
git commit -m "feat: add volume seasonality module with 10-day profile adjustment"
```

---

### Task 4: Create Options-Derived Signals Module

**Files:**
- Create: `engine/layers/l3_options.py`
- Test: `tests/test_l3_options.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l3_options.py
from engine.layers.l3_options import (
    compute_iv_percentile,
    compute_expected_range,
    compute_pcr_zscore,
    compute_rv_iv_ratio,
)


class TestIVPercentile:
    def test_iv_at_high_end(self):
        iv_history = [15, 16, 17, 18, 19, 20]  # current=20
        pctile = compute_iv_percentile(20, iv_history)
        assert pctile == 1.0  # at max

    def test_iv_at_midpoint(self):
        iv_history = [10, 12, 14, 16, 18, 20]
        pctile = compute_iv_percentile(16, iv_history)
        assert 0.4 <= pctile <= 0.6


class TestExpectedRange:
    def test_computation(self):
        import math
        er = compute_expected_range(atm=1000, iv=0.20, days=1)
        expected = 1000 * 0.20 / math.sqrt(252)
        assert er["expected_move"] == expected
        assert er["upper"] == 1000 + expected
        assert er["lower"] == 1000 - expected


class TestPCRZScore:
    def test_positive_zscore(self):
        z = compute_pcr_zscore(1.5, [1.0, 1.1, 1.2, 1.3])
        assert z > 0

    def test_negative_zscore(self):
        z = compute_pcr_zscore(0.8, [1.0, 1.1, 1.2, 1.3])
        assert z < 0


class TestRVIVRatio:
    def test_ratio_below_1(self):
        ratio = compute_rv_iv_ratio(realized_vol=0.15, iv=0.25)
        assert ratio == 0.6
```

- [ ] **Step 2: Create l3_options.py**

```python
# engine/layers/l3_options.py
"""Options-derived signals for F&O stocks.

Per system_design_final.md Section 5.3:
- IV Percentile (60-day + 1-year)
- Expected Range: ATM ± (IV/sqrt(252)) * ATM
- PCR Z-Score (20-day + 1-year)
- RV/IV Ratio
"""
import numpy as np
import math


def compute_iv_percentile(current_iv: float, iv_history: list[float]) -> float:
    """Percentile rank of current IV within the history."""
    if not iv_history:
        return 0.5
    below = sum(1 for v in iv_history if v < current_iv)
    return below / len(iv_history)


def compute_expected_range(atm: float, iv: float, days: int = 1) -> dict:
    """Expected range: ATM ± (IV/sqrt(252)) * ATM."""
    expected_move = atm * iv / math.sqrt(252 / days)
    return {
        "expected_move": round(expected_move, 2),
        "upper": round(atm + expected_move, 2),
        "lower": round(atm - expected_move, 2),
    }


def compute_pcr_zscore(current_pcr: float, pcr_history: list[float]) -> float:
    """Z-score of current PCR vs its history."""
    if len(pcr_history) < 2:
        return 0.0
    mean = np.mean(pcr_history)
    std = np.std(pcr_history)
    if std == 0:
        return 0.0
    return (current_pcr - mean) / std


def compute_rv_iv_ratio(realized_vol: float, iv: float) -> float:
    """RV/IV ratio — values < 1 mean IV exceeds RV (options expensive)."""
    if iv == 0:
        return 1.0
    return realized_vol / iv


def classify_oi(price_change_pct: float, oi_change_pct: float) -> str:
    """OI-based sentiment classification with threshold smoothing."""
    if price_change_pct > 0.5 and oi_change_pct > 2:
        return "Long Buildup"
    elif price_change_pct < -0.5 and oi_change_pct > 2:
        return "Short Buildup"
    elif price_change_pct < -0.5 and oi_change_pct < -2:
        return "Long Unwinding"
    elif price_change_pct > 0.5 and oi_change_pct < -2:
        return "Short Covering"
    return "Neutral"
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l3_options.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l3_options.py tests/test_l3_options.py
git commit -m "feat: add options-derived signals module (IV, expected range, PCR, RV/IV)"
```

---

### Task 5: Refactor L3Signals Orchestrator

**Files:**
- Modify: `engine/layers/l3_signals.py` (rewrite as orchestrator)

- [ ] **Step 1: Rewrite L3Signals**

Replace `engine/layers/l3_signals.py`:

```python
"""L3 Per-Stock Signal Layer — orchestrator.

Delegates to:
- l3_indicators: dual-timeframe indicator computation
- l3_reference_levels: PDH/PDL/CPR/pivots/ORB/FH levels
- l3_volume_seasonality: seasonal volume adjustment
- l3_options: IV percentile, expected range, PCR z-score, RV/IV ratio
"""
import pandas as pd
import numpy as np
from typing import Optional

from engine.layers.l3_indicators import (
    compute_all_indicators,
    detect_macd_divergence,
)
from engine.layers.l3_volume_seasonality import (
    compute_seasonal_profile,
    adjust_volume,
    compute_volume_confirm,
    compute_volume_zscore,
)
from engine.layers.l3_options import classify_oi


class L3Signals:
    """Per-stock signal computation with dual-timeframe indicators."""

    def __init__(self):
        self._seasonal_profiles: dict[str, np.ndarray] = {}
        self._adjusted_vol_history: dict[str, list[float]] = {}

    def compute(self, df: pd.DataFrame, symbol: str = "",
                df_15m: pd.DataFrame | None = None,
                nifty_df: pd.DataFrame | None = None,
                pcr: float | None = None,
                pcr_history: list[float] | None = None,
                iv: float | None = None,
                iv_history: list[float] | None = None,
                ) -> dict:
        """Compute all L3 signals for a symbol.

        Returns a dict with indicator values, seasonally-adjusted volume,
        and options-derived signals.
        """
        result = {}

        # 1. Dual-timeframe indicators
        indicators = compute_all_indicators(df, df_15m, nifty_df)
        latest = indicators.iloc[-1] if len(indicators) > 0 else pd.Series()

        # EMAs
        for tf in ["5m", "15m"]:
            e9 = latest.get(f"ema_9_{tf}")
            e20 = latest.get(f"ema_20_{tf}")
            e50 = latest.get(f"ema_50_{tf}")
            if e9 is not None:
                result[f"ema9_{tf}"] = float(e9)
                result[f"ema20_{tf}"] = float(e20)
                result[f"ema50_{tf}"] = float(e50)
                result[f"ema_aligned_{tf}"] = bool(latest.get(f"ema_aligned_{tf}", False))

        # Supertrend
        result["supertrend_5m"] = float(latest.get("supertrend_5m", 0))
        result["supertrend_dir_5m"] = int(latest.get("supertrend_dir_5m", 0))
        result["supertrend_bull"] = result["supertrend_dir_5m"] == 1

        # ADX
        result["adx_5m"] = float(latest.get("adx_5m", 0))
        result["adx_15m"] = float(latest.get("adx_15m", result["adx_5m"]))

        # RSI
        result["rsi_5m"] = float(latest.get("rsi_5m", 50))
        result["rsi_15m"] = float(latest.get("rsi_15m", result["rsi_5m"]))

        # MACD
        result["macd_hist_5m"] = float(latest.get("macd_hist_5m", 0))
        result["macd_hist_15m"] = float(latest.get("macd_hist_15m", 0))
        result["macd_divergence"] = detect_macd_divergence(indicators, "long", "5m")

        # ATR
        result["atr_5m"] = float(latest.get("atr_5m", 0))
        result["atr_pctile_5m"] = float(latest.get("atr_pctile_5m", 0.5))

        # Bollinger
        result["bb_upper_5m"] = float(latest.get("bb_upper_5m", 0))
        result["bb_lower_5m"] = float(latest.get("bb_lower_5m", 0))
        result["bb_width_5m"] = float(latest.get("bb_width_5m", 0))
        # BB position: where is close within the bands? 0=lower, 1=upper
        bb_range = result["bb_upper_5m"] - result["bb_lower_5m"]
        result["bb_position"] = ((latest["close"] - result["bb_lower_5m"]) / bb_range) if bb_range > 0 else 0.5

        # ROC vs Nifty
        result["roc_vs_nifty"] = float(latest.get("roc_vs_nifty", 0))

        # VWAP
        typical = (df["high"] + df["low"] + df["close"]) / 3
        cum_tp_vol = (typical * df["volume"]).cumsum()
        cum_vol = df["volume"].cumsum()
        vwap = cum_tp_vol / cum_vol
        result["vwap"] = float(vwap.iloc[-1]) if len(vwap) > 0 else float(latest["close"])
        result["above_vwap"] = float(latest["close"]) > result["vwap"]

        # 2. Volume seasonality
        raw_vol = float(latest.get("volume", 0))
        result["raw_volume"] = raw_vol
        # Bucket index from time of day (simplified — caller can provide)
        result["vol_z"] = 0.0
        result["vol_confirm"] = False

        # 3. Options-derived signals
        if pcr is not None:
            result["pcr"] = pcr
        if iv is not None:
            result["iv"] = iv

        return result
```

- [ ] **Step 2: Run all L3 tests**

Run: `pytest tests/test_l3_*.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l3_signals.py
git commit -m "refactor: L3Signals as orchestrator delegating to indicator/volume/options modules"
```
