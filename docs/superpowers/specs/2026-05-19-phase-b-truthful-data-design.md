# Phase B: Truthful Data — Design Spec

**Date:** 2026-05-19
**Status:** Approved
**Scope:** One consolidated PR — eliminate all hardcoded, random, and mock data from the Intraday Dashboard

## Scope: 26 Items

The Phase A audit identified 14 core items plus 12 API gap items. All are in scope.

### Items consolidated from audit

| # | Area | What changes |
|---|------|-------------|
| 1 | Health endpoint | Real TokenManager expiry, DB ping, Redis ping, APScheduler job count |
| 2 | Telemetry snapshot | Real scheduler.running boolean |
| 3 | Frontend types | Retype 7 components on real API types, delete simTypes.ts |
| 4 | VIX | Real Upstox India VIX quote (replaces `vix_value = 15.0`) |
| 5 | setup_type | Real L8 setup classification (replaces `random.randint(1, 6)`) |
| 6 | actionability_tier | Real tier computation (replaces `"Research-Only"` literal) |
| 7 | liquidity_quality | Real LQS from depth + ADV (replaces `random.choice(...)`) |
| 8 | Sector RS | Real L4 RS-Ratio + RS-Momentum from sector index feeds (replaces `_synthetic_sector_data`) |
| 9 | Symbol universe | Expand from 30 to 100 Nifty constituents |
| 10 | L2 flags | Wire NSE scraper F&O ban / MWPL / earnings into pipeline cycle |
| 11 | l2_real | Self-fixing when #10 lands |
| 12 | l4_real | Self-fixing when #8 lands |
| 13 | l10_real | Self-fixing when #14 lands |
| 14 | L9→L10 persistence | INSERT thesis outcomes on terminal state; L10 reads aggregated stats |

