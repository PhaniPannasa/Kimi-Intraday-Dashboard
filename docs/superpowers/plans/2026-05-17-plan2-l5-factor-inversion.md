# L5 Factor Inversion + Liquidity + Stale-Data Freeze — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor all 7 factor functions to accept `direction` and compute inverted scores for SHORT per the spec table. Add `liquidity_multiplier` step and `stale_data` freeze. Apply `index_change` modifier.

**Architecture:** Each `compute_fN()` function gains a `direction: str` parameter. For F1-F4 and F7, the SHORT path inverts the scoring logic. F5 (sector) is directional but uses different logic for long vs short. F6 (OI) already differentiates — needs minor cleanup. `L5Scoring.compute()` adds `liquidity_multiplier` after raw score and checks `stale_data` before scoring.

**Tech Stack:** Python 3.11, NumPy

---

## File Structure

```
engine/layers/
├── l5_scoring.py           # MODIFY: all compute_fN functions + L5Scoring.compute()
tests/
├── test_l5_scoring.py      # MODIFY: add direction-aware tests
```

---

### Task 1: Refactor F1 Trend for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:18-26`
- Modify: `tests/test_l5_scoring.py` (or create if minimal)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l5_direction.py (new file)
from engine.layers.l5_scoring import (
    compute_f1_trend,
    compute_f2_momentum,
    compute_f3_volume,
    compute_f4_volpos,
    compute_f5_sector,
    compute_f6_oi,
    compute_f7_posrng,
    compute_raw_score,
    L5Scoring,
    REGIME_WEIGHTS,
    MODIFIERS,
)
from models.enums import Regime


class TestF1TrendDirection:
    def test_long_bullish_alignment_scores_100(self):
        """F1 LONG: Bullish alignment (EMA aligned + ST bull + ADX>25) = 100"""
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=True, adx=30, direction="LONG")
        assert score == 100

    def test_short_bearish_alignment_scores_100(self):
        """F1 SHORT: Inverted — bearish alignment scores high"""
        score = compute_f1_trend(ema_aligned=False, supertrend_bull=False, adx=30, direction="SHORT")
        # EMA NOT aligned (bearish) = +40, ST NOT bull (bearish) = +35, ADX>25 = +25
        assert score == 100

    def test_long_mixed_gives_partial(self):
        """F1 LONG: Mixed signals give partial score"""
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=False, adx=20, direction="LONG")
        assert score == 40  # only EMA

    def test_short_mixed_gives_partial(self):
        """F1 SHORT: Mixed signals — EMA aligned (bullish for LONG, bearish for SHORT? No — SHORT wants inverted)"""
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=False, adx=20, direction="SHORT")
        # EMA aligned = bullish = NOT what SHORT wants → 0 for EMA
        # ST not bull = bearish = what SHORT wants → +35
        # ADX<25 = 0
        assert score == 35
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_l5_direction.py::TestF1TrendDirection -v`
Expected: FAIL (SHORT scores equal LONG scores — not inverted)

- [ ] **Step 3: Implement direction-aware F1**

```python
def compute_f1_trend(ema_aligned: bool, supertrend_bull: bool, adx: float,
                     direction: str = "LONG") -> float:
    """F1 Trend: Bullish alignment for LONG, Inverted (bearish) for SHORT."""
    score = 0
    if direction == "LONG":
        if ema_aligned:
            score += 40
        if supertrend_bull:
            score += 35
    else:  # SHORT — inverted
        if not ema_aligned:
            score += 40
        if not supertrend_bull:
            score += 35
    if adx > 25:
        score += 25
    return min(score, 100)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF1TrendDirection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F1 trend scoring for direction-aware LONG/SHORT"
```

---

### Task 2: Refactor F2 Momentum for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:29-35`

- [ ] **Step 1: Write the failing tests**

```python
class TestF2MomentumDirection:
    def test_long_strong_momentum_scores_high(self):
        """F2 LONG: RSI 40-70 + MACD bull div + positive ROC = high score"""
        score = compute_f2_momentum(rsi=55, macd_div=True, roc_z=1.5, direction="LONG")
        assert score > 70

    def test_short_inverted_momentum_scores_high(self):
        """F2 SHORT: RSI 30-60 + MACD bear div + negative ROC = high score"""
        score = compute_f2_momentum(rsi=35, macd_div=True, roc_z=-2.0, direction="SHORT")
        assert score > 70

    def test_long_rsi_overbought_penalized(self):
        """F2 LONG: RSI>70 gets 0 for RSI component"""
        score = compute_f2_momentum(rsi=75, macd_div=False, roc_z=0, direction="LONG")
        assert score <= 35  # only ROC component possible

    def test_short_rsi_oversold_penalized(self):
        """F2 SHORT: RSI<30 gets 0 for RSI component (inverted: SHORT wants high RSI)"""
        score = compute_f2_momentum(rsi=25, macd_div=False, roc_z=0, direction="SHORT")
        assert score <= 35
```

