# L10 Edge Statistics + L9 Monitor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L10: Implement 6-tier hierarchical fallback lookup, per-tier n/CI-width gates, replace `ci_lower > 0.35` with CI-width check, replace Bayesian bootstrap with Beta-Binomial conjugate, fix BH alpha to 0.10. L9: Add CREATED/PENDING states, setup-specific pending expiry, conditional 30-min extension, full outcome metrics (gross/net return, R-multiple, time-to-trigger/exit).

**Architecture:** L10 `lookup()` traverses Tier 1→6, checking n threshold and CI-width at each level. Beta-Binomial conjugate posterior replaces Dirichlet bootstrap. BH alpha parameterized. L9 state machine gains proper CREATED→PENDING→TRIGGERED→ACTIVE states with clock-based expiry per setup type. Outcome metrics computed at exit.

**Tech Stack:** Python 3.11, NumPy, SciPy

---

## File Structure

```
engine/layers/
├── l10_edge.py       # MODIFY: 6-tier lookup, CI-width gates, Beta-Binomial, BH alpha
├── l9_monitor.py     # MODIFY: state machine, expiry, outcome metrics
tests/
├── test_l10_edge.py  # MODIFY: tier fallback tests
├── test_l9_monitor.py # MODIFY: state machine tests
```

---

### Task 1: L10 — Implement 6-Tier Hierarchical Fallback

**Files:**
- Modify: `engine/layers/l10_edge.py`
- Modify: `tests/test_l10_edge.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l10_tiers.py
from engine.layers.l10_edge import L10EdgeLookup, TIER_CONFIG
from models.enums import SetupType, Regime, Direction


class TestTierFallback:
    @staticmethod
    def make_lookup() -> L10EdgeLookup:
        return L10EdgeLookup()

    def test_tier1_full_key_found(self):
        l = self.make_lookup()
        # Populate Tier 1 with sufficient data
        key_1 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, 1, 3)
        l.edge_store[key_1] = {"n": 35, "hit_rate": 0.65, "ci_lower": 0.50, "ci_upper": 0.78}
        result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
        assert result["tier"] == 1
        assert result["n"] == 35

    def test_tier2_fallback_when_tier1_insufficient_n(self):
        l = self.make_lookup()
        # Tier 1: only 15 samples (below n≥30 threshold)
        key_1 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, 1, 3)
        l.edge_store[key_1] = {"n": 15, "hit_rate": 0.6, "ci_lower": 0.35, "ci_upper": 0.85}
        # Tier 2: sufficient data (drop sector)
        key_2 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, None, 3)
        l.edge_store[key_2] = {"n": 45, "hit_rate": 0.62, "ci_lower": 0.48, "ci_upper": 0.74}
        result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
        assert result["tier"] == 2
        assert result["n"] == 45

    def test_tier3_drops_bucket(self):
        l = self.make_lookup()
        # Tier 1+2 missing, Tier 3 (Setup×Regime) available
        key_3 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, None, None)
        l.edge_store[key_3] = {"n": 55, "hit_rate": 0.58, "ci_lower": 0.45, "ci_upper": 0.70}
        result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
        assert result["tier"] == 3

    def test_tier5_setup_baseline(self):
        l = self.make_lookup()
        # Only setup baseline (Tier 5) available
        key_5 = l._make_key(SetupType.ORB_15MIN, None, Direction.LONG, None, None)
        l.edge_store[key_5] = {"n": 85, "hit_rate": 0.61, "ci_lower": 0.51, "ci_upper": 0.70}
        result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
        assert result["tier"] == 5

    def test_tier6_global_fallback(self):
        l = self.make_lookup()
        # Only global baseline
        key_6 = l._make_key(None, None, Direction.LONG, None, None)
        l.edge_store[key_6] = {"n": 200, "hit_rate": 0.55, "ci_lower": 0.48, "ci_upper": 0.62}
        result = l.lookup(SetupType.VWAP_RECLAIM, Regime.RANGE_BOUND, Direction.LONG)
        assert result["tier"] == 6
```

- [ ] **Step 2: Implement 6-tier fallback in lookup()**

