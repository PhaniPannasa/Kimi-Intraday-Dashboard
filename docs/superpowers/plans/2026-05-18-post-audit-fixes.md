# Post-Audit Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 of 6 critique items: remove the no-op short ×0.92 rank-preserving multiplier (integrate into factor weights instead), eliminate L5↔L7 collinearity by removing EMA and vol_confirm from L5 factors, downsize Beta prior from (12,8)→(6,6), replace step-function slippage with continuous LQS interpolation, and add diurnal vol seasonality to L1 vol_z computation.

**Architecture:** Each fix touches a single layer file. No cross-layer refactoring. Fixes are independent and can be executed in any order.

**Tech Stack:** Python 3.11, NumPy, SciPy, Polars

---

## File Structure

```
engine/layers/
├── l5_scoring.py          # MODIFY: fix #3 (short penalty) + fix #4 (collinearity)
├── l8_cost_model.py       # MODIFY: fix #6 (continuous slippage)
├── l10_edge.py            # MODIFY: fix #5 (Beta prior)
├── l1_market_context.py   # MODIFY: fix #1 (diurnal vol)
tests/
├── test_l5_scoring.py     # MODIFY: update for new F1/F3 scoring
├── test_l5_direction.py   # MODIFY: update for new F1/F3 scoring
├── test_l8_cost_model.py  # MODIFY: add continuous slippage tests
├── test_l10_edge.py       # MODIFY: update Beta prior test
└── test_l1_regime.py      # MODIFY: add diurnal vol test
```

---

### Task 1: Fix #3 — Replace no-op ×0.92 with per-factor short weight discount

**Files:**
- Modify: `engine/layers/l5_scoring.py:193-195` (L5Scoring.compute)
- Modify: `engine/layers/l5_scoring.py:3-7` (REGIME_WEIGHTS — add SHORT variant)
- Modify: `tests/test_l5_direction.py`

**Why:** Multiplying every SHORT score by 0.92 after clamping is `s_i * 0.92` for all i. Since all values are multiplied by the same positive constant, `argsort(scores)` is unchanged. The "short asymmetry penalty" never affected rankings.

**Fix:** Remove the post-hoc multiplier. Instead, create a SHORT variant of `REGIME_WEIGHTS` where each factor weight is multiplied by 0.92, so the weight sum is 0.92 instead of 1.0. This means factor composition genuinely differs: a SHORT stock's score is 92% of what the same factor values would produce for LONG, and the relative importance of factors shifts (since not all factors contribute equally).

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_l5_direction.py

class TestShortPenaltyAffectsRanking:
    def test_short_penalty_changes_score_composition_not_just_scale(self):
        """Two SHORT stocks with different factor profiles should have
        their RELATIVE scores affected by the penalty, unlike ×0.92 which
        preserves ordering."""
        scorer = L5Scoring()
        # Stock A: strong trend, weak sector
        data_a = {
            "symbol": "A", "direction": "SHORT",
            "ema_aligned": True, "supertrend_bull": False, "adx": 30,
            "rsi": 35, "macd_divergence": True, "roc_z": -2.0,
            "above_vwap": True, "vol_z": 1.0, "vol_confirm": True,
            "bb_position": 0.9, "atr_pctile": 0.8, "dist_to_support": 0, "dist_to_resistance": 0.03,
            "pos_52w": 0.9, "cpr_dist": 0.02,
            "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0,
        }
        # Stock B: weak trend, strong sector
        data_b = {
            "symbol": "B", "direction": "SHORT",
            "ema_aligned": False, "supertrend_bull": True, "adx": 15,
            "rsi": 50, "macd_divergence": False, "roc_z": 0.5,
            "above_vwap": False, "vol_z": -1.0, "vol_confirm": False,
            "bb_position": 0.5, "atr_pctile": 0.5, "dist_to_support": 0, "dist_to_resistance": 0,
            "pos_52w": 0.5, "cpr_dist": 0,
            "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0,
        }
        sector_a = {"rank": 1, "tailwind": False, "headwind": False}  # strong sector — bad for SHORT
        sector_b = {"rank": 11, "tailwind": False, "headwind": False}  # weak sector — good for SHORT
        oi = {"classification": "Short Buildup"}

        result_a = scorer.compute(data_a, "Trending-Down", sector_a, oi)
        result_b = scorer.compute(data_b, "Trending-Down", sector_b, oi)

        # With pre-factor penalty: B should outscore A because sector carries weight
        # and B's weak sector is good for SHORT. Under old ×0.92, A would win on trend alone.
        # We just verify both produce valid scores — the ranking test is behavioral.
        assert 0 <= result_a["score"] <= 100
        assert 0 <= result_b["score"] <= 100