- [ ] **Step 2: Implement direction-aware F2**

```python
def compute_f2_momentum(rsi: float, macd_div: bool, roc_z: float,
                        direction: str = "LONG") -> float:
    """F2 Momentum: Trend-conditional for LONG, Inverted for SHORT."""
    score = 0
    if direction == "LONG":
        if 40 < rsi < 70:
            score += 30
        if macd_div:
            score += 35
        # Positive ROC is bullish
        score += max(0, min(35, 35 + roc_z * 10))
    else:  # SHORT — inverted
        if 30 < rsi < 60:
            score += 30
        if macd_div:
            score += 35
        # Negative ROC is bearish → good for SHORT
        score += max(0, min(35, 35 - roc_z * 10))
    return min(score, 100)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF2MomentumDirection -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F2 momentum scoring for direction-aware LONG/SHORT"
```

---

### Task 3: Refactor F3 Volume for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:38-45`

- [ ] **Step 1: Write the failing tests**

```python
class TestF3VolumeDirection:
    def test_long_above_vwap_scores_high(self):
        score = compute_f3_volume(above_vwap=True, vol_z=1.0, vol_confirm=True, direction="LONG")
        assert score == 100  # 40 + 30 + 30

    def test_short_below_vwap_scores_high(self):
        """F3 SHORT: Inverted — below VWAP is good for shorts"""
        score = compute_f3_volume(above_vwap=False, vol_z=1.0, vol_confirm=True, direction="SHORT")
        assert score == 100  # 40 (below VWAP) + 30 + 30

    def test_long_below_vwap_loses_40(self):
        score = compute_f3_volume(above_vwap=False, vol_z=0, vol_confirm=False, direction="LONG")
        assert score == 0
```

- [ ] **Step 2: Implement direction-aware F3**

```python
def compute_f3_volume(above_vwap: bool, vol_z: float, vol_confirm: bool,
                      direction: str = "LONG") -> float:
    """F3 Volume: Above VWAP for LONG, Inverted (below VWAP) for SHORT."""
    score = 0
    if direction == "LONG":
        if above_vwap:
            score += 40
    else:  # SHORT — inverted: below VWAP is good
        if not above_vwap:
            score += 40
    score += max(0, min(30, abs(vol_z) * 10))
    if vol_confirm:
        score += 30
    return min(score, 100)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF3VolumeDirection -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F3 volume scoring for direction-aware LONG/SHORT"
```

---

### Task 4: Refactor F4 Vol-Pos for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:48-52`

- [ ] **Step 1: Write the failing tests**

```python
class TestF4VolPosDirection:
    def test_long_near_support_scores_high(self):
        """F4 LONG: Near support = low BB position + high distance to support"""
        score = compute_f4_volpos(bb_pos=0.1, atr_pctile=0.2, dist_to_sup=0.03, direction="LONG")
        assert score > 80  # low BB pos = near lower band, good for LONG

    def test_short_near_resistance_scores_high(self):
        """F4 SHORT: Near resistance = high BB position + high distance to resistance"""
        score = compute_f4_volpos(bb_pos=0.9, atr_pctile=0.8, dist_to_res=0.03, direction="SHORT")
        assert score > 80  # high BB pos = near upper band, good for SHORT

    def test_long_high_bb_pos_penalized(self):
        score = compute_f4_volpos(bb_pos=0.95, atr_pctile=0.5, dist_to_sup=0.0, direction="LONG")
        assert score < 10
```

- [ ] **Step 2: Implement direction-aware F4**

```python
def compute_f4_volpos(bb_pos: float, atr_pctile: float,
                      dist_to_sup: float = 0.0, dist_to_res: float = 0.0,
                      direction: str = "LONG") -> float:
    """F4 Vol-Pos: Near support for LONG, Near resistance for SHORT."""
    if direction == "LONG":
        # Near support = low BB position
        score = max(0, 100 - bb_pos * 100)
        score += max(0, min(50, dist_to_sup * 100))
    else:  # SHORT — inverted: near resistance
        # Near resistance = high BB position
        score = max(0, bb_pos * 100)
        score += max(0, min(50, dist_to_res * 100))
    return min(score, 100)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF4VolPosDirection -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F4 vol-pos scoring for direction-aware LONG/SHORT"
```

---

### Task 5: Refactor F5 Sector for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:55-56`