Plus 12 API gap items from `docs/backend-api-gaps.md` (gaps #1-#12).

## Code-vs-Spec Deviations (kept as authoritative)

Three changes in the current code improve on `system_design_final.md`. These stay:

1. **L5 F1** — EMA excluded from F1 scoring (delegated to L7 Check 4 gate). Prevents double-counting.
2. **L10 Beta prior** — Beta(6,6) centered at 50% (agnostic) instead of Beta(12,8) at 60%. Honest for Phase 1 with zero real outcomes.
3. **L10 Tier 6** — Separate LONG/SHORT global baselines (2 cells) instead of 1 combined. Indian markets have structural long bias.

## Work Streams (dependency order)

### Stream 1: Data Feed Wiring

**#9 — 100 Nifty constituents**

Add 70 missing symbols to `SYMBOL_TO_INSTRUMENT_KEY` in `engine/core/pipeline.py`. The Upstox WS subscription list, REST fetches, and `_run_live_cycle()` per-symbol loop all derive from `self.symbol_map` — expanding the dict automatically scales the pipeline.

Each entry: `"SYMBOL": "NSE_EQ|INE..."`. Source: NSE published constituent list.

**#4 — Real VIX**

In `_run_live_cycle()`, fetch `NSE_INDEX|India VIX` LTP via `self.upstox_rest.get_ltpc()` before the L1 compute step. Replace `vix_value = 15.0` with the fetched value.

**#10 — Wire L2 / NSE scraper**

The `nse_scraper` module is initialized in `main.py` lifespan and caches results in Redis. `_run_live_cycle()` reads the cached F&O ban list, MWPL, and earnings flags. Pass these into per-symbol L5 scoring (modifiers: `fo_ban`, `earnings`) and L8 thesis assembly (actionability tier gating).

**#8 — Real L4 sector RS**

Add `SECTOR_INDEX_MAP` mapping 11 NSE sector names to Upstox index keys. In `_run_live_cycle()`, fetch 5-min bars for all 11 sector indices, compute 5-day and 20-day returns vs Nifty, calculate RS-Ratio and RS-Momentum via the existing L4 module. Replace `_synthetic_sector_data()` calls. Cache sector data for the cycle (all stocks in same sector get same RS values).

### Stream 2: Compute Layer Wiring

**#5 — Real setup_type**

Instead of `random.randint(1, 6)`, run L8's setup assemblers (`l8_setups/`) for stocks above a minimum score threshold. Each assembler checks trigger conditions (price vs reference levels, indicator state, time window). First passing setup wins. Stocks that don't trigger any setup get no thesis card (no fake theses).

**#6 — Real actionability_tier**

`compute_actionability_tier()` in `l8_thesis.py` already implements the spec. When L8 assembles a thesis, tier is automatically correct. Remove the `"Research-Only"` literal override.

**#7 — Real liquidity_quality**

`compute_liquidity_quality_score()` in `l2_universe.py` implements the LQS formula. Wire it with real depth/spread/turnover from Upstox market depth. If live depth isn't available every cycle, use most recent Redis-cached snapshot. Replace `random.choice([...])` with computed LQS bucket.

### Stream 3: Persistence (L9 → L10)

**#14 — Thesis outcome INSERT**

When L9 `on_tick()` detects a terminal state (T1_HIT, T2_HIT, INVALIDATED, STOPPED_OUT, EXPIRED), INSERT into `thesis_outcomes` hypertable. Columns: thesis_id, symbol, setup_type, regime, direction, entry_price, exit_price, exit_reason, mfe_pct, mae_pct, net_return, r_multiple, created_at.

L10 `populate()` reads aggregated stats: `SELECT setup_type, regime, direction, sector, time_bucket, COUNT(*) as n, AVG(CASE WHEN net_return > 0 THEN 1 ELSE 0 END) as hit_rate, AVG(net_return) as avg_net_return, STDDEV(net_return) as std_net_return FROM thesis_outcomes GROUP BY ...`

Hypertable schema already exists in `engine/db/migrations/`.

### Stream 4: Health Endpoint Truthfulness

**#1 — Real health fields (rest_routes.py:595-598)**

- `token_expires_in_days`: compute from TokenManager's stored expiry
- `db_connected`: `await timescale.ping()`
- `redis_connected`: `await redis.ping()`
- `scheduler_jobs`: `len(scheduler.get_jobs())`

**#2 — Real scheduler_running (rest_routes.py:985)**

Replace literal with `scheduler.running` property from APScheduler instance.

### Stream 5: API Gap Closure

**Gap #5 — /market/context: event_flag + bank_nifty_divergence**

Pass `event_flag` (from NSE scraper: today's earnings/corporate actions) and `bank_nifty_divergence` (Bank Nifty return - Nifty return over same window) to L1.compute(). Both params already exist on the method signature.

**Gap #2 — /funnel/counts**

Track per-layer survivor counts during each pipeline cycle. Store in Redis hash `pipeline:funnel_counts`. Endpoint reads Redis.

**Gap #3 — /activity/events**

Maintain Redis list `pipeline:activity` of cycle events (new theses, invalidations, rank changes, tier promotions). Append each cycle, trim to last 200. Endpoint reads the list.

**Gap #4 — WS alert/funnel/activity broadcasts**

Call `ws_manager.broadcast_alert()` on thesis state changes, `broadcast_funnel_counts()` after ranking, `broadcast_activity()` on significant events. Wire into `_run_live_cycle()` at the natural points.

**Gap #9 — /market/candles/{symbol}**

Query `market_bars` hypertable for symbol + timeframe. Bars are already being inserted by BarAggregator. Endpoint runs: `SELECT ts, open, high, low, close, volume FROM market_bars WHERE instrument_key = $1 AND timeframe = $2 ORDER BY ts DESC LIMIT $3`

**Gap #1 — /rankings/top25/{dir}/full**

Extend `RankingEntry` model with: `price`, `change_pct`, `sector_name`, `sector_id`, `sparkline` (last 20 close prices), `rs_ratio`, `rs_momentum`, `state`, `edge_tier`. Sources: bar data (price, sparkline), L4 (sector, RS), L8 (state), L10 (edge_tier).

**Gap #6 — /rankings/{sym}/factors**

Add `l9_monitor` (MFE/MAE from shadow ledger), `l10_edge` (hit rate + CI from edge lookup), `price`, `sparkline` to the per-symbol factor response.

**Gap #7 — /edge/tiers**

Replace random tier generation with real L10 `lookup()` calls. Each tier row maps to a populated cell from `edge_store`. Only return tiers with n > 0.

**Gap #8 — RankingEntry.direction**

Ensure `direction` is always populated from the scoring computation. Verify pipeline passes it through.

**Gap #10 — /pipeline/status**

Populate `cycle_number` (increment each `_run_live_cycle()`) and `funnel_counts` (from Redis) from real sources.

**Gap #11 — /monitor/active-theses**

Read from L9's `self.active` dict. Map to API response shape.

**Gap #12 — TS type alignment**

Covered by item #3.

### Stream 6: Frontend Type Cleanup

**#3 — Delete simTypes.ts**

7 components import from `@/data/simTypes`:
- `LayerInspector.tsx` — `LAYER_META`, `SECTORS`, `SimStock`, `SimSnapshot`, `SimMarketContext`
- `SharedComponents.tsx` — `SimStock`
- `RankingsPanel.tsx` — `SimStock`
- `LayerJourney.tsx` — `evaluateLayers`, `LAYER_META`, `SimStock`, `SimMarketContext`
- `HealthStrip.tsx` — `SimPipelineLayer`
- `FunnelStrip.tsx` — `LAYER_META`, `SimPipelineLayer`
- `DetailPanel.tsx` — `SimStock`, `SimMarketContext`

Actions:
- `SimStock` → `RankingEntry` from `@/types/api`
- `SimMarketContext` → `MarketContextFrame` from `@/types/api`
- `SimSnapshot` → remove (telemetry snapshot uses real types)
- `SimPipelineLayer` → `PipelineLayer` from `@/types/api`
- `LAYER_META` → define from real layer list (no longer needs sim-specific fields)
- `SECTORS` → define from L4's 11-sector list
- `evaluateLayers` → rewrite to operate on real `PipelineStatus` data

Delete `frontend/src/data/simTypes.ts` after all imports are migrated.

### Stream 7: Telemetry Flags

**#11, #12, #13** — `l2_real`, `l4_real`, `l10_real` in `telemetry.py`

These flip automatically when their data sources become real:
- `l2_real` → True when NSE scraper F&O/MWPL/earnings data flows into L2 (item #10)
- `l4_real` → True when sector RS is computed from real index feeds (item #8)
- `l10_real` → True when thesis outcomes are persisted and L10 reads aggregated stats (item #14)

No code changes needed — just verify the conditions evaluate correctly after Streams 1-3.

## Dependencies

```
Stream 1 (Data Feeds) ──┐
                         ├──> Stream 2 (Compute) ──> Stream 3 (Persistence)
                         │                                    │
                         │                                    v
                         └──> Stream 5 (API Gaps) <───────────┘
                                    │
                                    v
                              Stream 6 (Frontend Types)

Stream 4 (Health) — independent, can land anytime
Stream 7 (Telemetry) — self-fixing, verify last
```

## Verification

- **Unit tests:** Each layer change gets a corresponding test addition
- **Health endpoint:** `curl http://localhost:8170/health` shows real (not hardcoded) values
- **Pipeline cycle:** `pytest tests/test_pipeline.py -v` — no mocks, real data flow
- **Frontend build:** `cd frontend && npm run build` — zero simTypes imports
- **Frontend tests:** `cd frontend && npm test` — all component tests pass with real types
