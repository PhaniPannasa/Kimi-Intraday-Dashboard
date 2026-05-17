# Real Data Pipeline — Design Spec

**Date:** 2026-05-17  
**Status:** Updated v3 — L8 cost model fix + BH fix + cold start + scheduler timezone + instrument mapping

## Goal

Replace synthetic/mock data in the L1-L10 pipeline with real Upstox market data. Add market-hours awareness so the engine auto-transitions between closed (snapshot), pre-market (prep), live (full pipeline), and closing (force-expire) phases. Weekends and NSE holidays are handled by the existing `HolidayCalendar`.

## Pre-Requisite Bug Fix

### L10 `benjamini_hochberg` is mathematically incorrect

`engine/layers/l10_edge.py:34-35` has `else: break` in the step-up loop. Standard BH requires finding the **largest** k where p_(k) <= k × α / m. Breaking on first failure stops too early.

Example: p = [0.009, 0.021, 0.022, 0.023, 0.5], m=5, α=0.05:

| Rank k | Threshold k×0.01 | p_(k) | Pass? | Correct k |
|--------|-----------------|--------|-------|-----------|
| 1 | 0.01 | 0.009 | ✓ | k=1 |
| 2 | 0.02 | 0.021 | ✗ | (skip) |
| 3 | 0.03 | 0.022 | ✓ | k=3 |
| 4 | 0.04 | 0.023 | ✓ | k=4 |
| 5 | 0.05 | 0.5 | ✗ | (skip) |

- **Buggy result:** `[True, False, False, False, False]`
- **Correct BH result:** `[True, True, True, True, False]`

**Fix:** Remove lines 34-35 (`else: break`). Update `test_benjamini_hochberg_monotonic` expected value to `[True, True, True, True, False]` and `test_benjamini_hochberg_basic` to match correct BH output. This is a 2-line code change + test expectation update.

### L8 `compute_brokerage` has incorrect Indian futures formulas

`engine/layers/l8_thesis.py:76-80` has 5 formula errors for NSE futures transaction costs:

| Cost | Current code | Correct (NSE futures) | Error |
|------|-------------|----------------------|-------|
| STT | `turnover * 0.00025` (0.025% on both legs) | `exit_leg_only * 0.000125` (0.0125% on sell side only) | 4× too high |
| Exchange | `turnover * 0.0000345` (equity rate) | `turnover * 0.000019` (futures rate) | 1.8× too high |
| SEBI | `turnover * 0.000001` (₹100/crore) | `turnover * 0.0000001` (₹10/crore) | 10× too high |
| GST | `brokerage * 0.18` | `(brokerage + exchange + sebi) * 0.18` | Missing exchange + SEBI base |
| Stamp | `turnover * 0.00002` (0.002% on full turnover) | `entry_leg * 0.00002` (0.002% on buy leg only, Maharashtra) | Both legs instead of buy only |

Brokerage is correct: `min(20, turnover * 0.0001)` matches Upstox's actual cap (₹20 max per order, or 0.01% whichever is lower).

Also: `L8Thesis.assemble()` (line 59) sets `net_rr = gross_rr * 0.9` as a placeholder. This is overwritten by the pipeline's `L8CostModel.apply()`, but `assemble()` should either call the cost model itself or leave `net_rr` at 0. Fix: remove the `* 0.9` line; `assemble()` sets `net_rr = 0` and the caller applies cost model.

**Fix:** Rewrite `compute_brokerage()` with correct formulas. Remove `net_rr = gross_rr * 0.9` from `assemble()`. Update `test_l8_cost.py` expected values.

---

## Architecture

### New: `engine/core/session/market_session.py`

A single `MarketSession` class in IST (`timezone(timedelta(hours=5, minutes=30))`) that answers: "what should the engine be doing right now?"

```
                   08:00          09:00    09:15              15:15    15:30
─────────────────────┼──────────────┼────────┼──────────────────┼────────┼────
    CLOSED           │  PRE-MARKET  │PRE-OPEN│    LIVE          │CLOSING │CLOSED
  (show snapshot)    │ (prep data)  │(prices)│ (full pipeline)  │(expire)│
```

