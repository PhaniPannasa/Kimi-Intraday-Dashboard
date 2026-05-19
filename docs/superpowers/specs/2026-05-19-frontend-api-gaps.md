# Frontend API Gaps — Backend Implementation Required

**Date:** 2026-05-19
**Frontend:** React + Vite + TypeScript (Kimi Intraday Dashboard)
**Backend:** FastAPI + Uvicorn on port 8170

---

## Summary

The frontend is a **fully implemented React PWA** with a built-in **engine simulator** (`data/engineSimulator.ts`) that can render rich mock data without any backend. When the simulator is active, no backend API calls are needed.

However, when the **simulator is OFF**, the frontend calls 4 REST endpoints and 1 WebSocket stream that the backend does **NOT** implement, causing 404s. Additionally, there are **field-level mismatches** where the backend response is missing fields the frontend type system expects.

This document records all gaps that require backend implementation. **Do not modify frontend code** to work around these gaps.

---

## Section A: Missing REST Endpoints (404s)

These endpoints are called by the frontend when the simulator is OFF, but return `404 Not Found` from the backend:

### 1. `GET /funnel/counts`
**Called by:** Not called directly by any component — appears in engine log as a 404. Likely from frontend proxy misconfiguration or a stale route reference.
**Expected response shape:** `Record<string, { in: number; out: number }>` (funnel in/out counts per layer L1–L10)
**Status:** ❌ NOT IMPLEMENTED — backend has no route for this

---

### 2. `GET /activity/events?limit={limit}`
**Called by:** Unknown — not found in any frontend component or hook.
**Expected response shape:** `CycleEvent[]` — array of `{ id, type, symbol, direction, text, detail, cycle }`
**Status:** ❌ NOT IMPLEMENTED — backend has no route for this

---

### 3. `GET /monitor/active-theses`
**Called by:** Unknown — not found in any frontend component or hook.
**Expected response shape:** `ThesisCard[]` — array of active thesis cards
**Status:** ❌ NOT IMPLEMENTED — backend has no route for this

---

### 4. `GET /market/candles/{symbol}?count={count}`
**Called by:** `ChartPanel.tsx` (calls `useFactorBreakdown` which uses `/rankings/{symbol}/factors` — not this endpoint; but ChartPanel accepts `CandlestickData[]` prop which may be filled from a different source in future)
**Expected response shape:** `CandlestickData[]` — array of `{ time, open, high, low, close, volume }`
**Status:** ❌ NOT IMPLEMENTED — backend has no route for this
**Note:** This is used by `ChartPanel.tsx` which renders a candlestick chart via `lightweight-charts`. Currently no frontend component fetches this endpoint — it is a **future** integration point for historical price charts.

---

## Section B: Partial Response — Missing Fields

The backend implements these endpoints but the response is missing some fields that the frontend TypeScript types expect:

### 1. `GET /market/context` → `MarketContextFrame`

| Missing Field | Frontend Type | Notes |
|---|---|---|
| `vix_value` | `number` | Backend model has it; REST response omits it. Will be absent from JSON (not defaulted). |
| `bank_nifty_divergence` | `number` | Same — present in model, absent from REST response constructor. |

**Fix location:** `engine/api/rest_routes.py` — `market_context()` function

---

### 2. `GET /rankings/top25/{direction}` → `RankingEntry[]`

| Missing Field | Frontend Type | Notes |
|---|---|---|
| `direction` | `Direction` | Each entry is missing the `direction` field. Frontend type `RankingEntry` requires it; backend returns `Direction.LONG` default in model but doesn't include in REST response JSON. |

**Fix location:** `engine/api/rest_routes.py` — `rankings()` function

---

### 3. `GET /rankings/{symbol}/factors` → `SymbolFactorBreakdown`

| Field | Frontend Type | Backend Type | Notes |
|---|---|---|---|
| `l4_sector.sector_name` | `string` | Missing | Backend `L4SectorFrame` has `sector_id` but not `sector_name`. Frontend `L4SectorFrame` interface has `sector_name: string` which will be `undefined` from API. |

**Fix location:** `engine/models/frames.py` — `L4SectorFrame` model and `SymbolFactorBreakdown` response construction

---

## Section C: Type Soundness Issues (Runtime OK, TypeScript Mismatch)

These are backend Pydantic models returning plain `str` where the frontend TypeScript has strict union/enum types. These **work at runtime** but TypeScript type narrowing is unsound:

