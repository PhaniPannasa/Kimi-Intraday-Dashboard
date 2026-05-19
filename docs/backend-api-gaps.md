# Backend API Gaps — Kimi Intraday Dashboard Frontend Refresh

> Generated 2026-05-18 · Documents what the new frontend needs vs what existing APIs return.
> Backend engineers: implement these in priority order to light up the new UI features.

## Priority Legend
- **P0 (Critical):** Frontend is using synthetic data; no real data path exists
- **P1 (High):** Partial API exists but missing key fields that would enrich the UI
- **P2 (Medium):** Nice-to-have; UI works without it via synthetic data

---

## P0 — Missing Endpoints (No Real Data Path)

### 1. `GET /api/rankings/top25/{direction}/full`
**Why:** The current `/rankings/top25/{long|short}` returns only 9 fields. The new RankingsPanel needs per-stock price, change%, sector name, sparkline data, RS metrics, and indicator values.

**Proposed response shape** (extend `RankingEntry`):
```json
{
  "symbol": "RELIANCE",
  "instrument_key": "NSE_EQ|INE002A01018",
  "direction": "LONG",
  "score": 84.5,
  "setup_type": 1,
  "setup_label": "ORB-15m",
  "confluence_score": 5,
  "net_rr": 1.4,
  "actionability_tier": "Tradeable",
  "rank_movement": "UP",
  "liquidity_quality": "Excellent",
  "price": 1284.50,
  "change_pct": 1.85,
  "sector_name": "Energy",
  "sector_id": 7,
  "sparkline": [1278.2, 1279.5, 1281.0, ...],
  "rs_ratio": 1.08,
  "rs_momentum": 1.02,
  "state": "PENDING",
  "edge_tier": 1
}
```

### 2. `GET /api/funnel/counts`
**Why:** The new FunnelStrip component shows survivor counts narrowing through each layer (L1: 1→1, L2: 50→48, L3: 48→42, ..., L10: 8→3). No endpoint currently provides these counts.

**Proposed response:**
```json
{
  "L1": {"in": 1, "out": 1},
  "L2": {"in": 50, "out": 48},
  "L3": {"in": 48, "out": 42},
  "L4": {"in": 42, "out": 38},
  "L5": {"in": 38, "out": 36},
  "L6": {"in": 36, "out": 25},
  "L7": {"in": 25, "out": 18},
  "L8": {"in": 18, "out": 12},
  "L9": {"in": 12, "out": 8},
  "L10": {"in": 8, "out": 3}
}
```

### 3. `GET /api/activity/events?since={cycle_number}`
**Why:** The new CycleActivity feed in the right column shows live events (new entries, rank moves, triggers, T1 hits, invalidations). No endpoint currently provides this.

**Proposed response:**
```json
{
  "events": [
    {
      "id": "evt-001",
      "ts": "2026-05-18T10:15:30+05:30",
      "type": "TRIGGER",
      "symbol": "RELIANCE",
      "direction": "LONG",
      "text": "triggered @ 1290.50",
      "detail": "ORB-15m · MFE +0.45R"
    }
  ]
}
```
**Event types:** `NEW`, `DROP`, `TRIGGER`, `T1`, `ACTIVE`, `INVALID`, `JUMP_UP`, `JUMP_DN`, `STATE`

### 4. WebSocket channel: `cycle_activity`
**Why:** The AlertToast component needs real-time push notifications for invalidations, triggers, T1 hits, and regime changes. Currently only `L1_CONTEXT`, `L6_RANKINGS`, `L8_THESIS`, `L9_INVALIDATION`, `L10_EDGE` are broadcast.

**Proposed messages:**
```json
{"type": "ALERT", "payload": {"type": "triggered", "symbol": "RELIANCE", "message": "RELIANCE LONG triggered @ 1290.50", "ts": "..."}}
{"type": "ALERT", "payload": {"type": "t1_hit", "symbol": "TCS", "message": "TCS T1_HIT (+1.85%) — partial booked", "ts": "..."}}
{"type": "ALERT", "payload": {"type": "invalidation", "symbol": "INFY", "message": "INFY SHORT invalidated · Score < 60", "ts": "..."}}
{"type": "ALERT", "payload": {"type": "regime", "message": "Trending-Up → Range-Bound", "ts": "..."}}
{"type": "ALERT", "payload": {"type": "edge", "symbol": "SBIN", "message": "SBIN promoted to T1 Full Confluence", "ts": "..."}}
```