Phases:
- **closed** — Pipeline does nothing. REST serves last snapshot from Redis with `snapped_at` IST timestamp. Frontend shows "Market Closed — Snapped at HH:MM IST" banner.
- **pre-market** (08:00-09:15) — Prepare universe for market open. Three jobs:
  1. Fetch global cues, F&O ban list, corporate actions from NSE scraper
  2. **Cold-start backfill:** Fetch yesterday's last 100 1-min bars for all 100 symbols via REST historical with `from_date/to_date` range. Merge with today's live WS bars before passing to L3 so EMA50, ADX(14), RSI(14), BB(20,2), ATR(14) have sufficient history at 09:15.
  3. Connect Upstox WebSocket, subscribe to 100 stocks (Full mode)
- **live** (09:15-15:15) — Full L1-L10 pipeline every 60 seconds. At 09:15:00, yesterday's merged bars already prime all indicators. Each subsequent cycle accumulates WS ticks into new 1-min bars. No REST calls for bars during live.
- **closing** (15:15-15:30) — Phase-based: no separate cron needed (pipeline runs every 60s, detects phase=="closing" on its own). Force-expire all active theses in L9, capture snapshot to Redis, run L10 edge update.

Weekend/holiday check: `HolidayCalendar.is_trading_day(today_ist)` — if False, phase is always `closed`. The `today_ist` is `datetime.now(IST).date()` to ensure correct date at UTC±IST boundaries.

Snapshot: stored in Redis under key `market:snapshot` as JSON:
```json
{
  "snapped_at": "2026-05-16T15:30:00+05:30",
  "context": { ... },
  "long_rankings": [ ... ],
  "short_rankings": [ ... ],
  "theses": [ ... ],
  "edge_promotions": [ ... ]
}
```

### Rewrite: `engine/core/pipeline.py`

**Cold-start strategy**

At 09:15:00, zero 1-min bars exist for today. Every indicator in L3 (EMA50, ADX(14), RSI(14), BB(20,2), ATR(14)) will produce NaN with <50 bars. Fix: during pre-market (08:00-09:15), fetch yesterday's last 100 1-min bars for every symbol via Upstox REST historical endpoint with a `from_date/to_date` range. Store in the `BarAggregator` as pre-bars. When today's first WS-accumulated bar closes at 09:16, merge yesterday's tail + today's bar before passing to L3. This ensures all indicators are valid from the first cycle.

**Instrument key mapping**

The pipeline operates on symbols ("RELIANCE") but Upstox REST and WebSocket require instrument keys ("NSE_EQ|INE002A01018"). A hardcoded `SYMBOL_TO_INSTRUMENT_KEY` dict for 30 Nifty symbols lives in the pipeline. Example:
```python
SYMBOL_TO_INSTRUMENT_KEY = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    # ... 28 more
}
```
Cached in the pipeline instance at startup. Can be refreshed daily from Upstox instrument master API in a future iteration.

**Data architecture: WebSocket tick accumulation + REST backfill**

The original spec's "100 REST calls per cycle" hits Upstox rate limits. The correct approach (matching the system design doc section 4) uses Upstox WebSocket Full mode for live ticks:

```
At 09:15 startup:
  ├── Pre-market already primed: yesterday's 100 bars merged into BarAggregator
  ├── WS: Subscribe to 100 Nifty stocks (Full mode, connection WS-1)
  │   Uses: upstox_ws.subscribe(all_100_instrument_keys, mode="full")
  │   Message handler: upstox_ws.on_message → TickBuffer.ingest()
  └── REST: Nifty 50 + BankNifty + VIX 5-min bars for L1 (once, then every 5 min)
      Uses: upstox_rest.get_historical_candle(index_key, "5minute")

Every 60s cycle during live:
  ├── WS Tick Buffer → aggregate completed ticks into 1-min OHLCV bars
  │   In-memory buffer per instrument_key: append tick, detect bar close
  │   On bar close: merge with yesterday's tail → push to L3
  ├── L1: REST Nifty 5-min (every 5 min, not every cycle)
  ├── L3: compute_indicators() on accumulated 1-min bars → extract signals
  ├── L5: score all 100 symbols from L3 signals
  ├── L6: rank → Top 25
  ├── L7: confluence on top entries
  ├── L8: thesis assembly + cost model
  ├── L9: shadow ledger tick check
  ├── L10: edge lookup
  └── Broadcast all via WebSocket manager
```

