# Engine vs. `system_design_final.md` — Gap Analysis

**Date:** 2026-05-17
**Scope:** Full algorithm sweep L1-L10 (per user request)
**Method:** Serena LSP symbol reads + direct file reads, compared against spec sections 5.1-5.10
**Verdict:** Skeleton complete (all 10 layer files present, frames/enums defined) but **multiple correctness-affecting gaps** in the math. The "MVP1 feature complete" memory describes presence, not spec-fidelity.

Severity legend: 🔴 correctness-affecting · 🟡 feature-incomplete · 🟢 minor/cosmetic

---

## Executive summary

| Layer | Spec match | Critical gaps |
|---|---|---|
| L1 Market Context | partial | Range-Bound unreachable; cold-start logic missing; 4 output fields hardcoded |
| L2 Universe | stub | LQS formula ✅; but 3 flag fields hardcoded; no live circuit/staleness tracking |
| L3 Signals | partial | Single timeframe (no 15m); ROC is not Nifty-relative; no volume seasonality; no reference levels; no options derivatives |
| L4 Sector | partial | Single horizon; broken denominator for negative Nifty; no rank-change/rotation tracking |
| L5 Scoring | mostly ✅ | Weights and modifiers correct; **but factor scoring is long-bias only — shorts get wrong factor values**; liquidity multiplier and stale-data freeze missing |
| L6 Ranking | partial | Hysteresis declared (θ=2.0) but **never enforced**; no σ_gap adaptation; no concentration metrics |
| L7 Confluence | ✅ | All 6 checks implemented with correct thresholds |
| L8 Thesis | severe gaps | **Only 1 of 6 setups** (ORB 15-min); cost model rates wrong (STT/exchange/SEBI off by orders of magnitude); slippage missing; Net R:R formula wrong shape; time-decay wrong formula |
| L9 Monitor | partial | MFE/MAE works; but **no R-multiple, no net return, no time-to-X**; no setup-specific pending expiry; conditional extension missing |
| L10 Edge | partial | Wilson CI ✅; **but no 6-tier fallback** (single-key lookup); wrong default n threshold (15 vs spec 30-80); Bayesian bootstrap implements wrong concept (Dirichlet on returns vs Beta-Binomial on hit rate) |

**Net assessment:** L7 is the only layer that genuinely matches spec. L5 weights match but factor inversion logic is missing. L8 has the most severe gaps and would produce incorrect trading output today.

---

## L1 — Market Context (`engine/layers/l1_market_context.py`)

### Matches spec
- 20-bar realized vol on returns ✅
- 60-day baseline z-score (using `60 * 75` 5-min bars as proxy for 60 trading days) ✅
- 50-bar EMA + slope (`diff(5)`) ✅
- VIX percentile bands at 20th/80th ✅
- Breadth formula skeleton: `0.5×VWAP_pct + 0.25×A_D + 0.25×H_L` ✅
- 3-state regime enum ✅

### Gaps
- 🔴 **Range-Bound regime is essentially unreachable.** `classify_regime` returns RANGE_BOUND only when `latest_slope == 0` exactly — every other path returns TRENDING_UP or TRENDING_DOWN. In live tick data, a slope of 0.0001 still classifies as Trending-Up.
- 🔴 **A/D ratio in breadth not normalized.** `ad_ratio = advancers / max(decliners, 1)` is unbounded [0, ∞). On a strong day with 90 advancers / 10 decliners, ad_ratio=9, and `B = 0.5 + 2.25 + 0.25 ≈ 3.0` — the 0.60/0.40 thresholds become meaningless.
- 🔴 **H/L ratio mislabeled.** Code computes `hl_ratio = advancers / total` — that's the advancer percentage, not new-high / new-low ratio per spec.
- 🔴 **Advancer/decliner computed vs session-open, not previous close.** `df["close"].head(1)` reads the session's first bar; spec wants up-on-the-day (vs PDC).
- 🔴 **No cold-start / 15-min EMA logic.** Spec mandates 9-bar EMA on 15-min bars from 9:15-10:45, then switch to 50-bar 5-min. Code unconditionally uses 50-bar EMA — under-determined for the first 90 minutes of the session.
- 🟡 **VIX history unbounded.** `self.vix_history.append(...)` grows forever; spec wants trailing 90 days. Also lost on restart (no persistence).
- 🟡 **Four output fields hardcoded:**
  - `volatility_qualifier = "Normal"` (never set to "Volatile")
  - `vix_trajectory = "Stable"` (never "Rising"/"Falling")
  - `time_bucket = "Trend Establishment"` (never derived from clock)
  - `premarket_bias = "Neutral"` (no global-cues integration despite `fetch_global_cues` job in scheduler)