---

## P1 — Existing Endpoints Missing Key Fields

### 5. `GET /market/context` — Missing fields
The `MarketContextFrame` model already defines `event_flag` and `bank_nifty_divergence`, but the endpoint at `engine/api/rest_routes.py:58` does not return them.

**Action:** Add to the `MarketContextFrame(...)` constructor:
```python
event_flag=None,  # or e.g. "RBI Policy 14:00" when applicable
bank_nifty_divergence=0.35,  # actual BankNifty vs Nifty divergence
```

### 6. `GET /rankings/{symbol}/factors` — Missing L9/L10 data
The `SymbolFactorBreakdown` response is the most complete endpoint but lacks:
- **L9 monitoring state:** `state` (PENDING/TRIGGERED/ACTIVE/T1_HIT), `mfe_pct`, `mae_pct`
- **L10 edge tier:** `edge_tier` (1-6), `edge_hit_rate`, `edge_ci_lower`, `edge_ci_upper`
- **Price/sparkline:** Current LTP and 30-point sparkline for mini chart

**Proposed additions to `SymbolFactorBreakdown`:**
```python
l9_monitor: Optional[L9MonitorSnapshot]  # new model
l10_edge: Optional[L10EdgeSnapshot]      # new model
price: float
change_pct: float
sparkline: List[float]
```

### 7. `GET /edge/tiers` — Returns empty data
The endpoint at `engine/api/rest_routes.py:126` returns `{"tiers": [], "promotions": []}`. It needs to return actual L10 edge tier statistics.

**Should return:**
```json
{
  "tiers": [
    {"tier": 1, "label": "Full Confluence", "n": 20, "hit_rate": 0.62, "ci_lower": 0.48, "ci_upper": 0.74, "live_count": 2},
    {"tier": 2, "label": "5/6 Confluence", "n": 32, "hit_rate": 0.55, "ci_lower": 0.42, "ci_upper": 0.67, "live_count": 1}
  ]
}
```

### 8. `GET /rankings/top25/{direction}` — Missing per-stock direction field
The `RankingEntry` model does not include a `direction` field. The frontend needs to know whether each ranking entry is LONG or SHORT, especially when displaying in a combined view.

**Action:** Add `direction: Direction` to `RankingEntry`.

---

## P2 — Nice-to-Have Enhancements

### 9. `GET /market/candles/{symbol}?interval=1m&count=60`
**Why:** The DetailPanel now includes an SVG candle chart showing the last 60 one-minute candles for the selected stock. No endpoint currently provides OHLC data.

**Proposed response:**
```json
{
  "symbol": "RELIANCE",
  "interval": "1m",
  "candles": [
    {"o": 1280.5, "h": 1282.0, "l": 1279.8, "c": 1281.5},
    ...
  ],
  "overlays": {
    "vwap": 1281.2,
    "trigger": 1290.5,
    "invalidation": 1270.0,
    "t1": 1310.0,
    "t2": 1340.0
  }
}
```

### 10. `GET /pipeline/status` — Add cycle number and funnel counts
Currently returns layer-level status but no cycle counter. The frontend HealthStrip and FunnelStrip need:
- `cycle_number: int` — monotonically increasing cycle counter
- `funnel_counts: dict` — same shape as the funnel endpoint, or merged

### 11. L9 Monitoring: `GET /monitor/active-theses`
**Why:** The right-column ActiveMonitor and L9 LayerInspector need real monitoring data. Currently only available per-thesis via `/thesis/{id}/outcome`.

**Proposed response:**
```json
{
  "theses": [
    {
      "thesis_id": "...",
      "symbol": "RELIANCE",
      "state": "ACTIVE",
      "mfe_R": 1.2,
      "mae_R": -0.3,
      "entry_price": 1290.5,
      "current_price": 1312.0
    }
  ]
}
```