**New classes in pipeline.py:**

```python
class TickBuffer:
    """Accumulates WebSocket ticks into 1-min OHLCV bars per instrument."""
    def ingest(self, instrument_key: str, ltp: float, volume: int, oi: int, ts: datetime) -> Optional[dict]:
        """Returns completed bar dict if a 1-min bar just closed, else None."""
        ...

    def get_latest_bars(self, instrument_key: str, n: int = 100) -> pl.DataFrame:
        """Return last n completed bars as Polars DF for L3."""
        ...

class BarAggregator:
    """Holds TickBuffers for all 100 symbols. Called by the WS message handler."""
    ...
```

**Pipeline flow:**
1. `_run_pre_market_cycle()` — Global cues from REST, F&O ban from NSE scraper, universe prep
2. `_run_live_cycle()` — Tick buffer → bar aggregation → L3 indicators → L5 scoring → L6 ranking → L7 confluence → L8 thesis → L9 tick → L10 edge → WS broadcast
3. `_run_closing_cycle()` — Force-expire L9, capture snapshot to Redis, run L10 edge stats

### REST endpoint behavior

| Endpoint | Closed phase | Live phase |
|----------|-------------|------------|
| `/health` | `market_status: "closed"`, `snapped_at: "..."` | `market_status: "live"` |
| `/market/context` | From Redis snapshot, or default | Pipeline L1 latest output |
| `/rankings/top25/{direction}` | From Redis snapshot, or [] | Pipeline L6 latest output |
| `/thesis/{id}` | From Redis snapshot, or 404 | Pipeline L8 latest theses |
| `/edge/tiers` | From Redis snapshot, or {} | Pipeline L10 latest edge |

### Changes to existing files

| File | Change |
|------|--------|
| `engine/layers/l10_edge.py` | **Bug fix:** Remove `else: break` (lines 34-35) |
| `engine/layers/l8_thesis.py` | **Bug fix:** Correct STT/exchange/SEBI/GST/stamp formulas; remove `* 0.9` placeholder from `assemble()` |
| `tests/test_l10.py` | **Bug fix:** Update BH test expectations |
| `tests/test_l8_cost.py` | **Bug fix:** Update expected values for corrected formulas |
| `engine/config.py` | Modify — add `upstox_api_secret` and `upstox_api_base_url` fields (already in `.env`, not in Settings) |
| `engine/core/session/__init__.py` | New — empty |
| `engine/core/session/market_session.py` | New — `MarketSession` class with IST timezone + HolidayCalendar |
| `engine/core/pipeline.py` | Rewrite — `TickBuffer`, `BarAggregator`, cold-start backfill, symbol→instrument_key mapping, remove all `_synthetic_*` |
| `engine/core/data/upstox_ws.py` | Modify — wire `on_message` callback to `TickBuffer.ingest()` |
| `engine/core/data/upstox_rest.py` | No change — existing client is sufficient for backfill + L1 |
| `engine/core/scheduler/market_scheduler.py` | Modify — all cron triggers pass `timezone='Asia/Kolkata'` |
| `engine/main.py` | Update lifespan — register pre-market (08:00 IST), live-start (09:15 IST); pass `timezone='Asia/Kolkata'` to scheduler |
| `engine/api/rest_routes.py` | Update — serve from pipeline state (live) or Redis snapshot (closed); return `stale: true` if snapshot >4h old |
| `tests/test_pipeline.py` | Rewrite — mock Upstox REST + WS, verify cold-start merge, test stale-snapshot guard |
| `tests/test_market_session.py` | New — test all phases, IST boundaries, holiday/weekend gating |
| `frontend/src/components/RegimeBanner.tsx` | Update — show `market_status` + `snapped_at` + stale-data warning |

## The Snapshot Flow