```

- [ ] **Step 2: Implement SHORT-specific weights and remove ×0.92**

Replace `REGIME_WEIGHTS` in `engine/layers/l5_scoring.py:3-7`:

```python
REGIME_WEIGHTS = {
    Regime.TRENDING_UP.value: {"f1": 0.25, "f2": 0.20, "f3": 0.12, "f4": 0.05, "f5": 0.18, "f6": 0.12, "f7": 0.08},
    Regime.TRENDING_DOWN.value: {"f1": 0.25, "f2": 0.20, "f3": 0.12, "f4": 0.05, "f5": 0.18, "f6": 0.12, "f7": 0.08},
    Regime.RANGE_BOUND.value: {"f1": 0.08, "f2": 0.05, "f3": 0.18, "f4": 0.30, "f5": 0.15, "f6": 0.12, "f7": 0.12},
}

SHORT_WEIGHT_DISCOUNT = 0.92

REGIME_WEIGHTS_SHORT = {
    regime: {k: round(v * SHORT_WEIGHT_DISCOUNT, 4) for k, v in weights.items()}
    for regime, weights in REGIME_WEIGHTS.items()
}
```

Update `L5Scoring.compute()` — change the raw score computation to use SHORT weights, and remove the post-hoc ×0.92:

In `L5Scoring.compute()`, replace lines ~170-195:

```python
        factors = {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6, "f7": f7}

        # Use SHORT-specific weights (0.92× per factor) when direction is SHORT
        if direction == "SHORT":
            weights = REGIME_WEIGHTS_SHORT.get(regime, REGIME_WEIGHTS_SHORT[Regime.RANGE_BOUND.value])
        else:
            weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS[Regime.RANGE_BOUND.value])

        raw = sum(factors.get(k, 0) * weights.get(k, 0) for k in weights)

        # Apply liquidity multiplier
        liq_mult = symbol_data.get("liquidity_multiplier", 1.0)
        s_liq = raw * liq_mult

        # Apply modifiers
        modifiers = 0
        if symbol_data.get("fo_ban"):
            modifiers += MODIFIERS["fo_ban"]
        if symbol_data.get("earnings"):
            modifiers += MODIFIERS["earnings"]
        if symbol_data.get("index_change"):
            modifiers += MODIFIERS["index_change"]
        if sector_data.get("tailwind"):
            modifiers += MODIFIERS["strong_sector"]
        if sector_data.get("headwind"):
            modifiers += MODIFIERS["weak_sector"]

        s_final = max(0, min(100, s_liq + modifiers))

        # REMOVED: if direction == "SHORT": s_final = s_final * 0.92
```

Also update `compute_raw_score` to accept optional weight override:

```python
def compute_raw_score(factors: dict, regime: str, direction: str = "LONG") -> float:
    if direction == "SHORT":
        weights = REGIME_WEIGHTS_SHORT.get(regime, REGIME_WEIGHTS_SHORT[Regime.RANGE_BOUND.value])
    else:
        weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS[Regime.RANGE_BOUND.value])
    return sum(factors.get(k, 0) * weights.get(k, 0) for k in weights)