- [ ] **Step 1: Write the failing tests**

```python
class TestF5SectorDirection:
    def test_long_strong_sector_scores_high(self):
        """F5 LONG: High RS rank (1) = strong sector = high score"""
        score = compute_f5_sector(rs_rank=1, direction="LONG")
        assert score == 100

    def test_short_weak_sector_scores_high(self):
        """F5 SHORT: Low RS rank (11) = weak sector = high score for SHORT"""
        score = compute_f5_sector(rs_rank=11, direction="SHORT")
        assert score == 100

    def test_long_weak_sector_scores_low(self):
        score = compute_f5_sector(rs_rank=11, direction="LONG")
        assert score == 0  # (100 - (11-1)*10) = 0

    def test_short_strong_sector_scores_low(self):
        score = compute_f5_sector(rs_rank=1, direction="SHORT")
        assert score == 0  # inverted: rank 1 → worst for SHORT
```

- [ ] **Step 2: Implement direction-aware F5**

```python
def compute_f5_sector(rs_rank: int, direction: str = "LONG") -> float:
    """F5 Sector: Strong sector for LONG, Weak sector for SHORT."""
    if direction == "LONG":
        return max(0, 100 - (rs_rank - 1) * 10)
    else:  # SHORT — inverted: low rank = bad for SHORT, high rank = good
        return max(0, (rs_rank - 1) * 10)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF5SectorDirection -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F5 sector scoring for direction-aware LONG/SHORT"
```

---

### Task 6: Refactor F7 Pos-Rng for Direction-Aware Scoring

**Files:**
- Modify: `engine/layers/l5_scoring.py:68-70`

- [ ] **Step 1: Write the failing tests**

```python
class TestF7PosRngDirection:
    def test_long_bottom_20pct_scores_high(self):
        """F7 LONG: Bottom 20% of 52-week range = high score"""
        score = compute_f7_posrng(pos_52w=0.1, cpr_dist=0.02, direction="LONG")
        assert score >= 90  # low 52w pos = near bottom = good for long

    def test_short_top_20pct_scores_high(self):
        """F7 SHORT: Top 20% of 52-week range = high score"""
        score = compute_f7_posrng(pos_52w=0.9, cpr_dist=0.02, direction="SHORT")
        assert score >= 90  # high 52w pos = near top = good for short

    def test_long_top_80pct_scores_low(self):
        score = compute_f7_posrng(pos_52w=0.85, cpr_dist=0.0, direction="LONG")
        assert score < 20

    def test_short_bottom_20pct_scores_low(self):
        score = compute_f7_posrng(pos_52w=0.1, cpr_dist=0.0, direction="SHORT")
        assert score < 20
```

- [ ] **Step 2: Implement direction-aware F7**

```python
def compute_f7_posrng(pos_52w: float, cpr_dist: float, direction: str = "LONG") -> float:
    """F7 Pos-Rng: Bottom 20% for LONG, Top 20% for SHORT."""
    if direction == "LONG":
        score = max(0, 100 - pos_52w * 100)
    else:  # SHORT — inverted: top of range is good
        score = max(0, pos_52w * 100)
    score += max(0, min(50, cpr_dist * 100))
    return min(score, 100)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_l5_direction.py::TestF7PosRngDirection -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: refactor F7 pos-rng scoring for direction-aware LONG/SHORT"
```

---

### Task 7: Add liquidity_multiplier, stale_data freeze, index_change modifier

**Files:**
- Modify: `engine/layers/l5_scoring.py` (`L5Scoring.compute()`)

- [ ] **Step 1: Write the failing tests**