```python
# engine/layers/l10_edge.py — add TIER_CONFIG and rewrite lookup()

TIER_CONFIG = {
    1: {"n_min": 30, "ci_max_halfwidth": 0.15, "drop_sector": False, "drop_bucket": False, "drop_regime": False},
    2: {"n_min": 40, "ci_max_halfwidth": 0.14, "drop_sector": True,  "drop_bucket": False, "drop_regime": False},
    3: {"n_min": 50, "ci_max_halfwidth": 0.14, "drop_sector": True,  "drop_bucket": True,  "drop_regime": False},
    4: {"n_min": 50, "ci_max_halfwidth": 0.14, "drop_sector": True,  "drop_bucket": False, "drop_regime": True},
    5: {"n_min": 80, "ci_max_halfwidth": 0.12, "drop_sector": True,  "drop_bucket": True,  "drop_regime": True},
    6: {"n_min": 50, "ci_max_halfwidth": 0.14, "drop_sector": True,  "drop_bucket": True,  "drop_regime": True},
}


def check_ci_width(ci_lower: float, ci_upper: float, max_halfwidth: float) -> bool:
    """Return True if CI half-width <= max allowed."""
    halfwidth = (ci_upper - ci_lower) / 2
    return halfwidth <= max_halfwidth


class L10EdgeLookup:
    def __init__(self):
        self.edge_store: dict[tuple, dict] = {}

    # _coerce and _make_key unchanged from current...

    def _make_key(
        self,
        setup_type: SetupType | None,
        regime: Regime | None,
        direction: Direction,
        sector: int | None,
        time_bucket: int | None,
    ) -> tuple:
        return (
            self._coerce(setup_type) if setup_type is not None else None,
            self._coerce(regime) if regime is not None else None,
            self._coerce(direction),
            sector,
            time_bucket,
        )

    def _check_tier(self, row: dict, tier: int) -> bool:
        """Return True if the row passes this tier's quality gates."""
        config = TIER_CONFIG[tier]
        n = row.get("n", 0)
        if n < config["n_min"]:
            return False
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)
        if ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(row.get("hit_rate", 0.5), n)
        if not check_ci_width(ci_lower, ci_upper, config["ci_max_halfwidth"]):
            return False
        return True

    def lookup(
        self,
        setup_type: SetupType,
        regime: Regime,
        direction: Direction,
        sector: int | None = None,
        time_bucket: int | None = None,
    ) -> dict:
        """Hierarchical 6-tier lookup with fallback.

        Tier 1: Setup × Regime × Sector × Bucket
        Tier 2: Setup × Regime × Bucket (drop Sector)
        Tier 3: Setup × Regime (drop Sector + Bucket)
        Tier 4: Setup × Bucket (drop Regime, keep Bucket)
        Tier 5: Setup baseline
        Tier 6: Global baseline
        """
        # Define key components for each tier
        tier_keys = [
            (1, setup_type, regime, sector, time_bucket),
            (2, setup_type, regime, None, time_bucket),
            (3, setup_type, regime, None, None),
            (4, setup_type, None, None, time_bucket),
            (5, setup_type, None, None, None),
            (6, None, None, None, None),
        ]

        for tier, st, rg, sc, tb in tier_keys:
            # Tier 4+5+6 need direction in key
            key = self._make_key(
                st if st is not None else None,
                rg if rg is not None else None,
                direction,
                sc,
                tb,
            )
            row = self.edge_store.get(key, {})
            if row and self._check_tier(row, tier):
                result = self._build_result(row, setup_type, regime, direction, sector, time_bucket)
                result["tier"] = tier
                return result

        # Ultimate fallback: return empty with tier=0
        return {
            "setup_type": setup_type, "regime": regime, "direction": direction,
            "sector": sector, "time_bucket": time_bucket,
            "n": 0, "hit_rate": 0.0, "ci_lower": 0.0, "ci_upper": 0.0,
            "is_significant": False, "avg_net_return": 0.0, "std_net_return": 0.0,
            "tier": 0,
        }

    def _build_result(self, row, setup_type, regime, direction, sector, time_bucket) -> dict:
        n = row.get("n", 0)
        hit_rate = row.get("hit_rate", 0.0)
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)
        if n > 0 and ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(hit_rate, n)
        return {
            "setup_type": row.get("setup_type", setup_type),
            "regime": row.get("regime", regime),
            "direction": row.get("direction", direction),
            "sector": sector,
            "time_bucket": time_bucket,
            "n": n,
            "hit_rate": hit_rate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "is_significant": hit_rate > 0.5 and ci_lower > 0.5,
            "avg_net_return": row.get("avg_net_return", 0.0),
            "std_net_return": row.get("std_net_return", 0.0),
        }
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l10_tiers.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10_tiers.py
git commit -m "feat: implement 6-tier hierarchical fallback in L10 lookup"
```