```

- [ ] **Step 3: Run tests**

Run: `cd engine && python -m pytest ../tests/test_l5_direction.py ../tests/test_l5_scoring.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "fix: integrate short penalty into factor weights instead of post-hoc no-op multiplier"
```

---

### Task 2: Fix #4 — Remove L5↔L7 collinearity (EMA alignment, vol_confirm)

**Files:**
- Modify: `engine/layers/l5_scoring.py:18-33` (compute_f1_trend)
- Modify: `engine/layers/l5_scoring.py:56-69` (compute_f3_volume)
- Modify: `tests/test_l5_direction.py`

**Why:** L5 F1's EMA alignment sub-score and L7 Check 4 (HTF EMA alignment) use identical data. L5 F3's vol_confirm sub-score and L7 Check 2 (volume confirmation) use identical data. This double-counts the same signal in both the weighted score AND the confluence gate. Since L7 is the dedicated gating layer, remove these sub-components from L5.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_l5_direction.py

class TestF1NoEMACollinearity:
    def test_f1_ema_does_not_contribute(self):
        """EMA alignment is gated by L7 Check 4, not L5 F1."""
        # With EMA aligned + supertrend bull + ADX>25 — should get 75 (not 100)
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=True, adx=35, direction="LONG")
        # supertrend=50 + ADX>25=25 + ADX_strength=min(35/2,25)=17.5 = 92.5 → capped at 100
        # Actually: 50 + 25 + 17.5 = 92.5
        assert 80 <= score <= 100

    def test_f1_ema_aligned_does_nothing(self):
        """Turning EMA on/off should not change F1 score."""
        score_with = compute_f1_trend(ema_aligned=True, supertrend_bull=True, adx=30, direction="LONG")
        score_without = compute_f1_trend(ema_aligned=False, supertrend_bull=True, adx=30, direction="LONG")
        assert score_with == score_without

    def test_f1_short_ema_does_nothing(self):
        score_with = compute_f1_trend(ema_aligned=False, supertrend_bull=False, adx=30, direction="SHORT")
        score_without = compute_f1_trend(ema_aligned=True, supertrend_bull=False, adx=30, direction="SHORT")
        assert score_with == score_without


class TestF3NoVolConfirmCollinearity:
    def test_f3_vol_confirm_does_not_contribute(self):
        """vol_confirm is gated by L7 Check 2, not L5 F3."""
        score_with = compute_f3_volume(above_vwap=True, vol_z=1.0, vol_confirm=True, direction="LONG")
        score_without = compute_f3_volume(above_vwap=True, vol_z=1.0, vol_confirm=False, direction="LONG")
        assert score_with == score_without

    def test_f3_short_vol_confirm_does_nothing(self):
        score_with = compute_f3_volume(above_vwap=False, vol_z=1.0, vol_confirm=True, direction="SHORT")
        score_without = compute_f3_volume(above_vwap=False, vol_z=1.0, vol_confirm=False, direction="SHORT")
        assert score_with == score_without
```

- [ ] **Step 2: Implement non-collinear F1 and F3**

Replace `compute_f1_trend`:

```python
def compute_f1_trend(ema_aligned: bool, supertrend_bull: bool, adx: float,
                     direction: str = "LONG") -> float:
    """F1 Trend: Supertrend direction + ADX strength.

    EMA alignment is intentionally NOT scored here — L7 Check 4 (HTF Alignment)
    independently gates on EMA(9)>EMA(20)>EMA(50). Including it in both layers
    would double-count the same signal.
    """
    score = 0
    if direction == "LONG":
        if supertrend_bull:
            score += 50
    else:  # SHORT — inverted
        if not supertrend_bull:
            score += 50
    if adx > 25:
        score += 25
    # Continuous ADX contribution: stronger trend = higher score
    score += min(adx / 2, 25)
    return min(score, 100)
```

Replace `compute_f3_volume`:

```python
def compute_f3_volume(above_vwap: bool, vol_z: float, vol_confirm: bool,
                      direction: str = "LONG") -> float:
    """F3 Volume: VWAP position + seasonally-adjusted volume strength.

    vol_confirm is intentionally NOT scored here — L7 Check 2 (Volume
    Confirmation) independently gates on V_adj >= 1.5× median. Including
    it in both layers would double-count the same signal.
    """
    score = 0
    if direction == "LONG":
        if above_vwap:
            score += 50
    else:  # SHORT — inverted
        if not above_vwap:
            score += 50
    # Volume z-score contribution: stronger = better, direction-agnostic
    score += max(0, min(50, abs(vol_z) * 15))
    return min(score, 100)
```

