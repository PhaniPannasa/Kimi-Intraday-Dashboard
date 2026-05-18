# L8 Cost Model + Thesis Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix L8 cost model rates, Net R:R formula, time-decay, and implement all 6 setup types so every thesis card displays correct Indian-cost-aware net R:R and grade.

**Architecture:** Refactor `engine/layers/l8_thesis.py` into focused functions: `cost_model.py` (rates + slippage + Net R:R), `time_decay.py` (spec quadratic decay), `setups/` (one file per setup type), and `l8_thesis.py` (orchestrator + actionability tier). The `ThesisCard` Pydantic model gets new fields for cost transparency.

**Tech Stack:** Python 3.11, Pydantic v2, NumPy

---

## File Structure

```
engine/layers/
├── l8_thesis.py           # MODIFY: orchestrator, actionability tier, setup dispatch
├── l8_cost_model.py       # CREATE: brokerage rates, slippage, Net R:R formula
├── l8_time_decay.py       # CREATE: spec quadratic time-decay
├── l8_setups/
│   ├── __init__.py         # CREATE
│   ├── orb_15.py           # CREATE: ORB 15-min setup (ported from l8_thesis.py)
│   ├── vwap_reclaim.py     # CREATE: VWAP Reclaim setup
│   ├── supertrend_pullback.py # CREATE: Supertrend Pullback setup
│   ├── mean_reversion.py   # CREATE: Mean Reversion setup
│   ├── first_hour_breakout.py # CREATE: First Hour Breakout setup
│   └── cpr_breakout.py     # CREATE: CPR Breakout setup
engine/models/
├── frames.py              # MODIFY: add cost_breakdown, slippage_bps to ThesisCard
└── enums.py               # MODIFY: add TimeBucket enum (if missing)
tests/
└── test_l8_cost_model.py  # CREATE: comprehensive cost model tests
└── test_l8_setups.py      # CREATE: all 6 setup tests
└── test_l8_time_decay.py  # CREATE: time-decay tests
└── test_l8_thesis.py      # MODIFY: update existing tests
```

---

### Task 1: Create Time Bucket Enum (if missing)

**Files:**
- Modify: `engine/models/enums.py`

- [ ] **Step 1: Add TimeBucket enum**

```python
class TimeBucket(str, Enum):
    PRE_OPEN = "Pre-Open"
    OPENING_SHOCK = "Opening Shock"          # 9:15-9:30
    TREND_ESTABLISHMENT = "Trend Establishment"  # 9:30-10:45
    MID_MORNING = "Mid-Morning"              # 10:45-12:00
    LUNCH = "Lunch"                          # 12:00-13:00
    AFTERNOON_RECOVERY = "Afternoon Recovery" # 13:00-14:30
    CLOSING_HOUR = "Closing Hour"            # 14:30-15:30
```

- [ ] **Step 2: Run existing tests to confirm no breakage**

Run: `pytest tests/ -x -q`
Expected: PASS (all existing tests still pass)

- [ ] **Step 3: Commit**

```bash
git add engine/models/enums.py
git commit -m "feat: add TimeBucket enum for session-time awareness"
```

---

### Task 2: Create Cost Model with Correct Rates

