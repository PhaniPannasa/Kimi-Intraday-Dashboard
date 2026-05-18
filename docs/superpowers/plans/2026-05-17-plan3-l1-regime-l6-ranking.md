# L1 Regime Fix + L6 Ranking Hysteresis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix L1 Range-Bound reachability, cold-start 15-min EMA path, hardcoded output fields, breadth normalization, and advancer/decliner computation. Add L6 hysteresis enforcement with adaptive theta, 5-min movement window, and concentration metrics.

**Architecture:** L1 gets a slope-threshold band for Range-Bound detection, a cold-start path that switches from 15-min to 5-min bars at 10:45, proper breadth normalization, and dynamic computation of previously-hardcoded fields. L6 gains a rank history buffer (last 5 minutes), adaptive theta from score-gap stddev, and concentration metric computation.

**Tech Stack:** Python 3.11, Polars, NumPy

---

## File Structure

```
engine/layers/
├── l1_market_context.py   # MODIFY: regime classifier, breadth, cold-start, hardcoded fields
├── l6_ranking.py          # MODIFY: hysteresis enforcement, adaptive theta, concentration
engine/models/
├── frames.py              # MODIFY: add concentration metrics to MarketContextFrame (optional)
tests/
├── test_l1_regime.py      # CREATE: regime classifier tests
├── test_l1_breadth.py     # CREATE: breadth computation tests
├── test_l6_ranking.py     # MODIFY: hysteresis + concentration tests
```

---

### Task 1: Fix L1 Regime Classifier — Range-Bound Reachability

**Files:**
- Modify: `engine/layers/l1_market_context.py:15-39`
- Test: `tests/test_l1_regime.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l1_regime.py
import numpy as np
import polars as pl
from engine.layers.l1_market_context import classify_regime
from models.enums import Regime


def make_nifty(slope_points: list[float], vol_z: float = 0.6) -> pl.DataFrame:
    """Build a synthetic Nifty DF with 100 bars and controlled slope/vol."""
    n = 100
    close = np.array(slope_points)
    # Ensure we have n bars: repeat the last pattern
    if len(close) < n:
        close = np.concatenate([np.full(n - len(close), close[0]), close])
    return pl.DataFrame({"close": close[-n:]})


class TestRegimeClassifier:
    def test_range_bound_when_slope_near_zero(self):
        """Slope within ±0.0003 band AND vol_z < 0.5 → RANGE_BOUND"""
        # Flat prices: all bars at 100 → slope ≈ 0, vol_z ≈ 0
        df = pl.DataFrame({"close": [100.0] * 100})
        regime, conf = classify_regime(df)
        assert regime == Regime.RANGE_BOUND.value

    def test_trending_up_with_high_vol(self):
        """Clear uptrend + high vol → TRENDING_UP with high confidence"""
        close = np.linspace(100, 110, 100) + np.random.normal(0, 0.5, 100)
        df = pl.DataFrame({"close": close})
        regime, conf = classify_regime(df)
        assert regime == Regime.TRENDING_UP.value

    def test_trending_down_clear_downtrend(self):
        """Clear downtrend → TRENDING_DOWN"""
        close = np.linspace(110, 100, 100) + np.random.normal(0, 0.3, 100)
        df = pl.DataFrame({"close": close})
        regime, conf = classify_regime(df)
        assert regime == Regime.TRENDING_DOWN.value

    def test_small_slope_low_vol_is_range_bound(self):
        """Realistic sideways: small oscillations, no strong trend"""
        close = 100 + np.sin(np.linspace(0, 6 * np.pi, 100)) * 0.5
        df = pl.DataFrame({"close": close})
        regime, conf = classify_regime(df)
        # Should classify as RANGE_BOUND (not trending)
        assert regime == Regime.RANGE_BOUND.value

    def test_confidence_is_between_0_and_1(self):
        df = pl.DataFrame({"close": np.linspace(100, 105, 100)})
        _, conf = classify_regime(df)
        assert 0.0 <= conf <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_l1_regime.py -v`
Expected: FAIL (Range-Bound tests fail — slope almost never exactly 0)

- [ ] **Step 3: Implement fixed regime classifier**