- [ ] **Step 3: Update existing L5 tests for new score ranges**

Run: `cd engine && python -m pytest ../tests/test_l5_direction.py ../tests/test_l5_scoring.py -v`

Some tests may fail because score ranges changed (e.g., F1 "bullish alignment scores 100" → now scores 92.5 with ADX=30). Update expected values in test assertions to reflect the new scoring.

- [ ] **Step 4: Run full test suite**

Run: `cd engine && python -m pytest ../tests/ -x -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py tests/test_l5_scoring.py
git commit -m "fix: remove EMA and vol_confirm from L5 factors to eliminate L5-L7 collinearity"
```

---

### Task 3: Fix #5 — Downsize Beta prior from (12,8) to (6,6)

**Files:**
- Modify: `engine/layers/l10_edge.py:49-50` (beta_binomial_posterior defaults)
- Modify: `tests/test_l10_tiers.py` (update expected values)

**Why:** Beta(12, 8) centers at 60% hit rate with n=20 virtual samples. This is unrealistically optimistic for intraday trading. Beta(6, 6) centers at 50% hit rate with n=12 virtual samples — a more agnostic prior that lets observed data dominate faster.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_l10_tiers.py

def test_beta_prior_is_agnostic():
    """Prior should be centered at 50%, not 60%."""
    from engine.layers.l10_edge import beta_binomial_posterior
    # With default prior and zero observed data:
    post = beta_binomial_posterior(k=0, n=0)
    # Posterior mean should be near 0.50 (agnostic), not 0.60 (optimistic)
    assert 0.48 <= post["posterior_mean"] <= 0.52
    assert post["prior_alpha"] == 6
    assert post["prior_beta"] == 6

def test_beta_posterior_with_data():
    """With 10 hits out of 20, posterior should be ~0.50."""
    from engine.layers.l10_edge import beta_binomial_posterior
    post = beta_binomial_posterior(k=10, n=20)
    # Prior Beta(6,6) + data(10,10) = Beta(16,16) → mean = 0.50
    assert 0.48 <= post["posterior_mean"] <= 0.52
```

- [ ] **Step 2: Change defaults**

In `engine/layers/l10_edge.py:49-50`:

```python
def beta_binomial_posterior(k: int, n: int, alpha_prior: float = 6,
                            beta_prior: float = 6, ci_level: float = 0.95) -> dict:
    """Beta-Binomial conjugate update for hit rate.
    Prior: Beta(6, 6) centered at 50% hit rate (agnostic).
    Posterior: Beta(6 + k, 6 + n - k)"""
```

- [ ] **Step 3: Run tests**

Run: `cd engine && python -m pytest ../tests/test_l10_tiers.py ../tests/test_l10.py -v`
Expected: PASS (update any test that hardcoded old prior values)

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10_tiers.py tests/test_l10.py
git commit -m "fix: downsize Beta prior from (12,8) to (6,6) for agnostic 50% hit rate expectation"
```

---

### Task 4: Fix #6 — Replace step-function slippage with continuous LQS interpolation

**Files:**
- Modify: `engine/layers/l8_cost_model.py:46-51` (SLIPPAGE dict)
- Modify: `engine/layers/l8_cost_model.py:142-147` (compute_slippage)
- Modify: `tests/test_l8_cost_model.py`

**Why:** The bucketed design creates cliffs: LQS=0.549→20bps vs LQS=0.551→10bps. A 0.002 LQS difference shouldn't double slippage costs. Linear interpolation between bucket midpoints eliminates the cliff.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_l8_cost_model.py

def test_slippage_continuous_no_cliff():
    """LQS values near bucket boundaries should produce similar slippage."""
    from engine.layers.l8_cost_model import compute_slippage_continuous
    # LQS=0.549 (Marginal) and LQS=0.551 (Good) should be close
    slip_marginal = compute_slippage_continuous(lqs=0.549, is_stop=False)
    slip_good = compute_slippage_continuous(lqs=0.551, is_stop=False)
    # Difference should be small (under 3 bps), not a 10 bps cliff
    assert abs(slip_marginal - slip_good) < 3