**Files:**
- Create: `engine/layers/l8_cost_model.py`
- Test: `tests/test_l8_cost_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l8_cost_model.py
import pytest
from engine.layers.l8_cost_model import (
    compute_brokerage_equity,
    compute_brokerage_futures,
    compute_slippage,
    compute_net_rr,
    COST_RATES,
)

def test_equity_brokerage_matches_spec():
    """Verify equity intraday (MIS) rates against spec table."""
    costs = compute_brokerage_equity(entry=1000.0, exit=1010.0, qty=100, direction="LONG")
    # Brokerage: 0.03% capped at 20/order
    assert costs["brokerage"] == pytest.approx(40.0, rel=0.01)  # 20+20 both legs
    # STT: 0.025% sell only
    assert costs["stt"] == pytest.approx(1010 * 100 * 0.00025, rel=0.01)
    # Exchange: 0.00297% both sides
    assert costs["exchange"] == pytest.approx((1000 + 1010) * 100 * 0.0000297, rel=0.01)
    # SEBI: 0.0001% both sides
    assert costs["sebi"] == pytest.approx((1000 + 1010) * 100 * 0.000001, rel=0.01)
    # Stamp: 0.003% buy only
    assert costs["stamp"] == pytest.approx(1000 * 100 * 0.00003, rel=0.01)
    # GST: 18% on (brokerage + exchange + sebi)
    gst_base = costs["brokerage"] + costs["exchange"] + costs["sebi"]
    assert costs["gst"] == pytest.approx(gst_base * 0.18, rel=0.01)

def test_futures_brokerage_matches_spec():
    """Verify futures intraday rates against spec table."""
    costs = compute_brokerage_futures(entry=1000.0, exit=1010.0, qty=100, direction="LONG")
    # Brokerage: flat 20/leg
    assert costs["brokerage"] == 40.0
    # STT: 0.0125% sell only
    assert costs["stt"] == pytest.approx(1010 * 100 * 0.000125, rel=0.01)
    # Exchange: 0.00173% both sides
    assert costs["exchange"] == pytest.approx((1000 + 1010) * 100 * 0.0000173, rel=0.01)

def test_slippage_by_liquidity_bucket():
    """Verify slippage rates match spec per liquidity bucket."""
    assert compute_slippage("Excellent", is_stop=False) == 5
    assert compute_slippage("Good", is_stop=False) == 10
    assert compute_slippage("Marginal", is_stop=False) == 20
    assert compute_slippage("Poor", is_stop=False) == 35
    # Stop-leg add-ons
    assert compute_slippage("Excellent", is_stop=True) == 13   # 5+8
    assert compute_slippage("Good", is_stop=True) == 25        # 10+15
    assert compute_slippage("Marginal", is_stop=True) == 45    # 20+25
    assert compute_slippage("Poor", is_stop=True) == 75        # 35+40

def test_net_rr_formula_matches_spec():
    """Spec: Net reward = |T1-Trigger| - (cost% * Trigger)
       Net risk = |Trigger-Invalidation| + (stop_slippage * Trigger)
       Net R:R = Net reward / Net risk"""
    result = compute_net_rr(
        trigger=1000.0, t1=1020.0, invalidation=990.0,
        cost_pct=0.05, stop_slippage_pct=0.0013,
    )
    net_reward = 20.0 - (0.0005 * 1000)  # = 19.5
    net_risk = 10.0 + (0.000013 * 1000)  # = 10.013
    expected = net_reward / net_risk
    assert result["net_rr"] == pytest.approx(expected, rel=0.01)
    assert result["net_reward"] == pytest.approx(net_reward, rel=0.01)
    assert result["net_risk"] == pytest.approx(net_risk, rel=0.01)

def test_short_direction_cost_application():
    """SHORT: entry is sell, exit is buy-to-cover. STT on entry leg, stamp on exit leg."""
    costs = compute_brokerage_futures(entry=1000.0, exit=990.0, qty=100, direction="SHORT")
    # STT: 0.0125% on sell leg = entry for SHORT
    assert costs["stt"] == pytest.approx(1000 * 100 * 0.000125, rel=0.01)
    # Stamp: 0.002% on buy leg = exit for SHORT (buy to cover)
    assert costs["stamp"] == pytest.approx(990 * 100 * 0.00002, rel=0.01)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_l8_cost_model.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create cost model module**

```python
# engine/layers/l8_cost_model.py
"""Indian intraday cost model per system_design_final.md Section 5.8.

Rates:
  Equity Intraday (MIS):
    Brokerage: 0.03% or Rs.20/order, whichever is lower (both sides)
    STT: 0.025% (sell only)
    Exchange: 0.00297% (both)
    SEBI: Rs.10/crore = 0.0001% (both)
    Stamp: 0.003% (buy only)
    GST: 18% on (brokerage + exchange + SEBI) (both)

  Futures Intraday:
    Brokerage: Rs.20/leg flat
    STT: 0.0125% (sell)
    Exchange: 0.00173% (both)
    Stamp: 0.002% (buy)
    GST: 18% on (brokerage + exchange + SEBI)

  Slippage (Depth-Derived):
    Excellent: 5 bps normal / +8 bps SL
    Good: 10 bps / +15 bps
    Marginal: 20 bps / +25 bps
    Poor: 35 bps / +40 bps
"""

COST_RATES = {
    "equity": {
        "brokerage_pct": 0.0003,     # 0.03%
        "brokerage_cap": 20.0,       # Rs.20 per order
        "stt_pct": 0.00025,          # 0.025% sell only
        "exchange_pct": 0.0000297,   # 0.00297%
        "sebi_pct": 0.000001,        # 0.0001% (Rs.10/crore)
        "stamp_pct": 0.00003,        # 0.003% buy only
        "gst_pct": 0.18,
    },
    "futures": {
        "brokerage_flat": 20.0,      # Rs.20/leg
        "stt_pct": 0.000125,         # 0.0125% sell only
        "exchange_pct": 0.0000173,   # 0.00173%
        "sebi_pct": 0.000001,        # 0.0001%
        "stamp_pct": 0.00002,        # 0.002% buy only
        "gst_pct": 0.18,
    },
}

SLIPPAGE = {
    "Excellent": {"normal": 5, "stop": 8},
    "Good": {"normal": 10, "stop": 15},
    "Marginal": {"normal": 20, "stop": 25},
    "Poor": {"normal": 35, "stop": 40},
}


def compute_brokerage_equity(entry: float, exit: float, qty: int = 100,
                              direction: str = "LONG") -> dict:
    """Compute all charges for equity intraday (MIS)."""
    r = COST_RATES["equity"]
    buy_value = entry * qty
    sell_value = exit * qty
    turnover = buy_value + sell_value

    brokerage = min(r["brokerage_cap"], buy_value * r["brokerage_pct"]) + \
                min(r["brokerage_cap"], sell_value * r["brokerage_pct"])

    # STT on sell leg only
    if direction == "LONG":
        stt = sell_value * r["stt_pct"]   # exit is sell for LONG
    else:
        stt = buy_value * r["stt_pct"]    # entry is sell for SHORT

    exchange = turnover * r["exchange_pct"]
    sebi = turnover * r["sebi_pct"]
    gst = (brokerage + exchange + sebi) * r["gst_pct"]

    # Stamp on buy leg only
    if direction == "LONG":
        stamp = buy_value * r["stamp_pct"]   # entry is buy for LONG
    else:
        stamp = sell_value * r["stamp_pct"]  # exit is buy-to-cover for SHORT

    total = brokerage + stt + exchange + sebi + gst + stamp
    return {
        "turnover": turnover,
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "sebi": round(sebi, 2),
        "gst": round(gst, 2),
        "stamp": round(stamp, 2),
        "total_cost": round(total, 2),
        "cost_pct": (total / turnover) * 100 if turnover > 0 else 0.0,
    }