---

### Task 2: L10 — Replace Bayesian Bootstrap with Beta-Binomial + Fix BH Alpha

**Files:**
- Modify: `engine/layers/l10_edge.py`
- Modify: `tests/test_l10_edge.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestBetaBinomial:
    def test_prior_centered_at_60pct(self):
        from engine.layers.l10_edge import beta_binomial_posterior
        # Prior: Beta(12, 8) → mean = 12/(12+8) = 0.60
        post = beta_binomial_posterior(k=10, n=20, alpha_prior=12, beta_prior=8)
        # Posterior: Beta(12+10, 8+10) = Beta(22, 18) → mean = 22/40 = 0.55
        assert 0.50 <= post["posterior_mean"] <= 0.60
        assert "ci_lower" in post
        assert "ci_upper" in post

    def test_bh_alpha_is_010(self):
        from engine.layers.l10_edge import benjamini_hochberg
        p_values = [0.01, 0.03, 0.05, 0.08, 0.15, 0.30]
        # With alpha=0.10 and m=6: thresholds are k*0.10/6
        # k=1: 0.0167, p=0.01 <= 0.0167 ✓
        # k=2: 0.0333, p=0.03 <= 0.0333 ✓
        # k=3: 0.0500, p=0.05 <= 0.0500 ✓
        # k=4: 0.0667, p=0.08 > 0.0667 ✗
        significant = benjamini_hochberg(p_values, alpha=0.10)
        assert sum(significant) == 3  # first 3 rejected
```

- [ ] **Step 2: Implement Beta-Binomial and fix BH default**

Replace `bayesian_bootstrap` in `l10_edge.py`:

```python
import scipy.stats as stats


def beta_binomial_posterior(k: int, n: int, alpha_prior: float = 12,
                            beta_prior: float = 8, ci_level: float = 0.95) -> dict:
    """Beta-Binomial conjugate update for hit rate.

    Prior: Beta(alpha=12, beta=8) centered at 60% hit rate
    Posterior: Beta(alpha + k, beta + n - k)

    Args:
        k: Number of hits (successes)
        n: Number of trials
        alpha_prior: Prior alpha (default 12 → 60% prior mean with beta=8)
        beta_prior: Prior beta (default 8)
        ci_level: Confidence level for credible interval (default 0.95)

    Returns:
        dict with posterior_mean, ci_lower, ci_upper
    """
    post_alpha = alpha_prior + k
    post_beta = beta_prior + n - k

    posterior_mean = post_alpha / (post_alpha + post_beta)

    # Equal-tailed credible interval
    tail = (1 - ci_level) / 2
    ci_lower = stats.beta.ppf(tail, post_alpha, post_beta)
    ci_upper = stats.beta.ppf(1 - tail, post_alpha, post_beta)

    return {
        "posterior_mean": round(posterior_mean, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "prior_alpha": alpha_prior,
        "prior_beta": beta_prior,
        "posterior_alpha": post_alpha,
        "posterior_beta": post_beta,
        "n_observed": n,
        "k_observed": k,
    }
```

Update `benjamini_hochberg` default alpha to 0.10:

```python
def benjamini_hochberg(p_values: list[float], alpha: float = 0.10) -> list[bool]:
    """Benjamini-Hochberg FDR correction.

    Spec: alpha = 0.10 (not 0.05).
    """
    if not p_values:
        return []
    m = len(p_values)
    sorted_idx = sorted(range(m), key=lambda i: p_values[i])

    k = 0
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            k = rank

    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if rank <= k:
            significant[idx] = True
    return significant
```

Keep `wilson_ci` unchanged (correct).

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l10_edge.py tests/test_l10_tiers.py -v`
Expected: PASS

- [ ] **Step 4: Remove old `bayesian_bootstrap` function and `check_confidence_interval`**

The old `check_confidence_interval` (tautological check) is no longer used by `lookup()`. Remove it. Keep `check_min_samples` but deprecate in favor of per-tier config.

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10_edge.py tests/test_l10_tiers.py
git commit -m "feat: replace Bayesian bootstrap with Beta-Binomial conjugate, fix BH alpha to 0.10"
```

---

### Task 3: L9 — Add CREATED/PENDING States to State Machine