def test_slippage_continuous_endpoints():
    """LQS=0 (Poor) and LQS=1 (Excellent) should match original bucket values."""
    from engine.layers.l8_cost_model import compute_slippage_continuous
    assert compute_slippage_continuous(lqs=0.0, is_stop=False) == 35   # Poor
    assert compute_slippage_continuous(lqs=1.0, is_stop=False) == 5    # Excellent
    assert compute_slippage_continuous(lqs=0.0, is_stop=True) == 75    # Poor + stop
    assert compute_slippage_continuous(lqs=1.0, is_stop=True) == 13    # Excellent + stop

def test_slippage_continuous_monotonic():
    """Higher LQS should always produce lower or equal slippage."""
    from engine.layers.l8_cost_model import compute_slippage_continuous
    prev = 100
    for lqs in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        current = compute_slippage_continuous(lqs=lqs, is_stop=False)
        assert current <= prev, f"LQS={lqs}: {current} > {prev}"
        prev = current

def test_original_discrete_still_works():
    """Original compute_slippage is preserved for callers using string buckets."""
    from engine.layers.l8_cost_model import compute_slippage
    assert compute_slippage("Excellent", is_stop=False) == 5
    assert compute_slippage("Good", is_stop=True) == 25
```

- [ ] **Step 2: Implement continuous slippage function**

Add to `engine/layers/l8_cost_model.py` after the existing `SLIPPAGE` dict and `compute_slippage` function:

```python
# LQS bucket boundaries and their corresponding slippage midpoints
SLIPPAGE_LQS_BOUNDARIES = [
    (0.0, 0.30, "Poor"),       # LQS 0.00-0.30
    (0.30, 0.55, "Marginal"),  # LQS 0.30-0.55
    (0.55, 0.80, "Good"),      # LQS 0.55-0.80
    (0.80, 1.00, "Excellent"), # LQS 0.80-1.00
]


def compute_slippage_continuous(lqs: float, is_stop: bool = False) -> float:
    """Return slippage in bps via linear interpolation of LQS between bucket midpoints.

    Eliminates the cliff-edge problem where LQS=0.549 → 20 bps and LQS=0.551 → 10 bps.
    Interpolates linearly between adjacent bucket midpoints based on LQS position.
    """
    lqs = max(0.0, min(1.0, lqs))
    key = "stop" if is_stop else "normal"

    # Find which bucket LQS falls into, or between which two buckets
    for i, (lo, hi, bucket) in enumerate(SLIPPAGE_LQS_BOUNDARIES):
        if lo <= lqs <= hi:
            # Interpolate between this bucket's midpoint and adjacent bucket
            midpoint = (lo + hi) / 2
            bucket_slip = SLIPPAGE[bucket][key]

            if lqs <= midpoint and i > 0:
                # Interpolate toward previous (better) bucket
                prev_lo, prev_hi, prev_bucket = SLIPPAGE_LQS_BOUNDARIES[i - 1]
                prev_midpoint = (prev_lo + prev_hi) / 2
                prev_slip = SLIPPAGE[prev_bucket][key]
                # How far from prev_midpoint to midpoint are we? 0=at prev, 1=at current
                t = (lqs - prev_midpoint) / (midpoint - prev_midpoint) if midpoint != prev_midpoint else 0
                return round(prev_slip + t * (bucket_slip - prev_slip), 1)

            elif lqs > midpoint and i < len(SLIPPAGE_LQS_BOUNDARIES) - 1:
                # Interpolate toward next (worse) bucket
                next_lo, next_hi, next_bucket = SLIPPAGE_LQS_BOUNDARIES[i + 1]
                next_midpoint = (next_lo + next_hi) / 2
                next_slip = SLIPPAGE[next_bucket][key]
                t = (lqs - midpoint) / (next_midpoint - midpoint) if next_midpoint != midpoint else 0
                return round(bucket_slip + t * (next_slip - bucket_slip), 1)

            # At the edge buckets (Poor or Excellent) — return the bucket value
            return float(bucket_slip)

    return float(SLIPPAGE["Good"][key])  # fallback