```
Market closes 15:30 IST
  → pipeline._run_closing_cycle()
    → l9.on_force_expire() — close all active theses
    → Capture latest context, rankings, theses, edge
    → redis.set("market:snapshot", json, ex=86400)  # 24h TTL
    → REST endpoints switch to serving snapshot

User opens dashboard at 19:45 IST (market closed)
  → Frontend fetches /api/market/context
  → Backend reads market:snapshot from Redis
  → Returns data with snapped_at = "2026-05-16T15:30:00+05:30"
  → RegimeBanner shows "Market Closed — Snapped at 15:30 IST"

Next trading day 08:00 IST
  → Scheduler triggers pre-market job
  → Pipeline preps universe, fetches global cues
  → REST endpoints switch to serving pre-market data

09:15 IST
  → Scheduler triggers live-start job
  → WebSocket connects, yesterday's bars already primed via pre-market backfill
  → Full pipeline starts with valid indicators from first cycle
```

### Snapshot staleness guard

If Redis is empty (restart, flush, expiry) during closed hours, REST endpoints return a `stale: true` flag:

- `/health` → adds `"snapshot_stale": true` if snapshot >4h old or missing
- `/market/context` → returns HTTP 200 but with `"stale": true` and a default/empty context
- `/rankings/top25/{direction}` → returns `[]` with `"stale": true`
- Frontend `RegimeBanner` shows "Data unavailable" instead of stale Friday data when stale flag is set

### Scheduler timezone

APScheduler `AsyncIOScheduler` defaults to system time (UTC on most VPS). All cron triggers must explicitly pass `timezone='Asia/Kolkata'`:

```python
scheduler.register_job(
    "pre_market",
    pipeline._run_pre_market_cycle,
    trigger="cron",
    hour=8, minute=0,
    timezone="Asia/Kolkata",  # Required — IST, no DST
)
```

India has no DST — `Asia/Kolkata` is stable year-round.

## Timezone Audit

| Component | Uses | Correct? |
|-----------|------|----------|
| `MarketSession` | `timezone(timedelta(hours=5, minutes=30))` | IST |
| Date boundary | `datetime.now(IST).date()` → `HolidayCalendar.is_trading_day()` | |
| `HolidayCalendar` | `datetime.date` objects (timezone-naive) |  (date only) |
| `config.py` | String times "09:15", "15:30" — parsed in IST context | |
| Scheduler cron triggers | `timezone='Asia/Kolkata'` | |
| Snapshot `snapped_at` | ISO 8601 with +05:30 offset | |
| Upstox API responses | UTC timestamps — converted to IST for comparison | |
| Frontend display | IST from backend | |

## Test Strategy

- `test_market_session.py` — Saturday/Sunday/holiday closed, pre-market boundary (07:59→closed, 08:00→pre-market), live boundary (09:14→pre-market, 09:15→live), closing boundary (15:14→live, 15:15→closing), closed boundary (15:29→closing, 15:30→closed)
- `test_pipeline.py` — Mock `upstox_rest` with `respx`, mock `upstox_ws` with `AsyncMock`, verify cold-start merge (yesterday's bars + today's tick → valid indicators), verify TickBuffer correctly aggregates ticks into 1-min OHLCV bars, verify snapshot saved to fakeredis on closing, test stale-snapshot guard (empty Redis → stale flag), test empty response from Upstox for delisted symbol
- `test_l10.py` — Fix BH test expectations (`test_benjamini_hochberg_monotonic` → `[True, True, True, True, False]`)
- Existing 96 backend + 20 frontend tests must continue to pass

## Scope

- **In scope:** Market session (IST + holidays + weekends), WebSocket Full-mode tick accumulation → 1-min bars, cold-start backfill from yesterday's REST historical, real Upstox data through L1-L10, symbol→instrument_key mapping, snapshot mechanism with staleness guard, scheduler with `timezone='Asia/Kolkata'`, auto phase transition (pre-market/live/closing), closed-state REST responses from Redis, frontend market-status banner with stale indicator, BH bug fix
- **Out of scope:** Docker Compose verification, OAuth daily token refresh (1-year analytics token is used), live order execution / paper trading (MVP2), Upstox WS-2 LTPC connection (MVP1 uses only WS-1 Full for 100 stocks + REST for indices), instrument master API daily refresh (hardcoded mapping is sufficient), half-day/special session handling (Muhurat trading — once a year, add `session_end_override` field to schema for future)