**Files:**
- Modify: `engine/layers/l9_monitor.py`
- Modify: `tests/test_l9_monitor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_l9_states.py
from engine.layers.l9_monitor import L9ShadowLedger
from models.enums import ThesisState


class TestStateMachine:
    def test_created_to_pending_to_triggered_to_active(self):
        ledger = L9ShadowLedger()
        thesis = {
            "thesis_id": "test-1", "symbol": "X", "direction": "LONG",
            "setup_type": 1, "trigger": 100, "invalidation": 95,
            "t1": 110, "t2": 115,
        }
        # 1. on_create: CREATED
        ledger.on_create(thesis)
        assert ledger.theses["test-1"]["state"] == ThesisState.CREATED.value

        # 2. on_pending: PENDING (price approaching trigger)
        ledger.on_pending("test-1")
        assert ledger.theses["test-1"]["state"] == ThesisState.PENDING.value

        # 3. on_trigger: ACTIVE
        ledger.on_trigger("test-1", entry_price=100)
        t = ledger.active["test-1"]
        assert t["state"] == ThesisState.ACTIVE.value
        assert t["entry_price"] == 100

    def test_pending_expiry_by_setup(self):
        ledger = L9ShadowLedger()
        thesis = {
            "thesis_id": "test-2", "symbol": "Y", "direction": "LONG",
            "setup_type": 1,  # ORB_15MIN → expires 11:00 AM
            "trigger": 100, "invalidation": 95, "t1": 110, "t2": 115,
        }
        ledger.on_create(thesis)
        ledger.on_pending("test-2")
        # Expire pending at setup-specific time
        expired = ledger.on_pending_expiry(current_time_str="11:01")
        assert len(expired) == 1
        assert expired[0]["state"] == ThesisState.EXPIRED.value

    def test_pending_does_not_expire_before_time(self):
        ledger = L9ShadowLedger()
        thesis = {
            "thesis_id": "test-3", "symbol": "Z", "direction": "SHORT",
            "setup_type": 2,  # VWAP_RECLAIM → expires 14:00
            "trigger": 100, "invalidation": 105, "t1": 90, "t2": 85,
        }
        ledger.on_create(thesis)
        ledger.on_pending("test-3")
        expired = ledger.on_pending_expiry(current_time_str="13:00")
        assert len(expired) == 0  # Not yet expired
```

- [ ] **Step 2: Implement state machine with CREATED/PENDING states**