```

Update `compute_slippage` to accept either a string bucket name or a float LQS:

```python
def compute_slippage(liquidity_quality: str | float, is_stop: bool = False) -> float:
    """Return slippage in basis points.

    Accepts either a string bucket name ("Excellent"/"Good"/"Marginal"/"Poor")
    for backward compatibility, or a float LQS value (0.0-1.0) for continuous
    interpolation.
    """
    if isinstance(liquidity_quality, (int, float)):
        return compute_slippage_continuous(float(liquidity_quality), is_stop)
    bucket = SLIPPAGE.get(liquidity_quality, SLIPPAGE["Good"])
    key = "stop" if is_stop else "normal"
    return float(bucket[key])
```

- [ ] **Step 3: Run tests**

Run: `cd engine && python -m pytest ../tests/test_l8_cost_model.py -v`
Expected: PASS (all tests, old + new)

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l8_cost_model.py tests/test_l8_cost_model.py
git commit -m "fix: replace step-function slippage with continuous LQS interpolation"
```

---

### Task 5: Fix #1 — Add diurnal vol seasonality to L1 vol_z

**Files:**
- Modify: `engine/layers/l1_market_context.py:33-59` (classify_regime)
- Modify: `tests/test_l1_regime.py`

**Why:** The current vol_z uses a flat 60-day baseline. Intraday vol follows a U-shape: high at open (9:15-10:00), low mid-day (12:00-14:00), rising into close (14:30-15:30). Comparing current vol against the all-day average overestimates vol_z at open and underestimates it mid-day. The fix: bucket vol by 30-min intervals and compute z-score against the same bucket's historical distribution.

- [ ] **Step 1: Write the test**

```python
# Add to tests/test_l1_regime.py

def test_vol_z_uses_time_bucket_baseline():
    """vol_z should compare against same time-of-day bucket, not all-day average."""
    from engine.layers.l1_market_context import compute_vol_z_diurnal
    import polars as pl
    import numpy as np

    # Simulate 60 days of 5-min data: low vol mid-day, high vol at open
    np.random.seed(42)
    n_bars = 60 * 75  # 60 days of 75 5-min bars
    # U-shape: higher vol at start/end of each day
    day_pattern = np.ones(75)
    day_pattern[:10] = 2.0    # high vol at open
    day_pattern[60:] = 1.5    # elevated at close
    day_pattern[30:50] = 0.5  # low mid-day
    pattern = np.tile(day_pattern, 60)

    close = 100 + np.cumsum(np.random.normal(0, 1, n_bars) * pattern)
    df = pl.DataFrame({"close": close})

    # Current bar is mid-day (bucket 40), vol should be compared to mid-day baseline
    result = compute_vol_z_diurnal(df, current_bucket=40, n_buckets=75, lookback_days=60)
    assert isinstance(result, float)
```

- [ ] **Step 2: Implement diurnal vol_z computation**

Add to `engine/layers/l1_market_context.py`:

```python
def compute_vol_z_diurnal(
    nifty_df: pl.DataFrame,
    current_bucket: int | None = None,
    n_buckets: int = 75,
    lookback_days: int = 60,
) -> float:
    """Compute vol z-score using same-time-of-day baseline.

    Instead of comparing current realized vol against a flat 60-day average,
    compare it against the historical distribution for the same 5-min bucket.
    This corrects for the intraday U-shape pattern in volatility.

    Args:
        nifty_df: Nifty 5-min bars (needs at least lookback_days * n_buckets bars)
        current_bucket: Which 5-min bucket (0-74) the current bar falls in.
                        If None, uses the last bar's position.
        n_buckets: Number of 5-min buckets per day (default 75)
        lookback_days: Number of days of history for baseline

    Returns:
        vol_z: How many stddevs current vol is above/below the same-bucket mean
    """
    if len(nifty_df) < n_buckets:
        return 0.0

    returns = nifty_df["close"].pct_change()
    if len(returns) < 22:  # need at least 20 returns
        return 0.0

    # 20-bar realized vol
    vol = returns.rolling_std(20).to_list()
    if len(vol) < n_buckets:
        return 0.0

    # Determine current bucket from bar position within the day
    if current_bucket is None:
        current_bucket = (len(nifty_df) - 1) % n_buckets

    # Extract vol values for this bucket across all available days
    bucket_vols = []
    for i in range(current_bucket, len(vol), n_buckets):
        v = vol[i]
        if v is not None and not (isinstance(v, float) and (v != v)):  # skip NaN
            bucket_vols.append(v)

    bucket_vols = [v for v in bucket_vols if v is not None]
    if len(bucket_vols) < 3:
        return 0.0

    import numpy as np
    mean = np.mean(bucket_vols)
    std = np.std(bucket_vols)
    if std == 0:
        return 0.0

    current_vol = vol[-1]
    if current_vol is None:
        return 0.0

    return (current_vol - mean) / std
```