def compute_brokerage_futures(entry: float, exit: float, qty: int = 100,
                               direction: str = "LONG") -> dict:
    """Compute all charges for futures intraday."""
    r = COST_RATES["futures"]
    buy_value = entry * qty
    sell_value = exit * qty
    turnover = buy_value + sell_value

    brokerage = r["brokerage_flat"] * 2  # Rs.20 per leg × 2

    if direction == "LONG":
        stt = sell_value * r["stt_pct"]
    else:
        stt = buy_value * r["stt_pct"]

    exchange = turnover * r["exchange_pct"]
    sebi = turnover * r["sebi_pct"]
    gst = (brokerage + exchange + sebi) * r["gst_pct"]

    if direction == "LONG":
        stamp = buy_value * r["stamp_pct"]
    else:
        stamp = sell_value * r["stamp_pct"]

    total = brokerage + stt + exchange + sebi + gst + stamp
    return {
        "turnover": turnover,
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "sebi": round(sebi, 2),
        "gst": round(gst, 2),
        "stamp": round(stamp, 2),
        "total_cost": round(total, 2),
        "cost_pct": (total / turnover) * 100 if turnover > 0 else 0.0,
    }


def compute_brokerage(entry: float, exit: float, qty: int = 100,
                      lot_size: int = 50, futures: bool = True,
                      direction: str = "LONG") -> dict:
    """Dispatch to equity or futures cost computation."""
    if futures:
        return compute_brokerage_futures(entry, exit, qty, direction)
    return compute_brokerage_equity(entry, exit, qty, direction)


def compute_slippage(liquidity_quality: str, is_stop: bool = False) -> int:
    """Return slippage in basis points for a given liquidity bucket."""
    bucket = SLIPPAGE.get(liquidity_quality, SLIPPAGE["Good"])
    key = "stop" if is_stop else "normal"
    return bucket[key]


def compute_net_rr(trigger: float, t1: float, invalidation: float,
                   cost_pct: float, stop_slippage_pct: float) -> dict:
    """Compute Net R:R per spec Section 5.8.

    Net reward = |T1 - Trigger| - (cost_pct/100 * Trigger)
    Net risk = |Trigger - Invalidation| + (stop_slippage_pct/100 * Trigger)
    Net R:R = Net reward / Net risk
    """
    cost_factor = cost_pct / 100.0
    slip_factor = stop_slippage_pct / 100.0

    gross_reward = abs(t1 - trigger)
    gross_risk = abs(trigger - invalidation)

    net_reward = gross_reward - (cost_factor * trigger)
    net_risk = gross_risk + (slip_factor * trigger)

    net_rr = net_reward / net_risk if net_risk > 0 else 0.0
    gross_rr = gross_reward / gross_risk if gross_risk > 0 else 0.0

    return {
        "gross_rr": round(gross_rr, 2),
        "net_rr": round(net_rr, 2),
        "net_reward": round(net_reward, 2),
        "net_risk": round(net_risk, 2),
        "cost_pct": round(cost_pct, 3),
    }


def compute_grade(net_rr: float) -> str:
    """≥ 1.5: ATTRACTIVE, 1.0-1.5: MARGINAL, < 1.0: UNATTRACTIVE"""
    if net_rr >= 1.5:
        return "ATTRACTIVE"
    elif net_rr >= 1.0:
        return "MARGINAL"
    return "UNATTRACTIVE"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_l8_cost_model.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l8_cost_model.py tests/test_l8_cost_model.py
git commit -m "feat: add spec-compliant Indian cost model with correct rates and slippage"
```

---

### Task 3: Create Time-Decay with Spec Formula

**Files:**
- Create: `engine/layers/l8_time_decay.py`
- Test: `tests/test_l8_time_decay.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_l8_time_decay.py
import math
from engine.layers.l8_time_decay import compute_time_decay, LAMBDA_VALUES, TIME_WINDOWS

def test_orb_time_decay_at_creation():
    """At t=0 minutes elapsed (just created), multiplier = 1.0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=0)
    assert result == 1.0

def test_orb_time_decay_after_60_min():
    """ORB: M(t) = exp(-0.0003 * max(0, 60-30)^2) = exp(-0.0003*900) = exp(-0.27) ≈ 0.763"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=60)
    expected = math.exp(-0.0003 * (60 - 30)**2)
    assert result == pytest.approx(expected, rel=0.001)

def test_vwap_time_decay_after_90_min():
    """VWAP/ST: lambda=0.00015, t_window=15"""
    result = compute_time_decay("VWAP_RECLAIM", minutes_since_creation=90)
    expected = math.exp(-0.00015 * (90 - 15)**2)
    assert result == pytest.approx(expected, rel=0.001)

def test_time_decay_before_window_is_1():
    """Before t_window, multiplier stays at 1.0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=15)
    assert result == 1.0

def test_time_decay_deep_decay():
    """After 4 hours, multiplier approaches 0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=240)
    assert result < 0.01    # exp(-0.0003 * 210^2) ≈ exp(-13.23) ≈ 0

def test_custom_setup_decay():
    """Setup not in LAMBDA_VALUES uses default lambda=0.0002"""
    result = compute_time_decay("CPR_BREAKOUT", minutes_since_creation=90)
    expected = math.exp(-0.0002 * (90 - 30)**2)
    assert result == pytest.approx(expected, rel=0.001)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_l8_time_decay.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create time-decay module**