```python
def classify_regime(nifty_df: pl.DataFrame) -> tuple:
    """3-state regime classifier with slope threshold band for Range-Bound.

    Returns (regime_value, confidence).
    Range-Bound is reachable when abs(slope) < SLOPE_THRESHOLD (not exact 0).
    """
    SLOPE_THRESHOLD = 0.0003  # near-zero slope → sideways
    VOL_Z_THRESHOLD = 0.5

    if len(nifty_df) < 50:
        return Regime.RANGE_BOUND.value, 0.5

    returns = nifty_df["close"].pct_change()
    vol = compute_realized_vol(returns, 20)
    vol_baseline = vol.rolling_mean(60 * 75)
    vol_z = (vol - vol_baseline) / vol_baseline.rolling_std(60 * 75)

    ema50 = compute_ema(nifty_df["close"], 50)
    slope = ema50.diff(5)

    latest_vol_z = vol_z.tail(1).to_list()[0] or 0
    latest_slope = slope.tail(1).to_list()[0] or 0

    # Range-Bound: slope within threshold band (not exact zero)
    if abs(latest_slope) < SLOPE_THRESHOLD:
        return Regime.RANGE_BOUND.value, 0.6

    if latest_slope > 0:
        confidence = 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
        return Regime.TRENDING_UP.value, confidence
    else:
        confidence = 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
        return Regime.TRENDING_DOWN.value, confidence
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_l1_regime.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l1_market_context.py tests/test_l1_regime.py
git commit -m "fix: make Range-Bound regime reachable with slope threshold band"
```

---

### Task 2: Add Cold-Start 15-min EMA Path

**Files:**
- Modify: `engine/layers/l1_market_context.py` (`L1MarketContext.compute()`)

- [ ] **Step 1: Write the test**

```python
# tests/test_l1_regime.py (add to existing file)
class TestColdStart:
    def test_uses_15min_bars_before_1045(self):
        """Before 10:45 IST, use 9-bar EMA on 15-min bars."""
        from engine.layers.l1_market_context import get_cold_start_ema
        # Simulate 15-min bars from 9:15 to 10:00 (4 bars)
        df_15m = pl.DataFrame({"close": [100.0, 101.0, 100.5, 102.0]})
        ema = get_cold_start_ema(df_15m)
        # Should use 15-min bars with span=9 (or fewer if not enough bars)
        assert len(ema) == len(df_15m)

    def test_switches_to_5min_after_1045(self):
        """After 10:45 IST, use 50-bar EMA on 5-min bars."""
        from engine.layers.l1_market_context import should_use_cold_start
        from datetime import time
        assert not should_use_cold_start(time(10, 46))
        assert should_use_cold_start(time(9, 20))
```

- [ ] **Step 2: Implement cold-start logic**

```python
from datetime import time

COLD_START_END = time(10, 45)  # Switch to primary 50-bar 5-min at 10:45 AM


def should_use_cold_start(current_time: time) -> bool:
    """Return True if we're in the cold-start window (9:15-10:45)."""
    return current_time < COLD_START_END


def get_cold_start_ema(df_15m: pl.DataFrame) -> pl.Series:
    """9-bar EMA on 15-min bars for cold-start (first 90 min of session)."""
    span = min(9, len(df_15m))
    if span < 2:
        return df_15m["close"]
    return compute_ema(df_15m["close"], span)


def get_primary_ema(df_5m: pl.DataFrame) -> pl.Series:
    """50-bar EMA on 5-min bars (primary system, after 10:45)."""
    return compute_ema(df_5m["close"], 50)
```

Update `classify_regime` to accept optional `use_cold_start` + `df_15m`:

```python
def classify_regime(nifty_df: pl.DataFrame, df_15m: pl.DataFrame | None = None,
                    use_cold_start: bool = False) -> tuple:
    SLOPE_THRESHOLD = 0.0003
    VOL_Z_THRESHOLD = 0.5

    if use_cold_start and df_15m is not None and len(df_15m) >= 2:
        ema_series = get_cold_start_ema(df_15m)
        slope = ema_series.diff(1)  # bar-over-bar for 15-min
    else:
        if len(nifty_df) < 50:
            return Regime.RANGE_BOUND.value, 0.5
        ema_series = get_primary_ema(nifty_df)
        slope = ema_series.diff(5)

    returns = nifty_df["close"].pct_change() if len(nifty_df) >= 2 else pl.Series("", [0.0])
    vol = compute_realized_vol(returns, 20)
    vol_baseline = vol.rolling_mean(60 * 75)
    vol_z = (vol - vol_baseline) / vol_baseline.rolling_std(60 * 75)

    latest_vol_z = vol_z.tail(1).to_list()[0] or 0
    latest_slope = slope.tail(1).to_list()[0] or 0

    if abs(latest_slope) < SLOPE_THRESHOLD:
        return Regime.RANGE_BOUND.value, 0.6
    if latest_slope > 0:
        return Regime.TRENDING_UP.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
    return Regime.TRENDING_DOWN.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l1_regime.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l1_market_context.py tests/test_l1_regime.py
git commit -m "feat: add cold-start 15-min EMA path for first 90 min of session"
```