| Field | Backend Model | Backend Returns | Frontend Type |
|---|---|---|---|
| `L5ScoreBreakdown.regime` | `str` (default `"Range-Bound"`) | plain string | `Regime = 'Trending-Up' \| 'Trending-Down' \| 'Range-Bound'` |
| `L6RankSnapshot.rank_movement` | `str` (default `"STABLE"`) | plain string | `RankMovement = 'NEW' \| 'UP' \| 'DOWN' \| 'STABLE'` |
| `L6RankSnapshot.liquidity_quality` | `str` (default `"Good"`) | plain string | `LiquidityQuality = 'Excellent' \| 'Good' \| 'Marginal' \| 'Poor'` |
| `L8ThesisSnapshot.actionability_tier` | `str` (default `"Research-Only"`) | plain string | `ActionabilityTier = 'Tradeable' \| 'Constrained' \| 'Research-Only'` |

**Fix location:** `engine/models/frames.py` — use `Literal` types or `Enum` for these fields

---

## Section D: WebSocket — Missing Message Types

The frontend `useWebSocket.ts` subscribes to channels: `market`, `rankings`, `theses`, `edge`. The backend **implements** the existing 5 message types:

| Message Type | Backend | Frontend Consumer |
|---|---|---|
| `L1_CONTEXT` | ✅ Implemented | `RegimeBanner`, `useMarketStore.context` |
| `L6_RANKINGS` | ✅ Implemented | `useMarketStore.longRankings/shortRankings` |
| `L8_THESIS` | ✅ Implemented | `ActiveMonitor`, `useMarketStore.theses` |
| `L9_INVALIDATION` | ✅ Implemented | `ActiveMonitor`, `useMarketStore.invalidatedTheses` |
| `L10_EDGE` | ✅ Implemented | `EdgePanel`, `useMarketStore.edgeTiers` |

The backend `websocket_manager.py` comments also reference **planned-but-not-implemented** message types:

| Planned Message | Frontend Expects | Status |
|---|---|---|
| `ALERT` — `{type, symbol, message}` | `AlertToast` component listens for WS events, but current implementation uses internal `useAlertFeed` from simulator. Real backend ALERT messages would need WS broadcast. | ⚠️ PLANNED (commented in ws_manager.py) |
| `FUNNEL_COUNTS` — `{L1: {in, out}, ...}` | `FunnelStrip` component receives funnel via props (from simulator); no direct WS dependency. Low priority. | ⚠️ PLANNED |
| `CYCLE_ACTIVITY` — `{id, type, symbol, ...}` | `CycleActivity` component uses `useCycleActivity` hook (simulator-only); no direct WS dependency. Low priority. | ⚠️ PLANNED |

---

## Section E: Frontend Type Additions (Backend Returns More Than Frontend Types)

The backend `ThesisCard` model includes 5 fields that the frontend TypeScript `ThesisCard` interface does not:

| Extra Backend Field | Type |
|---|---|
| `cost_breakdown` | `dict` |
| `slippage_bps` | `float` |
| `liquidity_quality` | `LiquidityQuality` |
| `net_reward` | `float` |
| `net_risk` | `float` |

These are silently ignored by the frontend (no runtime error). For completeness, the backend team may want these surfaced in the frontend types.

---

## Priority Order for Backend Team

| Priority | Gap | Impact |
|---|---|---|
| **P0** | `/market/context` missing `vix_value`, `bank_nifty_divergence` | RegimeBanner shows incomplete context data |
| **P0** | `/rankings/top25/{direction}` missing `direction` per entry | RankingsPanel shows `undefined` direction |
| **P1** | `SymbolFactorBreakdown.l4_sector.sector_name` missing | FactorGrid shows `undefined` sector name |
| **P2** | Enum-as-string type unsoundness (P0 runtime works, but TS types unsound) | TypeScript strict mode errors |
| **P3** | `GET /market/candles/{symbol}` not implemented | ChartPanel cannot show historical candles (future feature) |
| **P4** | `ALERT`, `FUNNEL_COUNTS`, `CYCLE_ACTIVITY` WS messages planned but not broadcast | AlertToast and FunnelStrip rely on simulator for these |
| **P5** | `ThesisCard` frontend type missing 5 backend fields | Data available but not typed on frontend |

**The 404s** (`/funnel/counts`, `/activity/events`, `/monitor/active-theses`) — these appear in the backend log but **no frontend component actually calls these**. They are either:
1. Stale proxy requests from old frontend code that was later removed
2. Or routes that the frontend simulator generates internally but which were never wired to real REST endpoints

Check with frontend team whether these endpoints are still needed before implementing.

---

*Document generated by Claude Code after full frontend audit — 2026-05-19*