```python
# engine/layers/l8_time_decay.py
"""Time-decay function per system_design_final.md Section 5.8.

M(t) = exp(-lambda * max(0, t - t_window)^2)

| Time           | ORB Multiplier | Supertrend/VWAP |
|----------------|----------------|-----------------|
| 9:30-10:30     | 1.00           | 1.00            |
| 10:30-11:30    | 0.85           | 0.90            |
| 11:30-12:30    | 0.65           | 0.78            |
| 12:30-13:30    | 0.42           | 0.62            |
| 13:30-14:30    | 0.22           | 0.42            |
| After 14:30    | 0.08           | 0.22            |
"""
import math

# lambda values per setup type (by enum value or name)
LAMBDA_VALUES = {
    "ORB_15MIN": 0.0003,
    "ORB_2HOUR": 0.0003,
    "FIRST_HOUR_BREAKOUT": 0.0003,
    "VWAP_RECLAIM": 0.00015,
    "SUPERTREND_PULLBACK": 0.00015,
    "CPR_BREAKOUT": 0.00015,
    "MEAN_REVERSION": 0.00015,
}

# t_window values (minutes after creation before decay starts)
TIME_WINDOWS = {
    "ORB_15MIN": 30,
    "ORB_2HOUR": 60,
    "FIRST_HOUR_BREAKOUT": 45,
    "VWAP_RECLAIM": 15,
    "SUPERTREND_PULLBACK": 15,
    "CPR_BREAKOUT": 15,
    "MEAN_REVERSION": 30,
}

DEFAULT_LAMBDA = 0.0002
DEFAULT_WINDOW = 30


def compute_time_decay(setup_type: str, minutes_since_creation: int) -> float:
    """Compute M(t) for a setup at elapsed minutes since thesis creation.

    Args:
        setup_type: Setup type name (e.g. "ORB_15MIN", "VWAP_RECLAIM")
        minutes_since_creation: Minutes elapsed since thesis was created

    Returns:
        Multiplier in (0, 1] — 1.0 at creation, decaying toward 0
    """
    lam = LAMBDA_VALUES.get(setup_type, DEFAULT_LAMBDA)
    t_window = TIME_WINDOWS.get(setup_type, DEFAULT_WINDOW)

    effective_t = max(0, minutes_since_creation - t_window)
    return math.exp(-lam * effective_t ** 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_l8_time_decay.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l8_time_decay.py tests/test_l8_time_decay.py
git commit -m "feat: add spec-compliant quadratic time-decay function"
```

---

### Task 4: Create Setup Type Implementations

**Files:**
- Create: `engine/layers/l8_setups/__init__.py`
- Create: `engine/layers/l8_setups/orb_15.py`
- Create: `engine/layers/l8_setups/vwap_reclaim.py`
- Create: `engine/layers/l8_setups/supertrend_pullback.py`
- Create: `engine/layers/l8_setups/mean_reversion.py`
- Create: `engine/layers/l8_setups/first_hour_breakout.py`
- Create: `engine/layers/l8_setups/cpr_breakout.py`
- Test: `tests/test_l8_setups.py`

- [ ] **Step 1: Create the __init__.py and setup implementations**

```python
# engine/layers/l8_setups/__init__.py
from engine.layers.l8_setups.orb_15 import assemble_orb_15
from engine.layers.l8_setups.vwap_reclaim import assemble_vwap_reclaim
from engine.layers.l8_setups.supertrend_pullback import assemble_supertrend_pullback
from engine.layers.l8_setups.mean_reversion import assemble_mean_reversion
from engine.layers.l8_setups.first_hour_breakout import assemble_first_hour_breakout
from engine.layers.l8_setups.cpr_breakout import assemble_cpr_breakout

SETUP_ASSEMBLERS = {
    1: assemble_orb_15,
    2: assemble_vwap_reclaim,
    3: assemble_supertrend_pullback,
    4: assemble_mean_reversion,
    5: assemble_first_hour_breakout,
    6: assemble_cpr_breakout,
}
```

```python
# engine/layers/l8_setups/orb_15.py
"""ORB 15-min setup.

Trigger: ORB High + 1 tick (long) / ORB Low - 1 tick (short)
Invalidation: max(ORB Low, VWAP-0.5%) / min(ORB High, VWAP+0.5%)
T1: Trigger + 1.5 * ORB Range
T2: PDH (long) / PDL (short)
Valid Window: Until 11:00 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_orb_15(
    symbol: str,
    direction: Direction,
    orb_high: float,
    orb_low: float,
    vwap: float,
    pdh: float,
    pdl: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    orb_range = orb_high - orb_low

    if direction == Direction.LONG:
        trigger = orb_high + tick_size
        invalidation = max(orb_low, vwap * 0.995)
        t1 = trigger + 1.5 * orb_range
        t2 = pdh
        regime = Regime.TRENDING_UP
    else:
        trigger = orb_low - tick_size
        invalidation = min(orb_high, vwap * 1.005)
        t1 = trigger - 1.5 * orb_range
        t2 = pdl
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.ORB_15MIN,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

```python
# engine/layers/l8_setups/vwap_reclaim.py
"""VWAP Reclaim setup.

Trigger: VWAP cross above + volume confirmation (long) / below (short)
Invalidation: VWAP - 0.8 * ATR (long) / VWAP + 0.8 * ATR (short)
T1: VWAP + 1.5 * ATR (long) / VWAP - 1.5 * ATR (short)
T2: VWAP + 2.5 * ATR (long) / VWAP - 2.5 * ATR (short)
Valid Window: After 9:45 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_vwap_reclaim(
    symbol: str,
    direction: Direction,
    vwap: float,
    atr: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = vwap + tick_size  # crossed above VWAP
        invalidation = vwap - 0.8 * atr
        t1 = vwap + 1.5 * atr
        t2 = vwap + 2.5 * atr
        regime = Regime.TRENDING_UP
    else:
        trigger = vwap - tick_size  # crossed below VWAP
        invalidation = vwap + 0.8 * atr
        t1 = vwap - 1.5 * atr
        t2 = vwap - 2.5 * atr
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.VWAP_RECLAIM,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

```python
# engine/layers/l8_setups/supertrend_pullback.py
"""Supertrend Pullback setup.