---

### Task 3: Fix Breadth Computation — Normalization + PDC-Based Advancer/Decliner

**Files:**
- Modify: `engine/layers/l1_market_context.py:54-83`
- Test: `tests/test_l1_breadth.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l1_breadth.py
import polars as pl
from engine.layers.l1_market_context import compute_breadth
from models.enums import Breadth

def make_stock_df(close: float, vwap: float, prev_close: float = 100.0):
    """Single-bar stock dataframe."""
    return pl.DataFrame({"close": [close], "vwap": [vwap], "prev_close": [prev_close]})


class TestBreadthNormalization:
    def test_normalized_ad_ratio_bounded(self):
        """A/D ratio should be normalized, not raw divison."""
        stocks = {}
        for i in range(80):
            stocks[f"S{i}"] = make_stock_df(105, 102, 100)  # advancers
        for i in range(80, 100):
            stocks[f"S{i}"] = make_stock_df(95, 98, 100)    # decliners

        breadth = compute_breadth(stocks)
        # With 80/20 advancers/decliners, raw ratio=4, normalized should ~0.94
        # B = 0.5*0.8 + 0.25*0.94 + 0.25*0.8 = 0.4+0.235+0.2 = 0.835 > 0.60
        assert breadth == Breadth.STRONG

    def test_balanced_day_is_mixed(self):
        stocks = {}
        for i in range(50):
            stocks[f"S{i}"] = make_stock_df(105, 102, 100)
        for i in range(50, 100):
            stocks[f"S{i}"] = make_stock_df(95, 98, 100)
        breadth = compute_breadth(stocks)
        assert breadth == Breadth.MIXED

    def test_bearish_day_is_weak(self):
        stocks = {}
        for i in range(20):
            stocks[f"S{i}"] = make_stock_df(105, 102, 100)
        for i in range(20, 100):
            stocks[f"S{i}"] = make_stock_df(95, 98, 100)
        breadth = compute_breadth(stocks)
        assert breadth == Breadth.WEAK

    def test_hl_ratio_is_new_high_vs_new_low(self):
        """H/L ratio should be (new highs)/(new lows), NOT advancer percentage."""
        # This verifies the computation, not just the label
        stocks = {}
        # 10 stocks hitting new session highs, 5 hitting new lows
        for i in range(10):
            stocks[f"H{i}"] = pl.DataFrame({
                "close": [110, 112, 115], "vwap": [109, 111, 113],
                "prev_close": [100, 100, 100]
            })
        for i in range(5):
            stocks[f"L{i}"] = pl.DataFrame({
                "close": [95, 93, 90], "vwap": [96, 94, 92],
                "prev_close": [100, 100, 100]
            })
        for i in range(85):
            stocks[f"M{i}"] = make_stock_df(102, 101, 100)

        breadth = compute_breadth(stocks)
        # H/L = 10/5 = 2.0, normalized via ratio → bounded
        # Should produce valid breadth without blowing up
        assert breadth in (Breadth.STRONG, Breadth.MIXED, Breadth.WEAK)
```

- [ ] **Step 2: Implement fixed breadth computation**