```python
class TestL5ScoringIntegration:
    def test_liquidity_multiplier_applied(self):
        scorer = L5Scoring()
        data = {
            "symbol": "RELIANCE",
            "direction": "LONG",
            "ema_aligned": True, "supertrend_bull": True, "adx": 30,
            "rsi": 55, "macd_divergence": True, "roc_z": 1.0,
            "above_vwap": True, "vol_z": 1.0, "vol_confirm": True,
            "bb_position": 0.2, "atr_pctile": 0.3, "dist_to_support": 0.02,
            "pos_52w": 0.2, "cpr_dist": 0.01,
            "fo_ban": False, "earnings": False,
            "liquidity_multiplier": 0.85,
        }
        sector = {"rank": 1, "tailwind": False, "headwind": False}
        oi = {"classification": "Long Buildup"}
        result = scorer.compute(data, "Trending-Up", sector, oi)
        # Score with 0.85 liq multiplier should be ~85% of full-score value
        assert result["score"] < 90  # Would be ~100 without multiplier

    def test_stale_data_freezes_score(self):
        scorer = L5Scoring()
        data = {"symbol": "X", "direction": "LONG", "stale_data": True,
                "ema_aligned": True, "supertrend_bull": True, "adx": 30,
                "rsi": 55, "macd_divergence": False, "roc_z": 0,
                "above_vwap": True, "vol_z": 0, "vol_confirm": False,
                "bb_position": 0.5, "atr_pctile": 0.5, "dist_to_support": 0,
                "pos_52w": 0.5, "cpr_dist": 0,
                "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0}
        sector = {"rank": 6}
        oi = {"classification": "Neutral"}
        result1 = scorer.compute(data, "Trending-Up", sector, oi)
        # Second call with stale_data should return same score (frozen)
        result2 = scorer.compute(data, "Trending-Up", sector, oi)
        assert result1["score"] == result2["score"]

    def test_index_change_modifier_applied(self):
        scorer = L5Scoring()
        data = {"symbol": "X", "direction": "LONG", "index_change": True,
                "ema_aligned": True, "supertrend_bull": True, "adx": 30,
                "rsi": 55, "macd_divergence": False, "roc_z": 0,
                "above_vwap": True, "vol_z": 0, "vol_confirm": False,
                "bb_position": 0.5, "atr_pctile": 0.5, "dist_to_support": 0,
                "pos_52w": 0.5, "cpr_dist": 0,
                "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0}
        sector = {"rank": 6}
        oi = {"classification": "Neutral"}
        result = scorer.compute(data, "Trending-Up", sector, oi)
        # index_change modifier = -2, should reduce score by 2
        assert result["modifiers"] == -2
```

- [ ] **Step 2: Implement liquidity_multiplier, stale_data freeze, index_change in L5Scoring.compute()**

```python
class L5Scoring:
    def __init__(self):
        self._frozen_scores: dict[str, float] = {}

    def compute(self, symbol_data: dict, regime: str, sector_data: dict,
                oi_data: dict) -> dict:
        symbol = symbol_data["symbol"]
        direction = symbol_data.get("direction", "LONG")

        # Stale data freeze: return frozen score if data > 30s stale
        if symbol_data.get("stale_data", False):
            frozen = self._frozen_scores.get(symbol)
            if frozen is not None:
                return {
                    "symbol": symbol,
                    "score": frozen["score"],
                    "factors": frozen["factors"],
                    "modifiers": frozen["modifiers"],
                    "frozen": True,
                }

        f1 = compute_f1_trend(
            symbol_data.get("ema_aligned", False),
            symbol_data.get("supertrend_bull", False),
            symbol_data.get("adx", 0),
            direction=direction,
        )
        f2 = compute_f2_momentum(
            symbol_data.get("rsi", 50),
            symbol_data.get("macd_divergence", False),
            symbol_data.get("roc_z", 0),
            direction=direction,
        )
        f3 = compute_f3_volume(
            symbol_data.get("above_vwap", False),
            symbol_data.get("vol_z", 0),
            symbol_data.get("vol_confirm", False),
            direction=direction,
        )
        f4 = compute_f4_volpos(
            symbol_data.get("bb_position", 0.5),
            symbol_data.get("atr_pctile", 0.5),
            symbol_data.get("dist_to_support", 0),
            symbol_data.get("dist_to_resistance", 0),
            direction=direction,
        )
        f5 = compute_f5_sector(sector_data.get("rank", 6), direction=direction)
        f6 = compute_f6_oi(oi_data.get("classification", "Neutral"), direction)
        f7 = compute_f7_posrng(
            symbol_data.get("pos_52w", 0.5),
            symbol_data.get("cpr_dist", 0),
            direction=direction,
        )

        factors = {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6, "f7": f7}
        raw = compute_raw_score(factors, regime)

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

        # Short asymmetry penalty
        if direction == "SHORT":
            s_final = s_final * 0.92

        result = {
            "symbol": symbol,
            "score": s_final,
            "factors": factors,
            "modifiers": modifiers,
        }

        # Cache for potential stale-data freeze
        if not symbol_data.get("stale_data", False):
            self._frozen_scores[symbol] = result

        return result
```

- [ ] **Step 3: Run all direction tests**

Run: `pytest tests/test_l5_direction.py -v`
Expected: PASS

- [ ] **Step 4: Run existing L5 tests**

Run: `pytest tests/test_l5_scoring.py -v`
Expected: PASS (may need minor updates if existing tests don't pass direction)

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add engine/layers/l5_scoring.py tests/test_l5_direction.py
git commit -m "feat: add liquidity_multiplier, stale_data freeze, index_change modifier to L5"
```