Trigger: Pullback touches ST line from above (long) / below (short)
Invalidation: ST line - 0.5 * ATR (long) / ST line + 0.5 * ATR (short)
T1: ST line + 1.5 * ATR (long) / ST line - 1.5 * ATR (short)
T2: ST line + 2.5 * ATR (long) / ST line - 2.5 * ATR (short)
Valid Window: Any (while ST direction matches)
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_supertrend_pullback(
    symbol: str,
    direction: Direction,
    supertrend_line: float,
    atr: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = supertrend_line + tick_size  # bounced off ST support
        invalidation = supertrend_line - 0.5 * atr
        t1 = supertrend_line + 1.5 * atr
        t2 = supertrend_line + 2.5 * atr
        regime = Regime.TRENDING_UP
    else:
        trigger = supertrend_line - tick_size  # rejected at ST resistance
        invalidation = supertrend_line + 0.5 * atr
        t1 = supertrend_line - 1.5 * atr
        t2 = supertrend_line - 2.5 * atr
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.SUPERTREND_PULLBACK,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

```python
# engine/layers/l8_setups/mean_reversion.py
"""Mean Reversion setup.

Trigger: Price touches lower 2-sigma BB (long) / upper 2-sigma BB (short)
Invalidation: Band breach below 2.5-sigma BB (long) / above 2.5-sigma BB (short)
T1: VWAP (min 0.6 * invalidation distance from entry)
T2: Opposite 1-sigma BB
Valid Window: Any
Preferred Regime: Range-Bound
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_mean_reversion(
    symbol: str,
    direction: Direction,
    bb_lower_2sigma: float,
    bb_upper_2sigma: float,
    bb_lower_25sigma: float,
    bb_upper_25sigma: float,
    bb_lower_1sigma: float,
    bb_upper_1sigma: float,
    vwap: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = bb_lower_2sigma - tick_size  # touched lower band
        invalidation = bb_lower_25sigma  # breach below 2.5 sigma
        raw_t1 = vwap
        min_reward = 0.6 * abs(trigger - invalidation)
        t1 = max(raw_t1, trigger + min_reward)
        t2 = bb_upper_1sigma  # opposite 1-sigma band
        regime = Regime.RANGE_BOUND
    else:
        trigger = bb_upper_2sigma + tick_size  # touched upper band
        invalidation = bb_upper_25sigma  # breach above 2.5 sigma
        raw_t1 = vwap
        min_reward = 0.6 * abs(trigger - invalidation)
        t1 = min(raw_t1, trigger - min_reward)
        t2 = bb_lower_1sigma  # opposite 1-sigma band
        regime = Regime.RANGE_BOUND

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.MEAN_REVERSION,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

```python
# engine/layers/l8_setups/first_hour_breakout.py
"""First Hour Breakout setup.

Trigger: Break above FH High after 10:15 (long) / below FH Low (short)
Invalidation: FH Low - 0.3 * FH Range (long) / FH High + 0.3 * FH Range (short)
T1: Trigger + 1.0 * FH Range (long) / Trigger - 1.0 * FH Range (short)
T2: PDH (long) / PDL (short)
Valid Window: 10:15-12:00 PM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_first_hour_breakout(
    symbol: str,
    direction: Direction,
    fh_high: float,
    fh_low: float,
    pdh: float,
    pdl: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    fh_range = fh_high - fh_low

    if direction == Direction.LONG:
        trigger = fh_high + tick_size
        invalidation = fh_low - 0.3 * fh_range
        t1 = trigger + 1.0 * fh_range
        t2 = pdh
        regime = Regime.TRENDING_UP
    else:
        trigger = fh_low - tick_size
        invalidation = fh_high + 0.3 * fh_range
        t1 = trigger - 1.0 * fh_range
        t2 = pdl
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.FIRST_HOUR_BREAKOUT,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

```python
# engine/layers/l8_setups/cpr_breakout.py
"""CPR Breakout setup.

Trigger: Break above TC + volume (long) / below BC + volume (short)
Invalidation: BC - 0.2 * CPR Width (long) / TC + 0.2 * CPR Width (short)
T1: R1 Floor Pivot (long) / S1 Floor Pivot (short)
T2: R2 Floor Pivot (long) / S2 Floor Pivot (short)
Valid Window: After 9:45 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_cpr_breakout(
    symbol: str,
    direction: Direction,
    tc: float,
    bc: float,
    r1: float,
    r2: float,
    s1: float,
    s2: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    cpr_width = abs(tc - bc)

    if direction == Direction.LONG:
        trigger = tc + tick_size
        invalidation = bc - 0.2 * cpr_width
        t1 = r1
        t2 = r2
        regime = Regime.TRENDING_UP
    else:
        trigger = bc - tick_size
        invalidation = tc + 0.2 * cpr_width
        t1 = s1
        t2 = s2
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.CPR_BREAKOUT,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
```

- [ ] **Step 2: Write the tests**

```python
# tests/test_l8_setups.py
import pytest
from datetime import datetime, timezone, timedelta
from models.enums import Direction, SetupType, Regime
from engine.layers.l8_setups.orb_15 import assemble_orb_15
from engine.layers.l8_setups.vwap_reclaim import assemble_vwap_reclaim
from engine.layers.l8_setups.supertrend_pullback import assemble_supertrend_pullback
from engine.layers.l8_setups.mean_reversion import assemble_mean_reversion
from engine.layers.l8_setups.first_hour_breakout import assemble_first_hour_breakout
from engine.layers.l8_setups.cpr_breakout import assemble_cpr_breakout


class TestORB15Setup:
    def test_long_thesis_levels(self):
        t = assemble_orb_15("RELIANCE", Direction.LONG, orb_high=2500, orb_low=2480, vwap=2490, pdh=2520, pdl=2470)
        assert t.direction == Direction.LONG
        assert t.setup_type == SetupType.ORB_15MIN
        assert t.trigger == 2500.05  # orb_high + tick
        assert t.invalidation == max(2480, 2490 * 0.995)
        assert t.t2 == 2520  # PDH for long

    def test_short_t2_is_pdl(self):
        t = assemble_orb_15("RELIANCE", Direction.SHORT, orb_high=2500, orb_low=2480, vwap=2490, pdh=2520, pdl=2470)
        assert t.direction == Direction.SHORT
        assert t.trigger == 2479.95  # orb_low - tick
        assert t.t2 == 2470  # PDL for short


class TestVWAPReclaim:
    def test_long_levels(self):
        t = assemble_vwap_reclaim("SBIN", Direction.LONG, vwap=600, atr=10)
        assert t.trigger == 600.05
        assert t.invalidation == 600 - 8  # VWAP - 0.8*ATR
        assert t.t1 == 600 + 15  # VWAP + 1.5*ATR
        assert t.t2 == 600 + 25  # VWAP + 2.5*ATR

    def test_short_levels(self):
        t = assemble_vwap_reclaim("SBIN", Direction.SHORT, vwap=600, atr=10)
        assert t.trigger == 599.95
        assert t.invalidation == 600 + 8
        assert t.t1 == 600 - 15


class TestSupertrendPullback:
    def test_long_levels(self):
        t = assemble_supertrend_pullback("INFY", Direction.LONG, supertrend_line=1500, atr=20)
        assert t.trigger == 1500.05
        assert t.invalidation == 1500 - 10  # ST - 0.5*ATR
        assert t.t1 == 1500 + 30  # ST + 1.5*ATR

    def test_short_levels(self):
        t = assemble_supertrend_pullback("INFY", Direction.SHORT, supertrend_line=1500, atr=20)
        assert t.trigger == 1499.95
        assert t.invalidation == 1500 + 10  # ST + 0.5*ATR


class TestMeanReversion:
    def test_long_t1_respects_min_reward(self):
        # If VWAP is too close, T1 should be at least 0.6 * invalidation_dist from entry
        t = assemble_mean_reversion("TATAMOTORS", Direction.LONG,
            bb_lower_2sigma=450, bb_upper_2sigma=500,
            bb_lower_25sigma=445, bb_upper_25sigma=505,
            bb_lower_1sigma=460, bb_upper_1sigma=490,
            vwap=455,  # very close to trigger=449.95, < 0.6 * (449.95-445)=2.97
        )
        min_t1 = 449.95 + 0.6 * abs(449.95 - 445)
        assert t.t1 >= min_t1
        assert t.preferred_regime == Regime.RANGE_BOUND


class TestFirstHourBreakout:
    def test_long_levels(self):
        t = assemble_first_hour_breakout("HDFC", Direction.LONG,
            fh_high=1650, fh_low=1630, pdh=1670, pdl=1620)
        fh_range = 20
        assert t.trigger == 1650.05
        assert t.invalidation == 1630 - 0.3 * fh_range
        assert t.t1 == 1650.05 + fh_range
        assert t.t2 == 1670  # PDH


class TestCPRBreakout:
    def test_long_levels(self):
        t = assemble_cpr_breakout("ICICIBANK", Direction.LONG,
            tc=950, bc=945, r1=960, r2=970, s1=940, s2=930)
        assert t.trigger == 950.05
        cpr_width = 5
        assert t.invalidation == 945 - 0.2 * cpr_width
        assert t.t1 == 960  # R1
        assert t.t2 == 970  # R2


class TestAllSetupsProduceValidCards:
    @pytest.mark.parametrize("assembler, kwargs", [
        (assemble_orb_15, {"symbol": "X", "direction": Direction.LONG, "orb_high": 100, "orb_low": 90, "vwap": 95, "pdh": 105, "pdl": 85}),
        (assemble_vwap_reclaim, {"symbol": "X", "direction": Direction.LONG, "vwap": 100, "atr": 5}),
        (assemble_supertrend_pullback, {"symbol": "X", "direction": Direction.LONG, "supertrend_line": 100, "atr": 5}),
        (assemble_mean_reversion, {"symbol": "X", "direction": Direction.LONG, "bb_lower_2sigma": 90, "bb_upper_2sigma": 110, "bb_lower_25sigma": 87, "bb_upper_25sigma": 113, "bb_lower_1sigma": 93, "bb_upper_1sigma": 107, "vwap": 100}),
        (assemble_first_hour_breakout, {"symbol": "X", "direction": Direction.LONG, "fh_high": 102, "fh_low": 98, "pdh": 105, "pdl": 95}),
        (assemble_cpr_breakout, {"symbol": "X", "direction": Direction.LONG, "tc": 100, "bc": 97, "r1": 105, "r2": 110, "s1": 95, "s2": 90}),
    ])
    def test_card_has_positive_risk(self, assembler, kwargs):
        t = assembler(**kwargs)
        risk = abs(t.trigger - t.invalidation)
        assert risk > 0, f"{assembler.__name__} produced zero-risk thesis"
```

- [ ] **Step 3: Run test to verify they pass**

Run: `pytest tests/test_l8_setups.py -v`
Expected: PASS (all parameterized + class tests)

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l8_setups/ tests/test_l8_setups.py
git commit -m "feat: implement all 6 setup types with spec-compliant levels"
```

---

### Task 5: Refactor L8Thesis Orchestrator + Actionability Tier

**Files:**
- Modify: `engine/layers/l8_thesis.py` (rewrite orchestrator)
- Modify: `engine/models/frames.py` (add cost_breakdown, slippage_bps fields)
- Modify: `tests/test_l8_thesis.py` (update for new orchestrator)

- [ ] **Step 1: Add cost_breakdown to ThesisCard model**

Edit `engine/models/frames.py` — add fields to `ThesisCard`:

```python
class ThesisCard(BaseModel):
    thesis_id: str
    symbol: str
    direction: Direction = Direction.LONG
    setup_type: SetupType = SetupType.ORB_15MIN
    trigger: float = 0.0
    invalidation: float = 0.0
    t1: float = 0.0
    t2: float = 0.0
    gross_rr: float = 0.0
    net_rr: float = 0.0
    grade: str = "UNATTRACTIVE"
    confluence_score: int = Field(0, ge=0, le=6)
    time_decay_multiplier: float = 1.0
    actionability_tier: ActionabilityTier = ActionabilityTier.RESEARCH_ONLY
    valid_until: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    preferred_regime: Regime = Regime.TRENDING_UP
    # NEW: cost transparency fields
    cost_breakdown: Optional[dict] = None    # full cost model output
    slippage_bps: int = 0                    # slippage applied in bps
    liquidity_quality: LiquidityQuality = LiquidityQuality.GOOD
    net_reward: float = 0.0                  # |T1-Trigger| - costs
    net_risk: float = 0.0                    # |Trigger-Invalidation| + slip
```

- [ ] **Step 2: Rewrite L8Thesis orchestrator**

Replace `engine/layers/l8_thesis.py`:

```python
"""L8 Thesis Assembly — orchestrator, cost model application, actionability tier.

Dispatches to l8_setups/ for each setup type's level computation,
then applies cost model + time-decay + actionability tier.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from models.frames import ThesisCard
from models.enums import Direction, SetupType, ActionabilityTier, LiquidityQuality
from engine.layers.l8_setups import SETUP_ASSEMBLERS
from engine.layers.l8_cost_model import (
    compute_brokerage,
    compute_slippage,
    compute_net_rr,
    compute_grade,
)
from engine.layers.l8_time_decay import compute_time_decay
from engine.layers.l7_confluence import L7Confluence


def compute_actionability_tier(
    net_rr: float,
    liquidity_quality: str,
    fo_ban: bool,
    shortability: str,
    direction: Direction,
    confluence_score: int,
) -> ActionabilityTier:
    """Determine actionability tier per spec Section 5.8.

    Tradeable: Clean path + Net R:R >= 1.0 + liquidity >= Good + no blocking flags
    Constrained: Execution path exists but with friction
    Research-Only: No viable retail execution
    """
    has_blocking_flags = fo_ban
    is_good_liquidity = liquidity_quality in ("Excellent", "Good")

    # Cash-only short with no SLB → Research-Only
    if direction == Direction.SHORT and shortability == "CASH_ONLY":
        return ActionabilityTier.RESEARCH_ONLY

    if net_rr < 0.8:
        return ActionabilityTier.RESEARCH_ONLY

    if net_rr >= 1.0 and is_good_liquidity and not has_blocking_flags and confluence_score >= 3:
        return ActionabilityTier.TRADEABLE

    if net_rr >= 0.8 and not has_blocking_flags:
        return ActionabilityTier.CONSTRAINED

    return ActionabilityTier.RESEARCH_ONLY


def get_setup_expiry(setup_type: SetupType, session_date: datetime) -> datetime:
    """Return clock-based valid_until for each setup type.

    Times are IST — caller must convert to UTC if needed.
    """
    setup_expiry_times = {
        SetupType.ORB_15MIN: (11, 0),
        SetupType.ORB_2HOUR: (13, 0),  # if added later
        SetupType.VWAP_RECLAIM: (14, 0),
        SetupType.SUPERTREND_PULLBACK: (14, 30),
        SetupType.MEAN_REVERSION: (13, 30),
        SetupType.FIRST_HOUR_BREAKOUT: (12, 0),
        SetupType.CPR_BREAKOUT: (14, 0),
    }
    hour, minute = setup_expiry_times.get(setup_type, (15, 15))
    return session_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


class L8Thesis:
    """Orchestrates thesis assembly: setup dispatch → cost model → time-decay → grading."""

    def __init__(self):
        self.confluence = L7Confluence()

    def assemble(
        self,
        symbol: str,
        direction: str,
        setup_type: int,
        setup_params: dict,
        confluence_data: dict,
        cost_params: dict | None = None,
        session_start: datetime | None = None,
    ) -> ThesisCard:
        """Assemble a complete thesis card with cost model and grading.

        Args:
            symbol: Stock symbol
            direction: "LONG" or "SHORT"
            setup_type: 1-6 (SetupType enum value)
            setup_params: Dict of params for the specific setup assembler
            confluence_data: Dict with close/high/low/volume/median_volume/ema9/ema20/ema50/atr/price/invalidation/t1/bar_range/median_range/direction/is_opening
            cost_params: Dict with qty/lot_size/futures/liquidity_quality/fo_ban/shortability
            session_start: Session start datetime for clock-based expiry
        """
        direction_enum = Direction(direction)
        setup_enum = SetupType(setup_type)

        # 1. Compute expiry time
        now = datetime.now(timezone.utc)
        valid_until = get_setup_expiry(setup_enum, session_start or now)

        # 2. Dispatch to setup assembler
        assembler = SETUP_ASSEMBLERS.get(setup_type)
        if assembler is None:
            raise ValueError(f"Unknown setup type: {setup_type}")

        thesis = assembler(
            symbol=symbol,
            direction=direction_enum,
            valid_until=valid_until,
            **setup_params,
        )

        # 3. Compute confluence score
        thesis.confluence_score = self.confluence.compute(confluence_data)

        # 4. Apply cost model
        cp = cost_params or {}
        qty = cp.get("qty", 100)
        lot_size = cp.get("lot_size", 50)
        futures = cp.get("futures", True)
        liq_quality = cp.get("liquidity_quality", "Good")
        fo_ban = cp.get("fo_ban", False)
        shortability = cp.get("shortability", "FUTURES_OPTIONS")

        # Compute brokerage for entry→T1 path
        costs = compute_brokerage(
            entry=thesis.trigger,
            exit=thesis.t1,
            qty=qty,
            lot_size=lot_size,
            futures=futures,
            direction=direction,
        )

        # Compute slippage
        normal_slip_bps = compute_slippage(liq_quality, is_stop=False)
        stop_slip_bps = compute_slippage(liq_quality, is_stop=True)

        # Compute Net R:R with spec formula
        rr = compute_net_rr(
            trigger=thesis.trigger,
            t1=thesis.t1,
            invalidation=thesis.invalidation,
            cost_pct=costs["cost_pct"],
            stop_slippage_pct=stop_slip_bps / 10000.0,  # bps → percentage
        )

        thesis.gross_rr = rr["gross_rr"]
        thesis.net_rr = rr["net_rr"]
        thesis.net_reward = rr["net_reward"]
        thesis.net_risk = rr["net_risk"]
        thesis.cost_breakdown = costs
        thesis.slippage_bps = normal_slip_bps
        thesis.liquidity_quality = LiquidityQuality(liq_quality)

        # 5. Apply time-decay
        thesis.time_decay_multiplier = compute_time_decay(
            setup_enum.name, minutes_since_creation=0
        )

        # 6. Grade
        thesis.grade = compute_grade(thesis.net_rr)

        # 7. Actionability tier
        thesis.actionability_tier = compute_actionability_tier(
            net_rr=thesis.net_rr,
            liquidity_quality=liq_quality,
            fo_ban=fo_ban,
            shortability=shortability,
            direction=direction_enum,
            confluence_score=thesis.confluence_score,
        )

        return thesis
```

- [ ] **Step 3: Update existing tests**

Run: `pytest tests/test_l8_thesis.py -v`
Expected: Some FAIL (old API changed). Update tests.

- [ ] **Step 4: Run all L8 tests**

Run: `pytest tests/test_l8_cost_model.py tests/test_l8_setups.py tests/test_l8_time_decay.py tests/test_l8_thesis.py -v`
Expected: ALL PASS

- [ ] **Step 5: Verify no other tests broken**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add engine/layers/l8_thesis.py engine/models/frames.py tests/test_l8_thesis.py
git commit -m "feat: refactor L8 orchestrator with cost model, time-decay, actionability tier, and all 6 setups"
```

---

### Task 6: Remove legacy functions from l8_thesis.py

**Files:**
- Modify: `engine/layers/l8_thesis.py` (clean up old code already replaced)

- [ ] **Step 1: Delete old standalone functions**

The file `engine/layers/l8_thesis.py` now contains only the `L8Thesis` class and helpers. The old `setup_orb_15()`, `compute_brokerage()`, `compute_time_decay()`, and `L8CostModel` class should all be removed (they were in the original file). Verify they're gone:

```bash
grep -n "def setup_orb_15\|def compute_brokerage\|def compute_time_decay\|class L8CostModel" engine/layers/l8_thesis.py
```
Expected: no matches

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add engine/layers/l8_thesis.py
git commit -m "refactor: remove legacy L8 functions, now in dedicated modules"
```

---

### Task 7: Update pipeline.py to use new L8 API

**Files:**
- Modify: `engine/core/pipeline.py` (update L8 call sites)

- [ ] **Step 1: Find L8 call sites**

Run: `grep -n "L8Thesis\|l8_thesis\|setup_orb_15\|L8CostModel" engine/core/pipeline.py`

- [ ] **Step 2: Update call sites to use new `L8Thesis.assemble()` API**

The new API expects `setup_type`, `setup_params`, `confluence_data`, and `cost_params` dicts. Update pipeline.py to construct these from available data.

- [ ] **Step 3: Run integration test**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/core/pipeline.py
git commit -m "fix: update pipeline to use new L8 thesis assembly API"
```