- 🟡 **`bank_nifty_divergence` and `event_flag` never populated** by `L1MarketContext.compute()` (default 0.0 / None persists).

---

## L2 — Universe (`engine/layers/l2_universe.py`)

### Matches spec
- LQS formula: `0.4×D_norm + 0.35×S_norm + 0.25×T_norm` ✅
- Buckets: Excellent ≥0.80, Good 0.55-0.79, Marginal 0.30-0.54, Poor <0.30 ✅
- Percentile-rank computation (with spread inverted via `1 - pctile`) ✅

### Gaps
- 🔴 **`L2Universe.enrich()` is a parameter passthrough, not enrichment.** All flags are passed in by caller. No data fetched here.
- 🔴 **Three flag fields hardcoded:**
  - `circuit_proximity = "None"` — no consumption of Upstox WS `ExtendedFeedDetails` uc/lc fields
  - `index_change = "None"` — no recent index-change tracking
  - `stale_data = False` — no >30s staleness gate
- 🟡 **`shortability` is binary** (`FUTURES_OPTIONS` vs `CASH_ONLY`) — spec's actionability-tier logic ("cash-only short with no SLB → Research-Only") implies SLB availability check, not modeled.
- 🟡 Where the data should arrive (NSE scraper, WS ExtendedFeedDetails) the files exist (`core/data/nse_scraper.py`, `core/data/upstox_ws.py`) but the orchestration in `pipeline.py` doesn't visibly plumb them into `L2Universe.enrich()` — needs verification by tracing call sites.

---

## L3 — Signals (`engine/layers/l3_signals.py`)

### Matches spec
- EMA(9/20/50) ✅
- Supertrend(10, 3.0) ✅ params
- ADX(14) ✅
- RSI(14) ✅
- MACD(12,26,9) histogram ✅
- ATR(14) ✅
- Bollinger Bands(20, 2σ) ✅
- OI classification thresholds (±0.5% price × ±2% OI) ✅