### 12. TS type alignment
The frontend TypeScript types in `frontend/src/types/api.ts` should be kept in sync as backend models evolve. Current gaps:
- `RankingEntry.direction` is used but not in the backend model
- `ThesisCard.valid_until` and `preferred_regime` are in types but not in all mock responses
- `MarketContextFrame.event_flag` and `bank_nifty_divergence` are in types but not in endpoint response

---

## Summary

| # | Endpoint | Priority | Issue |
|---|----------|----------|-------|
| 1 | `/rankings/top25/{dir}/full` | P0 | New endpoint needed for rich ranking data |
| 2 | `/funnel/counts` | P0 | New endpoint for layer survivor counts |
| 3 | `/activity/events` | P0 | New endpoint for cycle activity feed |
| 4 | WS `cycle_activity` channel | P0 | New WS channel for real-time alerts |
| 5 | `/market/context` | P1 | Missing `event_flag`, `bank_nifty_divergence` |
| 6 | `/rankings/{sym}/factors` | P1 | Missing L9/L10/price/sparkline |
| 7 | `/edge/tiers` | P1 | Returns empty data |
| 8 | `/rankings/top25/{dir}` | P1 | Missing `direction` field |
| 9 | `/market/candles/{symbol}` | P2 | New endpoint for OHLC candle data |
| 10 | `/pipeline/status` | P2 | Add cycle_number, funnel_counts |
| 11 | `/monitor/active-theses` | P2 | New endpoint for aggregate L9 state |
| 12 | TS type alignment | P2 | Keep frontend types in sync |

---

# Backend Implementation Plan

> Implementation order optimized to light up frontend features fastest.

## Phase 1: Quick Wins (2-4 hours)

These are existing endpoints that just need their mock responses filled in with real or richer mock data.

### Step 1.1: `GET /market/context` — Add missing fields
**File:** `engine/api/rest_routes.py:58`
**Change:** Add `event_flag=None` (or real event) and `bank_nifty_divergence=0.35` (or real divergence) to the `MarketContextFrame` constructor.
**Model check:** `engine/models/frames.py` — verify `MarketContextFrame` already has `event_flag: Optional[str]` and `bank_nifty_divergence: float`.
**Effort:** 15 min

### Step 1.2: `GET /rankings/top25/{direction}` — Add `direction` field
**File:** `engine/api/rest_routes.py:72`
**Change:** Add `direction=direction` to each `RankingEntry` constructor.
**Model fix:** `engine/models/frames.py` — add `direction: Direction` to `RankingEntry` if not present.
**Effort:** 15 min

### Step 1.3: `GET /edge/tiers` — Populate with real tier data
**File:** `engine/api/rest_routes.py:126`
**Change:** Replace `{"tiers": [], "promotions": []}` with actual tier stats computed from the L10 edge layer.
**Data source:** L10 layer's cross-tab of setup×regime hit rates with Wilson CI.
**Effort:** 1 hour

### Step 1.4: `GET /rankings/{symbol}/factors` — Add L9/L10 sections
**File:** `engine/api/rest_routes.py:147`
**Change:** Add `l9_monitor` and `l10_edge` data to the `SymbolFactorBreakdown` response.
**New models needed:** `L9MonitorSnapshot` (state, mfe_pct, mae_pct), `L10EdgeSnapshot` (edge_tier, hit_rate, ci_lower, ci_upper).
**Effort:** 1.5 hours

## Phase 2: Rich Ranking Data (3-4 hours)

### Step 2.1: Extend `RankingEntry` model
**File:** `engine/models/frames.py`
**Add fields:** `price: float`, `change_pct: float`, `sector_name: str`, `sector_id: int`, `rs_ratio: float`, `rs_momentum: float`, `setup_label: str`, `sparkline: List[float]`, `state: str`, `edge_tier: int`
**Effort:** 30 min