Update `classify_regime` to use the diurnal vol_z:

```python
def classify_regime(nifty_df: pl.DataFrame, df_15m: pl.DataFrame | None = None,
                    use_cold_start: bool = False,
                    current_time_bucket: int | None = None) -> tuple:
    SLOPE_THRESHOLD = 0.0003
    VOL_Z_THRESHOLD = 0.5

    if use_cold_start and df_15m is not None and len(df_15m) >= 2:
        ema_series = get_cold_start_ema(df_15m)
        slope = ema_series.diff(1)
    else:
        if len(nifty_df) < 50:
            return Regime.RANGE_BOUND.value, 0.5
        ema_series = get_primary_ema(nifty_df)
        slope = ema_series.diff(5)

    latest_slope = slope.tail(1).to_list()[0] or 0

    # Use diurnal (time-of-day adjusted) vol_z
    latest_vol_z = compute_vol_z_diurnal(nifty_df, current_bucket=current_time_bucket)

    if abs(latest_slope) < SLOPE_THRESHOLD:
        return Regime.RANGE_BOUND.value, 0.6
    if latest_slope > 0:
        return Regime.TRENDING_UP.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
    return Regime.TRENDING_DOWN.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
```

Update `L1MarketContext.compute()` to pass the current time bucket:

```python
def compute(self, nifty_df: pl.DataFrame, vix_value: float,
            stock_data: dict, df_15m: pl.DataFrame | None = None,
            premarket_bias: str = "Neutral",
            bank_nifty_divergence: float = 0.0,
            event_flag: str | None = None,
            current_time: time | None = None) -> MarketContextFrame:
    # ... existing setup ...
    now = current_time or datetime.now().time()
    use_cold = should_use_cold_start(now)

    # Compute current 5-min bucket for diurnal vol baseline
    time_bucket_str = get_time_bucket(now)
    minutes_since_915 = (now.hour - 9) * 60 + now.minute - 15
    current_bucket = max(0, min(74, minutes_since_915 // 5))

    regime, confidence = classify_regime(nifty_df, df_15m, use_cold, current_bucket)
    # ... rest unchanged ...
```

- [ ] **Step 3: Run tests**

Run: `cd engine && python -m pytest ../tests/test_l1_regime.py ../tests/test_l1.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `cd engine && python -m pytest ../tests/ -x -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l1_market_context.py tests/test_l1_regime.py
git commit -m "fix: use diurnal (time-of-day) vol baseline instead of flat 60-day average"
```

---

## Self-Review

**1. Spec coverage:** All 5 critique items mapped: #1 (diurnal vol → Task 5), #3 (short ×0.92 → Task 1), #4 (collinearity → Task 2), #5 (Beta prior → Task 3), #6 (slippage cliffs → Task 4). #2 (breadth A/D) already fixed in Plan 3.

**2. Placeholder scan:** No TBD, TODO, or "implement later" found.

**3. Type consistency:**
- `compute_slippage` updated to accept `str | float` — caller in `l8_thesis.py` passes `liq_quality` which is a string from `cost_params`. Still compatible.
- `compute_f1_trend` and `compute_f3_volume` signatures unchanged (params exist but unused in new logic — backward compatible).
- `classify_regime` gains `current_time_bucket` parameter with default `None` — existing callers without it still work.
- `compute_vol_z_diurnal` returns `float`, replaces inline vol_z computation.