### Gaps
- 🔴 **Single timeframe only.** `L3Signals.compute(df)` runs `compute_indicators(df)` once on whatever's passed. Spec requires both 5-min AND 15-min for EMA stack, ADX, RSI, MACD.
- 🔴 **`roc_20` is plain ROC, not ROC vs Nifty.** Spec says "Stock return - Nifty return". Code: `df["close"].pct_change(20) * 100`.
- 🔴 **No ATR percentile.** Spec wants ATR vs 20-day distribution percentile rank. Code's `atr_pct = atr / close * 100` is ATR-as-%-of-price, not a distributional percentile.
- 🔴 **No volume seasonality.** Spec: `V_seasonal(t)` (10-day avg per 5-min bucket) → `V_adj = V_raw / V_seasonal(t)` → z-score on V_adj + `V_confirm` (V_adj ≥ 1.5× median adjusted). Code's `compute_volume_zscore` is a generic z-score on raw vol with caller-provided μ/σ.
- 🔴 **No reference levels.** PDH, PDL, PDC, CP/BC/TC (CPR), Floor Pivots R1-3/S1-3, ORB 15-min H/L, ORB 2-hour H/L, First Hour H/L — none implemented in L3. Spec specifies these are "computed at 9:15 AM, fixed for session" — no equivalent symbol in code.
- 🔴 **No options-derived signals.** Missing entirely:
  - IV Percentile (60-day + 1-year)
  - Expected Range: ATM ± (IV/√252) × ATM
  - PCR z-score split by 20-day vs 1-year (code's `compute_pcr_zscore` takes generic `pcr_history` list)
  - RV/IV Ratio
- 🟡 **MACD divergence is simplified.** Spec: "Price 5-bar lower low AND MACD 5-bar higher low" (i.e., find low within window). Code: `prices[-5] > prices[-1] AND macd_hist[-5] < macd_hist[-1]` (point-to-point). Direction is right; precision is loose.
- 🟢 **No 15-min OI smoothing.** Spec mentions OI classification uses 15-min smoothing; code applies directly.
- 🟢 **Supertrend distance-to-flip missing.** Spec output is "Direction + distance to flip"; code only exposes direction.

---

## L4 — Sector (`engine/layers/l4_sector.py`)

### Matches spec
- 11 sectors enumerated: Auto, Bank, FMCG, IT, Media, Metal, Pharma, PSU Bank, Realty, Energy, Telecom ✅
- RS-Ratio formula shape ✅ (sector_return / nifty_return / rolling_std)
- RS-Momentum as 5-day diff ✅ (in spirit)
- Rank by RS-Ratio ✅

### Gaps
- 🔴 **`max(nifty_return, 0.0001)` divisor breaks for negative Nifty.** When Nifty is down 1%, `max(-0.01, 0.0001) = 0.0001` → RS-Ratio becomes meaningless on red days. Should use `abs()` or sign-preserved handling.
- 🔴 **Single horizon.** Spec requires both 5-day AND 20-day returns; code only takes one scalar per sector per call.
- 🔴 **RS-Momentum applied to wrong series.** `rank_sectors` passes sector return history (`sector_histories[sector]`) to `compute_rs_momentum`. Spec says "5-day change in RS-Ratio" — momentum should be diff of RS-Ratio series, not underlying return history.
- 🔴 **No rank-change tracking over 30 min.** Spec rotation rule (Gaining +2 / Steady ±1 / Losing -2 ranks) requires comparing current ranks to ranks 30 minutes ago. Code only returns current rank; no time-series of ranks retained.
- 🔴 **No rotation classification.** Gaining/Steady/Losing labels never assigned.
- 🟡 **60-day rolling std** — code uses `np.std(hist)` over whatever `hist` contains (caller-controlled); no enforced 60-day window.

---

## L5 — Scoring (`engine/layers/l5_scoring.py`)

### Matches spec
- Regime weights **exactly** match spec table:
  - Trending-Up / Trending-Down: 25/20/12/5/18/12/8 (×0.01) ✅
  - Range-Bound: 8/5/18/30/15/12/12 (×0.01) ✅
- Modifier values **exactly** match spec:
  - fo_ban -4, earnings -6, strong_sector +3, weak_sector -3, index_change -2 ✅
- Short asymmetry `× 0.92` applied ✅
- Final clamp `max(0, min(100, ...))` ✅

### Gaps
- 🔴 **Factor scoring is long-bias only.** F1, F2, F3, F4, F7 are written purely from a long perspective and **don't take direction as a parameter**. Only F6 (OI) differentiates LONG/SHORT. Spec table explicitly states:
  - F1 Trend: Long=Bullish alignment, Short=**Inverted**
  - F2 Momentum: Long=Trend-conditional, Short=**Inverted**
  - F3 Volume: Long=Above VWAP, Short=**Inverted**
  - F4 Vol-Pos: Long=Near support, Short=**Near resistance**
  - F7 Pos-Rng: Long=Bottom 20%, Short=**Top 20%**

  Multiplying the long-perspective sum by 0.92 does **not** approximate inversion — it just discounts a long-bias signal. This means short rankings are derived from long-bias inputs and would be systematically wrong.
- 🔴 **`liquidity_multiplier` not applied.** Spec: `S_liq = S_raw × liquidity_multiplier`. No such multiplier exists in `L5Scoring.compute()`. Step skipped.
- 🔴 **`stale_data` freeze missing.** Spec says "Stale data (>30 sec) → Score frozen." Code doesn't check the `stale_data` flag from L2 or otherwise preserve the prior score.
- 🟡 **`index_change` modifier defined but unused.** It's in the `MODIFIERS` dict, but `L5Scoring.compute()` never reads `symbol_data["index_change"]`.
- 🟢 **Order of operations differs slightly from spec.** Spec: raw → ×liq → +modifiers → clamp → ×0.92 (for shorts). Code: raw → +modifiers → clamp → ×0.92 (no ×liq). Within the [0,100] range, the difference is the missing liquidity step.

---

## L6 — Ranking (`engine/layers/l6_ranking.py`)

### Matches spec
- Sort by score descending, take top_n ✅
- Rank-movement category enum (NEW / UP / DOWN / STABLE) ✅
- Movement thresholds: ±2 positions = UP/DOWN ✅
- Movement direction signs correct (lower rank number = UP) ✅

### Gaps
- 🔴 **Hysteresis declared but never enforced.** `self.theta = 2.0` is set in `__init__` but never read in `rank()`. The method sorts purely by score and slices `[:top_n]` — no gate on entry/exit churn. Effectively non-hysteretic.
- 🔴 **No adaptive θ.** Spec: `θ = max(2.0, 0.25 × σ_gap)` computed over rank 20-30 score gaps, with ±10% adjustments based on rate of rank changes. None of this exists.
- 🔴 **Movement window is one tick, not 5 minutes.** `previous_ranks` is overwritten every call to `rank()`. If `rank()` runs every minute, "UP" means "+2 in last minute," not the spec's "in last 5 min."
- 🔴 **No concentration metrics emitted.** Sector concentration count, score spread (rank-1 vs rank-25), correlation-cluster pair count — none computed.
- 🟡 **NEW classification is one-shot.** A symbol that drops out of Top 25 and re-enters would not be re-flagged NEW; `previous_ranks` retains its last rank indefinitely.

---

## L7 — Confluence (`engine/layers/l7_confluence.py`)

### Matches spec — ✅ this layer is the closest to spec
- Check 1 Strong Close: upper 33% long / lower 33% short ✅
- Check 2 Volume Confirm: ≥1.5× median (2.0× during opening shock) ✅ — `is_opening` parameter handles the time-of-day adjustment
- Check 3 Non-Exhaustion: bar range ≤ 1.5× 20-bar median ✅
- Check 4 HTF Alignment: EMA(9)>EMA(20)>EMA(50) for long, inverse for short ✅
- Check 5 Risk Distance: |price - invalidation| ≥ 0.5× ATR ✅
- Check 6 Reward Distance: |T1 - price| ≥ 1.2× |price - invalidation| ✅
- Confluence score = 0-6 count ✅

### Gaps
- 🟡 **Relies on caller for correctness.** Check 2 assumes seasonally-adjusted volume (but L3 doesn't compute it — see L3 gaps). Check 4 assumes 15-min EMAs (but L3 only computes one timeframe). Check 5 assumes ATR from 5-min. `is_opening` is a parameter, not auto-derived from clock.

This is the only layer where the math matches but is silently degraded by upstream gaps.

---

## L8 — Thesis (`engine/layers/l8_thesis.py`) — **most severe gaps**

### Matches spec
- ORB 15-min setup: trigger = ORB high + tick, invalidation = `max(ORB Low, VWAP × 0.995)`, T1 = trigger + 1.5× ORB range ✅ (long path)
- Grade thresholds: ≥1.5 ATTRACTIVE / 1.0-1.5 MARGINAL / <1.0 UNATTRACTIVE ✅

### Gaps
- 🔴 **5 of 6 setup types missing.** Only `setup_orb_15` exists. Spec defines:
  - ORB (15-min) ✅
  - VWAP Reclaim ❌
  - Supertrend Pullback ❌
  - Mean Reversion ❌
  - First Hour Breakout ❌
  - CPR Breakout ❌

  `L8Thesis.assemble()` hardcodes the ORB path; there's no setup-selection logic based on market context.
- 🔴 **T2 hardcoded to PDH for both directions.** Comment in code admits this: `t2 = pdh  # previous day high for both directions`. For SHORT, T2 should be PDL.
- 🔴 **`valid_until = now + 2h` is constant.** Spec ORB-15 expires at 11:00 AM (clock-based), not 2h after creation. Each setup has its own session-time pending-expiry rule (see L9 spec table).
- 🔴 **Cost-model rates wrong** (`compute_brokerage`):
  | Charge | Spec | Code | Status |
  |---|---|---|---|
  | Brokerage equity | 0.03% capped ₹20 | 0.01% capped ₹20 | wrong rate |
  | Brokerage futures | flat ₹20/leg | same formula as equity | wrong shape |
  | STT equity | 0.025% sell-only | 0.1% × turnover (both legs) | **8× too high** |
  | STT futures | 0.0125% sell-only | 0.0125% sell-only | ✅ |
  | Exchange equity | 0.00297% | 0.00345% | overcharges ~16% |
  | Exchange futures | 0.00173% | 0.0019% | overcharges ~10% |
  | SEBI | 0.0001% (₹10/cr) | 0.00001% (`0.0000001`) | **10× too low** |
  | Stamp equity | 0.003% buy-only | 0.002% buy-only | undercharges |
  | Stamp futures | 0.002% buy-only | 0.002% buy-only | ✅ |
  | GST | 18% on (brk+exch+SEBI) | same | ✅ |
- 🔴 **Slippage missing entirely.** Spec table by liquidity bucket (Excellent 5bps / Good 10bps / Marginal 20bps / Poor 35bps, plus stop-leg add-ons) is not applied anywhere. Net R:R cannot match spec without it.
- 🔴 **Net R:R formula is wrong shape.** Spec:
  ```
  Net reward = |T1 - Trigger| - (cost% × Trigger)
  Net risk = |Trigger - Invalidation| + (stop_slippage × Trigger)
  Net R:R = Net reward / Net risk
  ```
  Code: `net_rr = gross_rr * (1 - cost_pct / 100)` — multiplicative on R:R, not additive on numerator/denominator. Diverges from spec especially at small Net R:R values.
- 🔴 **Time-decay formula is wrong shape.** Spec: `M(t) = exp(-λ × max(0, t - t_window)²)` with λ = 0.0003 (ORB) or 0.00015 (ST/VWAP) — quadratic exponent decaying from 1. Code: `1.0 - math.exp(-time_remaining_min / 30)` — exponential approach to 1 from 0 (going UP with time remaining). **The shapes are inverses of each other.**
- 🔴 **Grade computed against `net_rr = 0.0` placeholder.** `L8Thesis.assemble()` sets `thesis.net_rr = 0.0  # Set by cost model in pipeline`, then immediately runs the grade check → always UNATTRACTIVE until pipeline patches it. Grade should be recomputed after net_rr is finalized.
- 🟡 **Tick size hardcoded to ₹0.05.** Works for Nifty stocks > ₹100 but wrong for sub-₹100 stocks (tick = ₹0.01).
- 🟡 **Actionability tier not computed.** Spec defines 3-tier classification (Tradeable / Constrained / Research-Only) with criteria; L8 doesn't set it on the ThesisCard. L6 defaults to "Research-Only" if not provided.
- 🟡 **No setup-specific cost model differences.** `futures` is a boolean input with default True; no logic to derive whether a thesis is equity-MIS vs futures based on the symbol's F&O eligibility.

---

## L9 — Monitor (`engine/layers/l9_monitor.py`)

### Matches spec
- ACTIVE state on trigger ✅
- MFE/MAE tracking with sign flip for SHORT ✅
- T1/T2/SL transitions, FORCE_EXPIRED at session close ✅
- In-memory active dict + history list ✅

### Gaps
- 🔴 **State machine truncated.** Spec: `CREATED → PENDING → TRIGGERED → ACTIVE → terminal`. Code has only ACTIVE → terminal. No CREATED or PENDING handling — `on_trigger` jumps straight to ACTIVE, presuming the caller detected trigger.
- 🔴 **No setup-specific pending expiry.** Spec table:
  | Setup | Pending Expiry |
  |---|---|
  | ORB (15-min) | 11:00 AM |
  | ORB (2-hour) | 13:00 PM |
  | VWAP Reclaim | 14:00 PM |
  | Supertrend Pullback | 14:30 PM |
  | Mean Reversion | 13:30 PM |
  | FH Breakout | 12:00 PM |
  | CPR Breakout | 14:00 PM |

  Code only has `on_force_expire()` (called at 15:15). Theses never naturally expire by setup.
- 🔴 **Conditional 30-min extension not implemented.** Spec: "If VIX recovering from lunch lows + 5-min realized vol > 80th pct of session → extend VWAP/Supertrend expiry by 30 min." No equivalent logic.
- 🔴 **Outcome metrics underpopulated:**
  - Gross return ❌ not computed
  - Net return ❌ not computed (depends on missing L8 cost model)
  - R-multiple = Net Return / |Entry - Invalidation| ❌ not computed
  - Time-to-trigger ❌ not surfaced (no `trigger_ts`)
  - Time-to-exit ❌ not surfaced as a metric
  - MFE/MAE timestamps ❌ not tracked (only the magnitudes)
- 🟡 **`INVALIDATED` vs `STOPPED_OUT` conflation.** Code only sets `STOPPED_OUT` when price hits the invalidation level. Spec listed both as terminal states; the distinction (price-based stop vs invalidation-condition met) isn't preserved.
- 🟢 **Variable naming.** `triggered` in `on_tick` returns T1/T2 hits, which are exits, not entries — confusing terminology.

---

## L10 — Edge Lookup (`engine/layers/l10_edge.py`)

### Matches spec
- Wilson score interval formula ✅ (correct math, z=1.96)
- BH FDR step-up procedure ✅ (sort, find largest k with p ≤ (k/m)α, reject 1..k)
- Lookup keyed by `(setup, regime, direction, sector, time_bucket)` ✅

### Gaps
- 🔴 **6-tier fallback not implemented.** Spec defines a hierarchical fallback: when Tier 1 (Setup × Regime × Sector × Bucket) lacks data, fall back through Tier 2 (drop Sector) → Tier 3 (drop Bucket) → Tier 4 (drop Regime) → Tier 5 (Setup baseline) → Tier 6 (Global). Code's `lookup()` returns whatever's at a single key, with no traversal.
- 🔴 **Wrong default n threshold.** `check_min_samples(n, threshold=15)`. Spec per-tier: 30 / 40 / 50 / 50 / 80 / 50. Universal 15 default doesn't enforce any spec gate.
- 🔴 **CI width gates missing.** Spec: each tier requires CI half-width ≤ 15% / 14% / 14% / 14% / 12% / 14%. Code's `check_confidence_interval(hit_rate, ci_lower, ci_upper)` returns `ci_lower ≤ hit_rate ≤ ci_upper` — that's tautologically true by construction (the CI was built around the hit rate). Doesn't check width at all.
- 🔴 **`ci_lower > 0.35` gate is not in spec.** Code uses a fixed 0.35 lower-bound floor as a significance criterion. Spec uses CI **width** + BH FDR.
- 🔴 **Bayesian bootstrap implements wrong concept.** Spec: "Prior Beta(α=12, β=8) centered at 60% hit rate. Posterior: Beta(α + k, β + n - k)" — Beta-Binomial conjugate update on **hit rate**. Code: `bayesian_bootstrap(returns)` does Dirichlet-style resampling of **continuous returns** to estimate mean return CI. Different statistic, different data, different posterior.
- 🔴 **BH α default = 0.05.** Spec explicitly says 0.10: "Find largest k where p(k) ≤ (k/m) × 0.10."
- 🟡 **No tier promotion tracking.** Spec mentions a Dashboard "Edge Maturation" panel + weekly summary. No promotion event emitted from L10 to the WebSocket manager.

---

## Cross-cutting observations

1. **The skeleton-vs-spec gap is uniform.** Every layer has correct *names*, *enum values*, and *output frame fields*. Most have a thin implementation that demos the surface area but skips ~30-70% of the spec's actual math.
2. **`L8` cost model and `L10` Bayesian bootstrap have implementations that look correct at a glance but compute the wrong thing.** These are the highest-risk gaps because tests passing doesn't mean spec compliance — the tests likely just check that the function returns *a* number.
3. **No direction-aware factor inversion in L5** is the single most consequential algorithmic gap: it silently corrupts the entire Top-25-Short ranking output.
4. **Reference levels (L3)** are conspicuously missing — they're cited by spec for L8 setups (ORB H/L, FH H/L, CPR pivots) but L3 doesn't compute them. The current ORB-15 setup in L8 takes `orb_high`, `orb_low`, `pdh` as parameters, implying a caller computes them externally; need to trace `pipeline.py` to see where.
5. **Time-decay formula in L8 is shape-wrong**, not just parameter-wrong — would need a from-scratch reimplementation.

---

## Recommended remediation order (by trading-correctness impact)

1. 🔴 **L8 cost model** — rewrite `compute_brokerage` against the spec rate table; add slippage; fix Net R:R formula. Without this, every thesis's R:R grade is wrong.
2. 🔴 **L5 factor inversion** — refactor `compute_f1…f7` to take `direction` and compute inverted scores for SHORT. Without this, the short ranking is bogus.
3. 🔴 **L8 setups 2-6** — implement VWAP Reclaim, ST Pullback, Mean Reversion, FH Breakout, CPR Breakout. The dashboard claims setup variety it doesn't have.
4. 🔴 **L1 regime classifier** — fix Range-Bound reachability; add cold-start 15-min path.
5. 🔴 **L10 6-tier fallback + correct n/CI gates** — rewrite `lookup()` to traverse tiers; replace ci_lower > 0.35 gate with CI-width check.
6. 🔴 **L8 time-decay** — replace exponential-approach formula with spec's `exp(-λ × max(0, t-t_window)²)`.
7. 🟡 **L3 volume seasonality + reference levels** — needed for L7 check 2 to actually be seasonal, and for L8 setups to have correct PDH/PDL/CPR/ORB/FH inputs.
8. 🟡 **L9 outcome metrics** — add gross/net return, R-multiple, time-to-trigger/exit. Needed for L10 to have correct input data.
9. 🟡 **L6 hysteresis + concentration metrics** — implement adaptive θ + 30-min movement window + sector/score-spread/correlation metrics.
10. 🟡 **L10 Bayesian bootstrap** — replace with Beta-Binomial conjugate posterior on hit rate; use it as a fallback only when n < tier threshold.

---

## Verification basis

- All findings derived from Serena LSP symbol reads against current `main` @ `152127a`, cross-checked with direct file reads.
- Verified Serena index reflects HEAD before this audit (commits `39daf7f`, `3da01c1` symbols resolved).
- No claim was made from memory alone; every gap cites the function/class location verified by `find_symbol` or `Read`.
- This audit examines algorithm fidelity to `system_design_final.md` sections 5.1-5.10 only. Sections 6-13 (DB schema, Redis keys, APIs, scheduler, monitoring, deployment) were not in scope of the user's "full algorithm sweep L1-L10" request.