```python
def compute_breadth(stock_data: dict) -> Breadth:
    """Compute market breadth with normalized A/D and H/L ratios.

    B = 0.5 * VWAP_pct + 0.25 * A_D_norm + 0.25 * H_L_norm
    where A_D_norm and H_L_norm are bounded to [0, 1].
    """
    above_vwap = 0
    advancers = 0
    decliners = 0
    new_highs = 0
    new_lows = 0
    total = len(stock_data)

    if total == 0:
        return Breadth.MIXED

    for df in stock_data.values():
        if len(df) == 0:
            continue
        latest = df.tail(1)
        close_val = latest["close"].to_list()[0]
        vwap_val = latest["vwap"].to_list()[0]

        if close_val > vwap_val:
            above_vwap += 1

        # Advancer/decliner vs previous close (PDC), not session-open
        prev_close = latest["prev_close"].to_list()[0] if "prev_close" in latest.columns else df["close"].head(1).to_list()[0]
        if close_val > prev_close:
            advancers += 1
        elif close_val < prev_close:
            decliners += 1

        # New high / new low: highest/lowest in session vs recent bars
        session_high = df["close"].max()
        session_low = df["close"].min()
        if close_val >= session_high and len(df) > 1:
            new_highs += 1
        if close_val <= session_low and len(df) > 1:
            new_lows += 1

    vwap_pct = above_vwap / total

    # A/D ratio normalized: ad_ratio = advancers / (advancers + decliners)
    total_ad = advancers + decliners
    ad_norm = advancers / total_ad if total_ad > 0 else 0.5

    # H/L ratio normalized: hl_norm = new_highs / (new_highs + new_lows)
    total_hl = new_highs + new_lows
    hl_norm = new_highs / total_hl if total_hl > 0 else 0.5

    b = 0.5 * vwap_pct + 0.25 * ad_norm + 0.25 * hl_norm

    if b > 0.60:
        return Breadth.STRONG
    elif b < 0.40:
        return Breadth.WEAK
    return Breadth.MIXED
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l1_breadth.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l1_market_context.py tests/test_l1_breadth.py
git commit -m "fix: normalize breadth A/D and H/L ratios, use PDC for advancer/decliner"
```

---

### Task 4: Populate Hardcoded L1 Output Fields

**Files:**
- Modify: `engine/layers/l1_market_context.py` (`L1MarketContext.compute()`)

- [ ] **Step 1: Write the test**

```python
# tests/test_l1_regime.py (add)
class TestOutputFields:
    def test_volatility_qualifier_not_hardcoded(self):
        """volatility_qualifier should reflect actual vol_z vs threshold."""
        from engine.layers.l1_market_context import classify_volatility_qualifier
        assert classify_volatility_qualifier(0.6) == "Normal"
        assert classify_volatility_qualifier(1.2) == "Volatile"

    def test_vix_trajectory_not_hardcoded(self):
        from engine.layers.l1_market_context import classify_vix_trajectory
        # Rising: last 5 VIX values trending up
        assert classify_vix_trajectory([15, 16, 17, 18, 19]) == "Rising"
        assert classify_vix_trajectory([19, 18, 17, 16, 15]) == "Falling"
        assert classify_vix_trajectory([15, 16, 15, 16, 15]) == "Stable"

    def test_time_bucket_from_clock(self):
        from engine.layers.l1_market_context import get_time_bucket
        from datetime import time
        assert get_time_bucket(time(9, 20)) == "Opening Shock"
        assert get_time_bucket(time(10, 0)) == "Trend Establishment"
        assert get_time_bucket(time(12, 30)) == "Lunch"
        assert get_time_bucket(time(14, 0)) == "Afternoon Recovery"
        assert get_time_bucket(time(15, 0)) == "Closing Hour"
```

- [ ] **Step 2: Implement dynamic field computation**

```python
def classify_volatility_qualifier(vol_z: float) -> str:
    """vol_z > 0.8 → Volatile, else Normal."""
    return "Volatile" if abs(vol_z) > 0.8 else "Normal"


def classify_vix_trajectory(vix_history: list[float], window: int = 5) -> str:
    """Classify VIX trajectory over the last `window` values."""
    if len(vix_history) < window:
        return "Stable"
    recent = vix_history[-window:]
    if recent[-1] > recent[0] * 1.05:
        return "Rising"
    elif recent[-1] < recent[0] * 0.95:
        return "Falling"
    return "Stable"


def get_time_bucket(current_time: time) -> str:
    """Map current IST time to session time bucket."""
    if current_time < time(9, 15):
        return "Pre-Open"
    elif current_time < time(9, 30):
        return "Opening Shock"
    elif current_time < time(10, 45):
        return "Trend Establishment"
    elif current_time < time(12, 0):
        return "Mid-Morning"
    elif current_time < time(13, 0):
        return "Lunch"
    elif current_time < time(14, 30):
        return "Afternoon Recovery"
    else:
        return "Closing Hour"
```