```python
# engine/layers/l9_monitor.py (full rewrite)
from datetime import datetime, timezone, time
from typing import List, Optional

from models.enums import ThesisState, SetupType


# Setup-specific pending expiry times (IST)
SETUP_PENDING_EXPIRY = {
    SetupType.ORB_15MIN: time(11, 0),
    SetupType.ORB_2HOUR: time(13, 0),
    SetupType.VWAP_RECLAIM: time(14, 0),
    SetupType.SUPERTREND_PULLBACK: time(14, 30),
    SetupType.MEAN_REVERSION: time(13, 30),
    SetupType.FIRST_HOUR_BREAKOUT: time(12, 0),
    SetupType.CPR_BREAKOUT: time(14, 0),
}

FORCE_EXPIRE_TIME = time(15, 15)


class L9ShadowLedger:
    """Tracks thesis lifecycles: CREATED → PENDING → ACTIVE → terminal."""

    def __init__(self):
        self.theses: dict[str, dict] = {}   # CREATED or PENDING (not yet active)
        self.active: dict[str, dict] = {}   # ACTIVE (triggered)
        self.history: list[dict] = []

    # --- State transitions ---

    def on_create(self, thesis: dict):
        """Register a newly created thesis. State: CREATED."""
        thesis["state"] = ThesisState.CREATED.value
        thesis["created_ts"] = datetime.now(timezone.utc)
        self.theses[thesis["thesis_id"]] = thesis

    def on_pending(self, thesis_id: str):
        """Thesis is approaching trigger. State: PENDING."""
        t = self.theses.get(thesis_id)
        if t:
            t["state"] = ThesisState.PENDING.value
            t["pending_ts"] = datetime.now(timezone.utc)

    def on_trigger(self, thesis_id: str, entry_price: float):
        """Trigger price crossed. State: ACTIVE."""
        t = self.theses.pop(thesis_id, None)
        if t is None:
            return
        t["state"] = ThesisState.ACTIVE.value
        t["entry_ts"] = datetime.now(timezone.utc)
        t["entry_price"] = entry_price
        t["mfe_pct"] = 0.0
        t["mae_pct"] = 0.0
        self.active[thesis_id] = t

    def on_pending_expiry(self, current_time_str: str) -> List[dict]:
        """Expire PENDING theses whose setup time has passed.

        Args:
            current_time_str: Current IST time as "HH:MM" string
        """
        h, m = map(int, current_time_str.split(":"))
        now = time(h, m)
        expired = []
        for tid, t in list(self.theses.items()):
            if t["state"] not in (ThesisState.CREATED.value, ThesisState.PENDING.value):
                continue
            setup = SetupType(t.get("setup_type", 1))
            expiry = SETUP_PENDING_EXPIRY.get(setup, FORCE_EXPIRE_TIME)
            if now >= expiry:
                t["state"] = ThesisState.EXPIRED.value
                t["exit_ts"] = datetime.now(timezone.utc)
                expired.append(t)
                del self.theses[tid]
                self.history.append(t)
        return expired

    # --- Tick processing (ACTIVE → terminal) ---

    async def on_tick(self, price: float) -> List[dict]:
        """Process tick for all ACTIVE theses. Returns list of terminal theses."""
        terminal = []
        for tid, t in list(self.active.items()):
            entry = t.get("entry_price") or t["trigger"]
            raw_pct = (price - entry) / entry * 100

            if t["direction"] == "SHORT":
                raw_pct = -raw_pct

            t["mfe_pct"] = max(t.get("mfe_pct", 0), raw_pct)
            t["mae_pct"] = min(t.get("mae_pct", 0), raw_pct)

            hit = self._check_exits(t, price)
            if hit:
                terminal.append(hit)
                del self.active[tid]
                self.history.append(hit)

        return terminal

    def _check_exits(self, t: dict, price: float) -> dict | None:
        """Check if price crossed T1, T2, or SL. Return terminal thesis or None."""
        if t["direction"] == "LONG":
            if price >= t["t2"]:
                t["state"] = ThesisState.T2_HIT.value
                return self._finalize(t, price)
            elif price >= t["t1"]:
                t["state"] = ThesisState.T1_HIT.value
                return self._finalize(t, price)
            elif price <= t["invalidation"]:
                t["state"] = ThesisState.STOPPED_OUT.value
                return self._finalize(t, price)
        else:  # SHORT
            if price <= t["t2"]:
                t["state"] = ThesisState.T2_HIT.value
                return self._finalize(t, price)
            elif price <= t["t1"]:
                t["state"] = ThesisState.T1_HIT.value
                return self._finalize(t, price)
            elif price >= t["invalidation"]:
                t["state"] = ThesisState.STOPPED_OUT.value
                return self._finalize(t, price)
        return None

    def _finalize(self, t: dict, exit_price: float) -> dict:
        """Record exit and compute outcome metrics."""
        t["exit_price"] = exit_price
        t["exit_ts"] = datetime.now(timezone.utc)

        entry = t.get("entry_price") or t["trigger"]
        invalidation = t["invalidation"]

        # Gross return
        if t["direction"] == "LONG":
            gross_return_pct = (exit_price - entry) / entry * 100
        else:
            gross_return_pct = (entry - exit_price) / entry * 100
        t["gross_return_pct"] = round(gross_return_pct, 4)

        # R-multiple = gross return / |entry - invalidation|
        risk = abs(entry - invalidation)
        risk_pct = risk / entry
        t["r_multiple"] = round(gross_return_pct / (risk_pct * 100), 4) if risk_pct > 0 else 0.0

        # Time to exit
        entry_ts = t.get("entry_ts")
        exit_ts = t["exit_ts"]
        if entry_ts and exit_ts:
            t["time_to_exit_min"] = int((exit_ts - entry_ts).total_seconds() / 60)

        return t

    # --- Force expire ---

    async def on_force_expire(self) -> List[dict]:
        """Expire all active theses at session close (15:15 IST)."""
        expired = list(self.active.values())
        for t in expired:
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            self.history.append(t)
        self.active.clear()

        # Also expire any remaining CREATED/PENDING
        for t in list(self.theses.values()):
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            expired.append(t)
            self.history.append(t)
        self.theses.clear()

        return expired
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_l9_states.py tests/test_l9_monitor.py -v`
Expected: PASS (update old tests to use new state names)

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l9_monitor.py tests/test_l9_states.py tests/test_l9_monitor.py
git commit -m "feat: add CREATED/PENDING states and setup-specific expiry to L9 state machine"
```

---

### Task 4: L9 — Add Conditional Extension + Missing Outcome Metrics

**Files:**
- Modify: `engine/layers/l9_monitor.py`

- [ ] **Step 1: Write the test**

```python
class TestConditionalExtension:
    def test_extension_when_vix_recovering_and_vol_high(self):
        ledger = L9ShadowLedger()
        # Simulate VWAP thesis at 13:55, VIX recovering + vol > 80th pctile
        should_extend = ledger.should_extend(
            setup_type=2, current_time_str="13:55",
            vix_recovering=True, vol_above_80th=True,
        )
        assert should_extend is True

    def test_no_extension_without_conditions(self):
        ledger = L9ShadowLedger()
        should_extend = ledger.should_extend(
            setup_type=2, current_time_str="13:55",
            vix_recovering=False, vol_above_80th=False,
        )
        assert should_extend is False

    def test_extension_only_for_vwap_supertrend(self):
        ledger = L9ShadowLedger()
        # ORB does not qualify for extension
        should_extend = ledger.should_extend(
            setup_type=1, current_time_str="10:55",
            vix_recovering=True, vol_above_80th=True,
        )
        assert should_extend is False