### Step 2.2: Create `GET /rankings/top25/{direction}/full`
**File:** `engine/api/rest_routes.py` — new endpoint
**Returns:** Extended `RankingEntry` list with all fields from Step 2.1.
**Data pipeline:** Wire the endpoint to the real L2-L8 layer outputs (already computed each cycle).
**Effort:** 2 hours

### Step 2.3: Add sparkline generation
**File:** `engine/core/pipeline.py` or new helper
**Logic:** Store last 30 one-minute closes per symbol in Redis, return as sparkline array.
**Redis key:** `sparkline:{symbol}` → sorted set or list of (timestamp, price) pairs.
**Effort:** 1.5 hours

## Phase 3: New Endpoints (4-6 hours)

### Step 3.1: `GET /funnel/counts`
**File:** `engine/api/rest_routes.py` — new endpoint
**Logic:** After each cycle completes, compute how many symbols survive each layer. Store in Redis under `funnel:counts`. Return on request.
**Route:** `@router.get("/funnel/counts")`
**Effort:** 1 hour

### Step 3.2: `GET /activity/events`
**File:** `engine/api/rest_routes.py` — new endpoint  
**Logic:** Track events in Redis list `activity:events`. Each cycle: diff old vs new universe, push NEW/DROP/TRIGGER/T1/STATE events. Return last N events.
**Route:** `@router.get("/activity/events")` with optional `?since=cycle_number` query param.
**Event schema:** `{id, ts, type, symbol, direction, text, detail}`
**Effort:** 2 hours

### Step 3.3: `GET /market/candles/{symbol}`
**File:** `engine/api/rest_routes.py` — new endpoint
**Logic:** Return last 60 one-minute OHLC candles from TimescaleDB `market_bars` hypertable.
**Route:** `@router.get("/market/candles/{symbol}")` with optional `?interval=1m&count=60`
**Effort:** 2 hours

### Step 3.4: `GET /monitor/active-theses`
**File:** `engine/api/rest_routes.py` — new endpoint
**Logic:** Return all active/triggered/T1-hit theses from Redis `active_theses:*` keys.
**Effort:** 1 hour

## Phase 4: WebSocket Enhancements (2-3 hours)

### Step 4.1: Add `ALERT` message type to WebSocket
**File:** `engine/api/websocket_manager.py`
**New message type:** `ALERT` with payload `{type, symbol, message, ts}`
**Alert types:** `triggered`, `t1_hit`, `invalidation`, `regime`, `edge`
**Trigger logic:** In the pipeline orchestrator, after each cycle, detect state transitions and broadcast ALERT messages.
**Effort:** 2 hours

### Step 4.2: Add `FUNNEL` channel
**File:** `engine/api/websocket_manager.py`
**New channel:** `funnel` — pushes funnel counts after each cycle completes.
**Effort:** 1 hour

## Phase 5: Pipeline & Polish (1-2 hours)

### Step 5.1: Add cycle_number to pipeline status
**File:** `engine/api/rest_routes.py:197` and `engine/models/factors.py`
**Change:** Add `cycle_number: int` to `PipelineStatusResponse`.
**Effort:** 15 min

### Step 5.2: Sync frontend TS types
**File:** `frontend/src/types/api.ts`
**Changes:** Add any missing fields to match backend models after Phase 1-4 changes.
**Effort:** 30 min

---

## Total Estimated Effort

| Phase | Hours | Frontend Feature Unlocked |
|-------|-------|--------------------------|
| Phase 1 | 3.5h | Regime events, direction pills, edge tiers, L9/L10 cards |
| Phase 2 | 4h | Rich rankings (prices, sectors, sparklines, RS metrics) |
| Phase 3 | 6h | FunnelStrip, CycleActivity, CandleChart, ActiveMonitor |
| Phase 4 | 3h | Real-time AlertToast, live funnel updates |
| Phase 5 | 1h | Pipeline polish, type sync |
| **Total** | **17.5h** | Full dashboard on real data |

## Quick Way to Test Without Backend

The frontend already works with synthetic data via `engineSimulator.ts`. To verify:
```bash
cd frontend && npm run dev
# Open http://localhost:8190
# Dashboard renders with full L1-L10 pipeline simulation
```