Update `L1MarketContext.compute()`:

```python
class L1MarketContext:
    def __init__(self):
        self.vix_history: list[float] = []

    def compute(self, nifty_df: pl.DataFrame, vix_value: float,
                stock_data: dict, df_15m: pl.DataFrame | None = None,
                premarket_bias: str = "Neutral",
                bank_nifty_divergence: float = 0.0,
                event_flag: str | None = None,
                current_time: time | None = None) -> MarketContextFrame:
        self.vix_history.append(vix_value)

        # Trim VIX history to trailing 90 days (~ 90 * 75 * 5min bars ≈ no, use length cap)
        if len(self.vix_history) > 90:
            self.vix_history = self.vix_history[-90:]

        now = current_time or datetime.now().time()
        use_cold = should_use_cold_start(now)

        regime, confidence = classify_regime(nifty_df, df_15m, use_cold)
        vix_band = classify_vix_band(vix_value, self.vix_history)
        breadth = compute_breadth(stock_data)

        # Compute vol_z for volatility qualifier
        returns = nifty_df["close"].pct_change() if len(nifty_df) >= 2 else pl.Series("", [0.0])
        vol = compute_realized_vol(returns, 20) if len(nifty_df) >= 20 else pl.Series("", [0.0])
        vol_z = (vol - vol.rolling_mean(60 * 75)) / vol.rolling_std(60 * 75) if len(nifty_df) >= 50 else pl.Series("", [0.0])
        latest_vol_z = vol_z.tail(1).to_list()[0] or 0.0

        return MarketContextFrame(
            regime=regime,
            regime_confidence=round(confidence, 2),
            volatility_qualifier=classify_volatility_qualifier(latest_vol_z),
            vix_band=vix_band.value,
            vix_trajectory=classify_vix_trajectory(self.vix_history),
            time_bucket=get_time_bucket(now),
            event_flag=event_flag,
            breadth=breadth.value,
            premarket_bias=premarket_bias,
            bank_nifty_divergence=bank_nifty_divergence,
        )
```

- [ ] **Step 3: Run all L1 tests**

Run: `pytest tests/test_l1_regime.py tests/test_l1_breadth.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l1_market_context.py tests/test_l1_regime.py
git commit -m "fix: compute all L1 output fields dynamically, remove hardcoded values"
```

---

### Task 5: L6 — Enforce Hysteresis with Adaptive Theta + 5-min Movement Window

**Files:**
- Modify: `engine/layers/l6_ranking.py`
- Modify: `tests/test_l6_ranking.py` (or create)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l6_hysteresis.py
from engine.layers.l6_ranking import L6Ranking, compute_adaptive_theta
from models.enums import RankMovement


class TestHysteresis:
    def test_entry_blocked_when_gap_below_theta(self):
        ranker = L6Ranking(top_n=25)
        # Pre-populate Top 25 with a known rank 25
        ranker.previous_ranks = {f"S{i}": i+1 for i in range(25)}
        # Rank 25 has score 80. Rank 26 has score 80.1. Theta = 2.0.
        # Gap = 0.1 < 2.0 → rank 26 should NOT enter
        stocks = [{"symbol": f"S{i}", "score": 90 - i} for i in range(25)]
        stocks.append({"symbol": "NEWCO", "score": 80.1})  # rank 26
        result = ranker.rank(stocks)
        symbols = [r.symbol for r in result]
        assert "NEWCO" not in symbols  # blocked by hysteresis

    def test_entry_allowed_when_gap_exceeds_theta(self):
        ranker = L6Ranking(top_n=25)
        ranker.previous_ranks = {f"S{i}": i+1 for i in range(25)}
        stocks = [{"symbol": f"S{i}", "score": 90 - i} for i in range(25)]
        stocks.append({"symbol": "NEWCO", "score": 85.0})  # gap = 5 > theta=2
        result = ranker.rank(stocks)
        symbols = [r.symbol for r in result]
        assert "NEWCO" in symbols  # allowed entry

    def test_exit_blocked_when_gap_below_theta(self):
        ranker = L6Ranking(top_n=25)
        ranker.previous_ranks = {f"S{i}": i+1 for i in range(25)}
        # Rank 25 has low score, but rank 26 gap is < theta
        stocks = [{"symbol": f"S{i}", "score": 90 - i} for i in range(25)]
        stocks.append({"symbol": "OUTSIDER", "score": stocks[24]["score"] + 0.5})
        result = ranker.rank(stocks)
        symbols = [r.symbol for r in result]
        # Rank 25 (S24) should persist if outsider gap < theta
        assert "S24" in symbols

    def test_movement_window_is_5_min(self):
        ranker = L6Ranking(top_n=25)
        # Simulate a rank that was at position 10 in previous minute
        # and is now at position 8 — should be UP (improved >= 2)
        ranker._rank_history["TEST"] = [(10, 0), (10, 1), (10, 2), (9, 3), (8, 4)]
        movement = ranker.compute_rank_movement("TEST", 8)
        assert movement in (RankMovement.UP, RankMovement.STABLE)


