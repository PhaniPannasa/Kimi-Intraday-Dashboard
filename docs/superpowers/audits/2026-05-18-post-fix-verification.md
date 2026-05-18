# Post-Fix Verification — Engine L1-L10

**Date:** 2026-05-18
**Audit basis:** systematic-debugging skill, Phase 1-4 protocol
**Scope:** Verify every fix in 18 commits + uncommitted L1/frames work addresses the root cause from the 2026-05-17 gap analysis and the 6 spec-design critiques
**Test status:** 201 tests passing
**Verdict:** **Substantial progress; 2 new bugs introduced; 2 layers untouched.** Tests passing ≠ spec-compliant — three of the issues below would not be caught by current tests.

Severity legend: 🔴 trading-correctness-affecting · 🟡 partial fix or unused-feature · 🟢 cosmetic · ✅ properly fixed · ❌ not addressed

---

## Executive summary

| Layer | Status | Highlights |
|---|---|---|
| L1 | ✅ mostly fixed | Range-Bound reachable, breadth normalized, diurnal vol, cold-start, dynamic output fields |
| L2 | ❌ untouched | All original gaps remain (hardcoded circuit/staleness/index_change) |
| L3 | ✅ math fixed; ⚠️ integration | Six new modules with correct math; legacy `L3Signals.compute()` still uses single-TF wrapper |
| L4 | ❌ untouched | `max(nifty_return, 0.0001)` divisor bug, no rotation tracking, no rank-change |
| L5 | ✅ direction-aware + ❌ critique #3 mis-fixed | F1-F7 invert for SHORT correctly; collinearity removed (#4 ✅); **but the short × 0.92 no-op is still a no-op — just moved into weights** |
| L6 | ❌ hysteresis dead code | Adaptive θ + concentration metrics work; **hysteresis gate condition is logically impossible after sort** |
| L7 | ✅ unchanged | Still spec-compliant |
| L8 | ✅ mostly + 🔴 stop-slippage unit bug | All 6 setups, correct cost rates, continuous slippage, spec Net R:R formula; **but caller passes `bps / 10000` to a function expecting %, making slippage 100× too small** |
| L9 | ✅ mostly fixed | Full state machine, setup-specific expiry, outcome metrics; minor: should_extend unused, MFE/MAE timestamps still missing, net_return uses simplified formula |
| L10 | ✅ mostly fixed | 6-tier fallback, correct per-tier n + CI gates, Beta-Binomial with Beta(6,6) prior |