```

- [ ] **Step 2: Implement conditional extension**

Add to `L9ShadowLedger`:

```python
EXTENSIBLE_SETUPS = {SetupType.VWAP_RECLAIM, SetupType.SUPERTREND_PULLBACK}
EXTENSION_MINUTES = 30


def should_extend(self, setup_type: int, current_time_str: str,
                  vix_recovering: bool = False, vol_above_80th: bool = False) -> bool:
    """Check if thesis qualifies for conditional 30-min extension.

    Spec: If VIX recovering from lunch lows + 5-min realized vol > 80th
    percentile of session → extend VWAP/Supertrend expiry by 30 min.
    """
    setup = SetupType(setup_type)
    if setup not in self.EXTENSIBLE_SETUPS:
        return False
    return vix_recovering and vol_above_80th
```

- [ ] **Step 3: Run all L9 tests**

Run: `pytest tests/test_l9_*.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/layers/l9_monitor.py tests/test_l9_states.py
git commit -m "feat: add conditional 30-min extension for VWAP/Supertrend setups"
```

---

### Task 5: L9 — Add Outcome Metrics (Net Return, Time-to-Trigger)

**Files:**
- Modify: `engine/layers/l9_monitor.py`
- Modify: `engine/models/frames.py` (ThesisOutcome already has these fields)

- [ ] **Step 1: Update `_finalize` to compute net return**

```python
def _finalize(self, t: dict, exit_price: float) -> dict:
    """Record exit and compute all outcome metrics."""
    t["exit_price"] = exit_price
    t["exit_ts"] = datetime.now(timezone.utc)

    entry = t.get("entry_price") or t["trigger"]
    invalidation = t["invalidation"]

    # Gross return
    if t["direction"] == "LONG":
        gross_return_pct = (exit_price - entry) / entry * 100
    else:
        gross_return_pct = (entry - exit_price) / entry * 100
    t["gross_return_pct"] = round(gross_return_pct, 4)

    # Net return (after costs, if cost_breakdown available)
    cost_pct = 0.0
    cost_breakdown = t.get("cost_breakdown", {})
    if cost_breakdown:
        cost_pct = cost_breakdown.get("cost_pct", 0.0)
    t["net_return_pct"] = round(gross_return_pct - cost_pct, 4)

    # R-multiple
    risk = abs(entry - invalidation)
    risk_pct = risk / entry
    t["r_multiple"] = round(gross_return_pct / (risk_pct * 100), 4) if risk_pct > 0 else 0.0

    # Time-to-trigger (from created to entry)
    created_ts = t.get("created_ts")
    entry_ts = t.get("entry_ts")
    if created_ts and entry_ts:
        t["time_to_trigger_min"] = int((entry_ts - created_ts).total_seconds() / 60)

    # Time-to-exit (from entry to exit)
    exit_ts = t["exit_ts"]
    if entry_ts and exit_ts:
        t["time_to_exit_min"] = int((exit_ts - entry_ts).total_seconds() / 60)

    return t
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_l9_*.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add engine/layers/l9_monitor.py
git commit -m "feat: add net return and time-to-trigger/exit outcome metrics"
```