class TestAdaptiveTheta:
    def test_theta_from_score_gaps(self):
        # Scores: gaps between ranks 20-30
        scores = [85, 84, 83, 82, 81, 80, 79, 78, 77, 76, 75]
        theta = compute_adaptive_theta(scores)
        # sigma_gap = std of gaps ≈ ~0.0 (all gaps=1) → theta = max(2.0, 0)
        assert theta == 2.0

    def test_theta_increases_with_large_gaps(self):
        scores = [90, 85, 80, 75, 70, 60, 50, 40, 30, 20, 10]
        theta = compute_adaptive_theta(scores)
        # Gaps are large (5,5,5,5,10,10,10,10,10,10) → std_dev ≈ 2.5
        # theta = max(2.0, 0.25 * 2.5) ≈ max(2.0, 6.25) = 6.25
        assert theta > 2.0
```

- [ ] **Step 2: Implement hysteresis + adaptive theta**

```python
# engine/layers/l6_ranking.py (full rewrite)
import math
from typing import List
from models.frames import RankingEntry
from models.enums import RankMovement


def compute_adaptive_theta(scores_20_30: list[float]) -> float:
    """Adaptive hysteresis threshold from score gaps at ranks 20-30.

    theta = max(2.0, 0.25 * sigma_gap)
    where sigma_gap = stddev of score gaps between adjacent ranks 20-30.
    """
    if len(scores_20_30) < 2:
        return 2.0
    gaps = [abs(scores_20_30[i] - scores_20_30[i+1])
            for i in range(len(scores_20_30) - 1)]
    mean_gap = sum(gaps) / len(gaps)
    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
    sigma_gap = math.sqrt(variance)
    return max(2.0, 0.25 * sigma_gap)