**Spec critiques 1–6:** 4 properly fixed (#1, #2, #4, #5, #6), 1 mis-fixed (#3).

---

## L1 — Market Context — ✅ mostly fixed

### Properly fixed
- ✅ **Range-Bound now reachable.** `if abs(latest_slope) < SLOPE_THRESHOLD: return RANGE_BOUND, 0.6` with `SLOPE_THRESHOLD = 0.0003`. Was previously requiring `slope == 0` exactly.
- ✅ **A/D ratio bounded.** `ad_norm = advancers / (advancers + decliners)` now ∈ [0, 1]. Equivalent to your proposed `(A-D)/(A+D)` rescaled.
- ✅ **H/L is genuinely new highs/lows.** Counts stocks closing at session high vs session low, normalized by total H+L.
- ✅ **Advancers vs prev close.** New code prefers `prev_close` column; falls back to session open only if column missing.
- ✅ **Cold-start logic.** `should_use_cold_start(now)` checks if before 10:45 IST → uses 9-bar EMA on 15-min bars per spec.
- ✅ **VIX history bounded.** `if len(self.vix_history) > 90: self.vix_history = self.vix_history[-90:]`.
- ✅ **Dynamic output fields.** `volatility_qualifier`, `vix_trajectory`, `time_bucket` all computed from data/clock.
- ✅ **Spec critique #1 properly addressed.** `compute_vol_z_diurnal()` buckets historical vol by 5-min time-of-day index and compares current to same-bucket distribution. Correctly addresses the intraday U-shape bias.
- ✅ **Spec critique #2 properly addressed.** A/D and H/L both bounded.

### Caveats
- 🟡 **`SLOPE_THRESHOLD = 0.0003` is absolute, not relative.** On Nifty ≈ 22,000, this is essentially the floating-point noise floor for a 5-bar EMA diff. Range-Bound will trigger only on dead-flat sessions. Should ideally be a percentage of price (e.g., 0.05%).
- 🟡 **VIX history cap of 90 has ambiguous unit.** Spec says "trailing 90 days," but `compute()` appears to be called per-tick or per-cycle. If called every minute, cap of 90 = 90 minutes, not 90 days. Worth verifying call cadence at pipeline integration.
- 🟡 **`premarket_bias`, `bank_nifty_divergence`, `event_flag` now passed in as parameters** — better architecture, but L1 itself never derives them. The 6 AM global-cues fetch (`fetch_global_cues()` per scheduler) needs to populate them via the pipeline. Verify upstream plumbing.
- 🟢 **Diurnal bucket math assumes contiguous sessions** (`range(current_bucket, len(vol), n_buckets)` indexes by 75-step). If the DataFrame has gaps between sessions, buckets won't align. Check data construction.

---

## L2 — Universe — ❌ untouched

No commits touched `l2_universe.py`. All original audit findings still hold:
- 🔴 `circuit_proximity`, `index_change`, `stale_data` hardcoded to "None" / False
- 🔴 `enrich()` is a parameter passthrough; no actual data fetching
- 🟡 `shortability` binary only (no SLB availability for cash-only shorts)

This is the **most under-served layer in the fix work**.

---

## L3 — Signals — ✅ math fixed; ⚠️ integration gap

### Properly fixed
- ✅ **Dual-timeframe indicators** in `l3_indicators.compute_indicators_single_tf(df, suffix)` — produces `ema_9_5m`, `ema_9_15m`, etc. `compute_all_indicators` joins both timeframes.
- ✅ **ROC vs Nifty.** `result["roc_vs_nifty"] = result["roc_20_stock"] - result["roc_20_nifty"]` when Nifty df is supplied.
- ✅ **ATR percentile.** Rolling 20-day window (20×75 5-min bars or 20×25 15-min bars), counts historical ATRs below current to give percentile rank. Math correct.
- ✅ **MACD divergence as 5-bar pattern** (not point-to-point). `prices[-5:].min() < prices[-10:-5].min() and macd_hist[-5:].min() > macd_hist[-10:-5].min()` for long.
- ✅ **Volume seasonality.** `compute_seasonal_profile` builds a 75-bucket profile from historical volumes; `adjust_volume` computes V_adj = raw / seasonal; `compute_volume_confirm(v_adj, median_adj)` checks ≥ 1.5×.
- ✅ **Reference levels.** All present: floor pivots (R1-R3, S1-S3), CPR (Pivot/BC/TC + width), ORB (15-min + 2-hour), FH high/low, PDH/PDL/PDC.
- ✅ **Options derivatives.** IV percentile, expected range (ATM × IV / √(252/days)), PCR z-score, RV/IV ratio. Formulas match spec.

### Integration concern
- 🟡 **Legacy `L3Signals.compute(df)` still uses single-TF wrapper.** It calls `compute_indicators(df)` which delegates to `compute_indicators_single_tf(df, suffix="5m")` and strips the suffix. The new dual-TF, options, reference levels, and seasonality modules **must be invoked by the pipeline directly** — they're not surfaced through `L3Signals`.
- 🟡 IV percentile and PCR z-score don't separate 60-day vs 1-year (spec calls out both windows); single history list parameter.

Need to verify `pipeline.py` calls the new modules. (Not in this scope; flag for cross-check.)

---

## L4 — Sector — ❌ untouched

No commits touched `l4_sector.py`. All original audit findings still hold:
- 🔴 `max(nifty_return, 0.0001)` divisor breaks RS-Ratio on negative-Nifty days
- 🔴 Single horizon (no 5-day + 20-day split per spec)
- 🔴 `compute_rs_momentum(hist)` is passed sector return history, not RS-Ratio history
- 🔴 No 30-min rank-change tracking
- 🔴 No rotation classification (Gaining / Steady / Losing)

The 11-sector list is confirmed correct.

---

## L5 — Scoring — ✅ direction-aware + ❌ critique #3 mis-fixed

### Properly fixed
- ✅ **All 7 factors now take `direction`** and invert for SHORT:
  - F1: long=`supertrend_bull` scores +50; short=`not supertrend_bull` scores +50
  - F2: long=RSI 40-70; short=RSI 30-60; ROC z sign flipped
  - F3: long=above_vwap; short=below_vwap; `vol_z` uses `abs()`
  - F4: long=lower BB position better; short=upper BB position better
  - F5: long=lower RS rank better; short=lower RS rank worse
  - F7: long=lower pos_52w better; short=higher pos_52w better
- ✅ **Liquidity multiplier applied.** `s_liq = raw * liq_mult` (default 1.0; caller-supplied).
- ✅ **Stale-data freeze.** Returns cached `_frozen_scores[symbol]` when `stale_data=True`.
- ✅ **`index_change` modifier applied** (was previously defined but unused).
- ✅ **Spec critique #4 addressed** — F1 no longer uses `ema_aligned` (decoupled from L7 Check 4); F3 no longer uses `vol_confirm` (decoupled from L7 Check 2). At the cost of slight spec divergence (F1/F3 no longer include those inputs).

### Not actually fixed
- ❌ **Spec critique #3 NOT genuinely addressed.**

  The commit `bb9052c` claims to "integrate short penalty into factor weights," but mathematically this is **identical** to the old end-of-pipeline multiplier:

  Old code: `final = clamp(sum(w_i × F_i) + modifiers) × 0.92`
  New code: `final = clamp(0.92 × sum(w_i × F_i) + modifiers)`

  The 0.92 is still a uniform scalar on the weighted sum, only with the order of operations swapped against the modifier addition. Since all shorts undergo the same transformation, the **Top-25-Short ordinal ranking is still preserved exactly** — the original critique stands.

  To genuinely address #3, you'd need one of:
  - Asymmetric per-stock penalties (e.g., based on SLB cost, hard-to-borrow flag, MWPL proximity)
  - Apply the penalty as a threshold in actionability tier rather than a score scalar
  - Bake direction asymmetry into the FACTOR formulas themselves (not the weights), so some factors penalize shorts more than others

### Caveats
- 🟡 **Stale fallthrough on first call.** If `stale_data=True` on the very first observation, no cached value exists → falls through to compute new (stale) score. Spec says "Score frozen" — implies prior value.

---

## L6 — Ranking — ❌ hysteresis dead code

### Properly fixed
- ✅ **Adaptive σ_gap computation.** `compute_adaptive_theta(scores_20_30)` computes std dev of consecutive score gaps in ranks 20-30 and returns `max(2.0, 0.25 × σ_gap)`. Math matches spec.
- ✅ **Concentration metrics (2 of 3).** `sector_concentration` (max single-sector count), `is_theme_day` (> 8), `score_spread`, `is_high_conviction` (> 20). Matches spec thresholds.
- ✅ **5-tick movement window.** `_rank_history` retains up to 10 entries per symbol; `compute_rank_movement` looks back ≥ 5 ticks. Approximates spec's 5-minute window (if `rank()` is called once per minute).

### Not actually fixed
- 🔴 **Hysteresis enforcement is dead code.** The gate:
  ```python
  if len(scored_stocks) > self.top_n:
      rank_25_score = top_n_candidates[-1]["score"]
      rank_26_score = scored_stocks[self.top_n]["score"]
      if rank_26_score > rank_25_score + self.theta:
          top_n_candidates[-1] = scored_stocks[self.top_n]
  ```
  Since `scored_stocks` is sorted descending and `top_n_candidates = scored_stocks[:25]`, by construction `rank_26_score ≤ rank_25_score`. The condition `rank_26 > rank_25 + θ` is **never true**.

  **Empirically verified:** Set stock at input index 25 to score 50 points above index 24 → after sort, that stock becomes a high rank (#1 in fact), making the condition still impossible.

  The spec hysteresis intent is **sticky-boundary anti-churn**: a symbol *currently in top 25* should not be displaced unless the challenger's score exceeds it by θ. This requires comparing the **current sort against the previous top-25 membership**, not against the same sort's own boundary.

  Correct implementation skeleton:
  ```python
  prev_top_25 = set(self.previous_ranks.keys())
  new_top_25 = [s for s in scored_stocks[:25]]
  new_symbols = {s["symbol"] for s in new_top_25}
  for incumbent in scored_stocks[25:35]:
      if incumbent["symbol"] in prev_top_25 and incumbent["symbol"] not in new_symbols:
          # Incumbent dropped out of natural top 25 — does the boundary new entry exceed it by θ?
          boundary_new = next(s for s in new_top_25 if s["symbol"] not in prev_top_25)
          if boundary_new["score"] - incumbent["score"] < self.theta:
              # Keep incumbent, displace the marginal new entry
              new_top_25.remove(boundary_new)
              new_top_25.append(incumbent)
  ```

- 🟡 **Adaptive θ has no rate-feedback ±10%.** Spec says: "If rate > 1/min: θ += 10%, if rate < 0.5/min: θ -= 10%." Code recomputes from σ_gap each call but doesn't track rank-change rate over time.
- 🟡 **Correlation cluster missing.** Spec defines a third concentration metric (cosine similarity > 0.70 pair count); not in code.

---

## L7 — Confluence — ✅ unchanged

All 6 checks still pass spec audit. Note: the L5-L7 decoupling was done by **removing inputs from L5**, not by adding orthogonal checks to L7. L7 itself is untouched and still spec-correct.

---

## L8 — Thesis — ✅ mostly + 🔴 stop-slippage unit bug

### Properly fixed
- ✅ **All 6 setups implemented.** `l8_setups/{orb_15, vwap_reclaim, supertrend_pullback, mean_reversion, first_hour_breakout, cpr_breakout}.py` with dispatch via `SETUP_ASSEMBLERS`. Spot-checked levels:
  - ORB-15: trigger ORB high + tick, invalidation `max(ORB Low, VWAP × 0.995)`, T1 = trigger + 1.5×range, **T2 = PDL for shorts** (the PDH-for-both bug is fixed)
  - VWAP Reclaim: VWAP ± tick, invalidation VWAP ∓ 0.8×ATR, T1 = VWAP ± 1.5×ATR, T2 = VWAP ± 2.5×ATR
  - Mean Reversion: trigger near 2σ BB, invalidation at 2.5σ, T1 = max(VWAP, trigger + 0.6×|trigger-inv|), T2 = opposite 1σ band
  - All matches spec.
- ✅ **Setup-specific clock-based valid_until.** `get_setup_expiry()` returns 11:00 for ORB-15, 14:00 for VWAP, 14:30 for ST, 13:30 for MR, 12:00 for FH, 14:00 for CPR. Matches spec L9 table.
- ✅ **Cost-model rates all corrected** (was the most broken layer pre-fix):
  | Charge | Spec | New code | Status |
  |---|---|---|---|
  | Brokerage equity | 0.03% capped ₹20 | 0.0003 capped 20.0 | ✅ |
  | Brokerage futures | flat ₹20/leg | flat × 2 | ✅ |
  | STT equity | 0.025% sell-only | 0.00025 sell-only | ✅ |
  | STT futures | 0.0125% sell-only | 0.000125 sell-only | ✅ |
  | Exchange equity | 0.00297% | 0.0000297 | ✅ |
  | Exchange futures | 0.00173% | 0.0000173 | ✅ |
  | SEBI | 0.0001% | 0.000001 | ✅ |
  | Stamp equity | 0.003% buy-only | 0.00003 buy-only | ✅ |
  | Stamp futures | 0.002% buy-only | 0.00002 buy-only | ✅ |
  | GST | 18% on (brk+exch+SEBI) | 0.18 | ✅ |
- ✅ **Slippage table matches spec** (Excellent 5/+8, Good 10/+15, Marginal 20/+25, Poor 35/+40 bps).
- ✅ **Spec critique #6 addressed.** `compute_slippage_continuous(lqs, is_stop)` linearly interpolates between bucket midpoints (Poor 0.15 / Marginal 0.425 / Good 0.675 / Excellent 0.90). LQS=0.55 → 15.0 bps, LQS=0.54 → 15.4 bps. Smooth transition.
- ✅ **`compute_net_rr` formula matches spec exactly:**
  ```python
  net_reward = gross_reward - (cost_factor * trigger)
  net_risk = gross_risk + (slip_factor * trigger)
  ```
- ✅ **Time-decay formula matches spec:** `M(t) = exp(-λ × max(0, t - t_window)²)` with correct λ per setup (0.0003 ORB-family, 0.00015 ST/VWAP/CPR/MR).
- ✅ **Actionability tier** implemented with spec criteria (Tradeable / Constrained / Research-Only), including cash-only-short → Research-Only and confluence ≥ 3 gate for Tradeable.

### Critical regression
- 🔴 **Stop-slippage unit conversion bug at the L8Thesis.assemble call site.**

  `l8_thesis.py:149`:
  ```python
  rr = compute_net_rr(
      ...,
      cost_pct=costs["cost_pct"],          # in % (e.g., 0.06 for 0.06%)
      stop_slippage_pct=stop_slip_bps / 10000.0,  # converts bps to FRACTION (0.0025)
  )
  ```

  But `compute_net_rr` does `slip_factor = stop_slippage_pct / 100.0` — assumes input is **percentage** and divides by 100 to get fraction. Same as `cost_factor = cost_pct / 100.0`.

  Net effect: slip_factor is 100× too small. Empirically verified:

  | Test case | Computed | Spec-correct |
  |---|---|---|
  | Trigger=1000, T1=1010, Invalid=995, Good liquidity (stop_slip=25bps), futures cost ≈ 0.06% | Net R:R = **1.87** | Net R:R = **1.25** |

  This **49% overstatement** of Net R:R means theses that should be MARGINAL (1.25, grade Amber) are being graded ATTRACTIVE (1.87, grade Green). The actionability-tier logic that gates Tradeable on `net_rr >= 1.0` is also affected.

  **Root cause:** unit mismatch. Either change the caller to `stop_slip_bps / 100.0` (bps → %), or change `compute_net_rr` to expect fraction directly (remove the internal `/ 100.0`). The former is more consistent with `cost_pct` semantics.

  **Why tests didn't catch it:** the L8 cost-model tests likely call `compute_net_rr` directly with units chosen to validate the formula, not the integration via `L8Thesis.assemble`. An end-to-end test asserting "for these inputs, net_rr should be ≈ X" would have failed.

### Caveat
- 🟡 **Time-decay called only at thesis creation.** `compute_time_decay(setup_enum.name, minutes_since_creation=0)` is invoked once in `assemble()`; multiplier is always 1.0 at creation. No code path updates the multiplier as time elapses. Pipeline or L9 needs to periodically recompute and apply.
- 🟡 ORB_2HOUR not in setup_expiry_times map (falls back to FORCE_EXPIRE=15:15); spec lists 13:00.

---

## L9 — Monitor — ✅ mostly fixed

### Properly fixed
- ✅ **Full state machine:** CREATED → PENDING → ACTIVE → {T1_HIT | T2_HIT | STOPPED_OUT | EXPIRED | FORCE_EXPIRED}. Each transition has its own method (`on_create`, `on_pending`, `on_trigger`, `on_tick`, `on_pending_expiry`, `on_force_expire`).
- ✅ **Setup-specific pending expiry.** `SETUP_PENDING_EXPIRY` maps each setup to its session-time cutoff per spec.
- ✅ **Gross return, time-to-trigger, time-to-exit** all computed in `_finalize`.
- ✅ **MFE/MAE tracking** preserved with correct sign-flip for SHORT.

### Caveats
- 🟡 **`should_extend()` defined but unused.** The conditional 30-min extension function exists but `on_pending_expiry()` doesn't consult it before expiring VWAP/ST setups. Wire it up: `if not (now >= expiry and not self.should_extend(...)): continue`.
- 🟡 **Net return uses a simplified formula.** `net_return_pct = gross_return_pct - cost_pct` mixes units: gross_return_pct is % of entry, but cost_pct is % of turnover. Approximately right if exit ≈ entry, but diverges for theses with large moves. Spec L8 Net Reward formula is more precise; should use it.
- 🟡 **R-multiple uses gross return, not net.** Spec: `R-Multiple = Net Return / |Entry - Invalidation|`. Code uses gross. For high-cost-pct shorts this overstates R.
- 🟡 **MFE/MAE timestamps still not tracked.** Spec wants both magnitude and time-of-MFE/time-of-MAE.
- 🟡 **ORB_2HOUR not in pending-expiry map** (falls back to FORCE_EXPIRE).

---

## L10 — Edge Lookup — ✅ mostly fixed

### Properly fixed
- ✅ **Six-tier hierarchical fallback** in `lookup()`. Traverses T1→T6 with correct degeneration order: drop sector → drop bucket → drop regime → keep setup → global. Matches spec.
- ✅ **Per-tier n thresholds match spec exactly:** 30 / 40 / 50 / 50 / 80 / 50.
- ✅ **CI width gates implemented** via `check_ci_width()`. Per-tier half-widths: 0.15 / 0.14 / 0.14 / 0.14 / 0.12 / 0.14 match spec.
- ✅ **Beta-Binomial conjugate posterior** via `beta_binomial_posterior(k, n, alpha_prior=6, beta_prior=6)` using `scipy.stats.beta.ppf` for CI bounds. The previous Dirichlet-on-returns implementation is gone.
- ✅ **Spec critique #5 addressed.** Beta(6, 6) prior centered at 50% with sample strength 12. Close to your proposed Beta(5, 5) — agnostic and weak.
- ✅ **BH FDR alpha = 0.10 default** (was 0.05).
- ✅ **Wilson CI** still correct.

### Caveat
- 🟡 **BH FDR utility not integrated into `is_significant` determination.** `_build_result` sets `is_significant = (hit_rate > 0.5 and ci_lower > 0.5)` — a per-cell heuristic without multiple-testing correction. To actually apply BH across cells, you'd need to compute p-values for all cells in a tier and call `benjamini_hochberg(p_values, 0.10)` to set the significance flags. Currently the utility exists but isn't part of the pipeline.

---

## Spec critiques verification

| # | Critique | Status |
|---|---|---|
| 1 | Vol z-score ignores intraday seasonality | ✅ Properly fixed in L1 (`compute_vol_z_diurnal` time-bucketed baseline) |
| 2 | Undefined A/D normalization in breadth | ✅ Properly fixed in L1 (`ad_norm = advancers / (advancers + decliners)`) |
| 3 | Short × 0.92 is a ranking no-op | ❌ **NOT actually fixed.** Moved 0.92 into weights but mathematically identical scalar on all shorts. Top-25-Short ordering unchanged. |
| 4 | L5 ↔ L7 collinearity | ✅ Addressed by removing EMA from F1 and vol_confirm from F3 (at cost of slight spec divergence) |
| 5 | Beta(12, 8) prior too optimistic | ✅ Replaced with Beta(6, 6) — agnostic 50% prior, weak strength 12 |
| 6 | Slippage step-function cliffs | ✅ Continuous LQS interpolation between bucket midpoints |

---

## New bugs introduced

| # | Layer | Severity | Description |
|---|---|---|---|
| N1 | L8 | 🔴 | Stop-slippage unit conversion: caller passes `bps / 10000` (fraction) to function expecting `%`. Result: slippage in Net R:R is 100× too small, overstating Net R:R by ~50% in typical cases. **Net R:R = 1.87 vs spec-correct 1.25** for the verification case. |
| N2 | L6 | 🔴 | Hysteresis gate condition `rank_26 > rank_25 + θ` is logically impossible after sort. Dead code; provides zero anti-churn enforcement. |
| N3 | L8 | 🟡 | `compute_time_decay` invoked only with `minutes_since_creation=0`; multiplier always 1.0. No code path updates as time elapses. |
| N4 | L9 | 🟡 | `should_extend()` function defined but never invoked in `on_pending_expiry`; the conditional 30-min extension for VWAP/ST is decoupled and dead. |
| N5 | L10 | 🟡 | `benjamini_hochberg` utility exists but not integrated into `is_significant` determination; hardcoded heuristic used instead. |

---

## Still-open gaps (from original audit, not addressed)

| Layer | Gap |
|---|---|
| L2 | All flag fields hardcoded (`circuit_proximity`, `index_change`, `stale_data`); enrich() is parameter passthrough |
| L3 | New modules not wired through `L3Signals.compute()` orchestrator (only invocable directly from pipeline) |
| L4 | `max(nifty_return, 0.0001)` divisor; no rotation classification; no rank-change tracking; single horizon |
| L5 | First-call stale-data path falls through to fresh compute (no prior cached value) |
| L6 | Correlation-cluster concentration metric; θ rate-feedback ±10% adjustment |
| L9 | MFE/MAE timestamps; net_return uses simplified formula; R-multiple uses gross |
| L10 | Tier promotion event emission |

---

## Recommended remediation order

1. 🔴 **Fix L8 stop-slippage unit conversion** (`l8_thesis.py:149`). One-line change: `stop_slippage_pct=stop_slip_bps / 100.0` instead of `/ 10000.0`. Add an integration test asserting Net R:R ≈ 1.25 for the documented case to lock it in.
2. 🔴 **Fix L6 hysteresis** to actually enforce sticky-boundary anti-churn. Compare current sort against previous top-25 membership, not against the same sort's own boundary. Add a test where rank 26 should be excluded despite slight score advantage.
3. 🔴 **Decide on critique #3.** Either accept the 0.92 as cosmetic and document it, or replace with per-stock asymmetric penalties (SLB cost, hard-to-borrow flag).
4. 🟡 **Wire `compute_time_decay` into a periodic update loop** (L9 on_tick or a separate scheduled job updates `thesis.time_decay_multiplier`).
5. 🟡 **Wire `should_extend` into `on_pending_expiry`** so VWAP/ST setups actually extend.
6. 🟡 **L9 net_return + R-multiple precision fixes.**
7. 🟡 **L3 pipeline integration**: verify `pipeline.py` calls the new dual-TF / seasonality / reference-level / options modules directly (not via the single-TF `L3Signals.compute`).
8. 🟡 **L2 + L4** — address still-open original audit gaps (data plumbing for L2, RS-Ratio denominator + rotation for L4).
9. 🟢 **L10 BH FDR integration**: replace hardcoded `is_significant` heuristic with cross-cell BH application.
10. 🟢 **Tighten L1 SLOPE_THRESHOLD** to a relative threshold (% of price).

---

## Verification methodology

- All findings reproducible by reading the files at `engine/layers/*.py` against the current HEAD (`832bdd4`) + uncommitted changes to `l1_market_context.py` and `frames.py`.
- L8 stop-slippage and L6 hysteresis bugs verified empirically with inline Python scripts (transcript in conversation).
- 201 tests pass; the bugs exist because no test covers the specific integration path or invariant that would have detected them.
- Audit scope: code-vs-spec algorithm fidelity (sections 5.1-5.10 of `system_design_final.md`) + the 6 spec-design critiques previously raised.