class L6Ranking:
    def __init__(self, top_n: int = 25):
        self.top_n = top_n
        self.previous_ranks: dict[str, int] = {}
        self._rank_history: dict[str, list[tuple[int, int]]] = {}  # symbol → [(rank, tick_id), ...]
        self._tick_counter: int = 0
        self.theta: float = 2.0

    def compute_rank_movement(self, symbol: str, new_rank: int) -> RankMovement:
        """Movement over 5-minute window (5 ticks), not single-tick."""
        old_rank = self.previous_ranks.get(symbol)
        if old_rank is None:
            return RankMovement.NEW

        # Look back 5 ticks
        history = self._rank_history.get(symbol, [])
        rank_5_ticks_ago = old_rank
        current_tick = self._tick_counter
        for r, tick in reversed(history):
            if current_tick - tick >= 5:
                rank_5_ticks_ago = r
                break

        if new_rank <= rank_5_ticks_ago - 2:
            return RankMovement.UP
        if new_rank >= rank_5_ticks_ago + 2:
            return RankMovement.DOWN
        return RankMovement.STABLE

    def rank(self, scored_stocks: list) -> List[RankingEntry]:
        """Rank with hysteresis gate on entry/exit.

        1. Sort by score
        2. Compute adaptive theta from ranks 20-30 score gaps
        3. Apply hysteresis: entry requires score > rank_25_score + theta
           exit requires rank_26_score > rank_25_score + theta
        4. Track rank movement over 5-tick window
        """
        self._tick_counter += 1
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # Adaptive theta from scores around the boundary (20-30)
        boundary_scores = [s["score"] for s in scored_stocks[19:30]] if len(scored_stocks) >= 30 \
            else [s["score"] for s in scored_stocks[-11:]]
        self.theta = compute_adaptive_theta(boundary_scores)

        # Apply hysteresis gate
        top_n_candidates = scored_stocks[:self.top_n]
        if len(scored_stocks) > self.top_n:
            rank_25_score = top_n_candidates[-1]["score"]
            rank_26_score = scored_stocks[self.top_n]["score"]

            # Entry gate: rank 26 enters only if score > rank_25_score + theta
            if rank_26_score > rank_25_score + self.theta:
                top_n_candidates[-1] = scored_stocks[self.top_n]

            # Exit gate: rank 25 drops only if rank 26 exceeds it by theta
            elif rank_26_score > rank_25_score + self.theta:
                pass  # already handled by entry gate

        # Build ranking entries
        ranked = []
        for i, stock in enumerate(top_n_candidates):
            rank = i + 1
            symbol = stock["symbol"]
            movement = self.compute_rank_movement(symbol, rank)

            ranked.append(RankingEntry(
                symbol=symbol,
                instrument_key=stock.get("instrument_key", ""),
                score=stock["score"],
                setup_type=stock.get("setup_type", 1),
                confluence_score=stock.get("confluence_score", 0),
                net_rr=stock.get("net_rr", 0.0),
                actionability_tier=stock.get("actionability_tier", "Research-Only"),
                rank_movement=movement,
                liquidity_quality=stock.get("liquidity_quality", "Good"),
            ))

            # Track rank history
            if symbol not in self._rank_history:
                self._rank_history[symbol] = []
            self._rank_history[symbol].append((rank, self._tick_counter))
            # Keep last 10 entries
            if len(self._rank_history[symbol]) > 10:
                self._rank_history[symbol] = self._rank_history[symbol][-10:]

            self.previous_ranks[symbol] = rank

        return ranked
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l6_hysteresis.py tests/test_l6_ranking.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l6_ranking.py tests/test_l6_hysteresis.py
git commit -m "feat: enforce hysteresis with adaptive theta and 5-min movement window"
```

---

### Task 6: Add Concentration Metrics to L6

**Files:**
- Modify: `engine/layers/l6_ranking.py` (`rank()` method)

- [ ] **Step 1: Write the test**

```python
class TestConcentration:
    def test_sector_concentration(self):
        from engine.layers.l6_ranking import compute_concentration
        sectors = ["Bank"] * 10 + ["IT"] * 5 + ["Auto"] * 3 + ["FMCG"] * 3 + ["Metal"] * 4
        metrics = compute_concentration(scores=list(range(25)), sectors=sectors)
        assert metrics["sector_concentration"] == 10  # max count = Bank=10
        assert metrics["is_theme_day"] is True       # > 8 = theme day

    def test_score_spread(self):
        from engine.layers.l6_ranking import compute_concentration
        scores = [90] + [85] * 23 + [80]
        metrics = compute_concentration(scores=scores, sectors=["A"] * 25)
        assert metrics["score_spread"] == 10
        assert metrics["is_high_conviction"] is False  # <= 20
```

- [ ] **Step 2: Implement concentration metrics**

```python
def compute_concentration(scores: list[float], sectors: list[str]) -> dict:
    """Compute informational concentration metrics."""
    from collections import Counter
    sector_counts = Counter(sectors)
    max_sector_count = max(sector_counts.values()) if sector_counts else 0

    score_spread = max(scores) - min(scores) if scores else 0

    return {
        "sector_concentration": max_sector_count,
        "is_theme_day": max_sector_count > 8,
        "score_spread": score_spread,
        "is_high_conviction": score_spread > 20,
    }
```

Add to `L6Ranking.rank()` return or as a separate method. Expose via `rank()` return value as a second element:

```python
def rank(self, scored_stocks: list) -> tuple[List[RankingEntry], dict]:
    # ... existing ranking logic ...
    sectors = [s.get("sector", "Unknown") for s in top_n_candidates]
    scores = [s["score"] for s in top_n_candidates]
    metrics = compute_concentration(scores, sectors)
    return ranked, metrics
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l6_hysteresis.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l6_ranking.py tests/test_l6_hysteresis.py
git commit -m "feat: add concentration metrics to L6 ranking output"
```
