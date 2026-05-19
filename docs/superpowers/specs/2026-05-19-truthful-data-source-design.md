---
name: 2026-05-19-truthful-data-source-design
description: Phase A — strip the simulator/mock lies from the Kimi Intraday Dashboard and surface per-component data-source truth via X-Data-Source header, WS source field, telemetry endpoint, MOCK badges, and a debug panel
status: draft
phase: A
authors: ["Phani", "Claude"]
related:
  - docs/backend-api-gaps.md
  - docs/superpowers/specs/2026-05-19-frontend-api-gaps.md
  - docs/superpowers/specs/2026-05-19-intraday-monitoring-log.md
---

# Truthful Data Source — Phase A Design

## TL;DR

The dashboard at https://kimi.intraday-edge-4zz.uk/ currently presents 100% mock data as if it were live market data. There are two independent fabrication paths — a client-side simulator running every 10 seconds and a backend mock fallback on every REST endpoint — and the UI gives the operator no way to tell them apart from real pipeline output. This spec covers **Phase A**: rip out the client simulator, surface the existing `X-Data-Source` header per panel, add a `source` field to every WebSocket message, expose a `/api/telemetry/data-sources` summary endpoint, and render per-component `MOCK` badges plus a `DataSourceDebugPanel`. After Phase A, every panel will visibly declare whether it's showing real pipeline output, backend mock, or stub data — making the genuine wiring gaps (Phase B, separate spec) self-evident.

---

## 1. Audit Findings — what is mock right now

### 1.1 Live REST headers (verified 2026-05-19, 22:59 IST, market closed)

| Endpoint | `X-Data-Source` returned |
|---|---|
| `/api/market/context` | `mock` |
| `/api/rankings/top25/long` | `mock` |
| `/api/rankings/top25/short` | `mock` |
| `/api/funnel/counts` | `mock` |
| `/api/monitor/active-theses` | `mock` |
| `/api/pipeline/status` | `mock` |
| `/api/edge/tiers` | (no header set, always mock-generated) |
| `/api/activity/events` | (no header set, always mock-generated) |
| `/api/thesis/{id}` | `mock` |
| `/api/rankings/{symbol}/factors` | (no header set, always mock-generated) |
| `/api/market/candles/{symbol}` | `mock` |
| `/api/health` | (no header set; body fields hardcoded) |

### 1.2 Why every endpoint returns mock

`engine/api/rest_routes.py` follows the pattern:
```python
if pipeline.latest_long_rankings:
    response.headers["X-Data-Source"] = "pipeline"
    return pipeline.latest_long_rankings[:25]
response.headers["X-Data-Source"] = "mock"
# ... mulberry32 PRNG generates fake RankingEntry list
```

`pipeline.latest_*` is populated only by `PipelineOrchestrator._run_live_cycle()`, which:
- Only runs when `market_session.current_phase() == "live"` (09:15–15:30 IST on trading days)
- Requires at least 20 real Upstox bars per symbol before it can run L3 indicators
- Has no scheduler entry actually firing it right now (verified via `/api/pipeline/status` returning mock)

So outside market hours, on weekends, or whenever the Upstox WebSocket has not been ingesting ticks long enough to fill TickBuffer, every endpoint silently falls back to seeded `mulberry32` PRNG output.

### 1.3 Frontend simulator (client-side fabrication)

`frontend/src/App.tsx:24` defines `REFRESH_BASE_MS = 60000` and `frontend/src/App.tsx:121` sets `speed = 6` — so the simulator cycles every **10 seconds**, not 60. Every cycle:
1. Calls `genUniverse(cycle)` (`frontend/src/data/engineSimulator.ts:313`) → fabricates 50 stocks with full L2-L10 fields via `mulberry32` PRNG, returns top-25 long + top-25 short.
2. Calls `genMarketContext(cycle)` → fabricates regime, VIX, breadth, time bucket, event flags.
3. Calls `genPipelineStatus(cycle, ts)` → fabricates per-layer durations.
4. Calls `syncToStore(universe, ctx)` (`App.tsx:49`) which **writes the fake data directly into the Zustand store** if no real data has arrived from WS. Components reading `useMarketStore.longRankings` / `.context` cannot distinguish this from real pipeline output.

The simulator is the source of every "MAJOR REGIME SHIFT" entry in `docs/superpowers/specs/2026-05-19-intraday-monitoring-log.md`. All 58 intervals recorded in that log were monitoring simulator PRNG output, not real market data.

### 1.4 "Real pipeline" mode still contains hardcoded values

Even when `_run_live_cycle()` does run with real Upstox bars, several L1-L10 fields are not real:

| Location | Field | Issue |
|---|---|---|
| `engine/core/pipeline.py:405` | `vix_value = 15.0` | VIX hardcoded |
| `engine/core/pipeline.py:393` | `setup_type = random.randint(1, 6)` | Random setup type |
| `engine/core/pipeline.py:394` | `actionability_tier = "Research-Only"` | Hardcoded |
| `engine/core/pipeline.py:395` | `liquidity_quality = random.choice(...)` | Random |
| `engine/core/pipeline.py:770` | `_synthetic_sector_data(symbol)` | L4 sector RS placeholder |
| `engine/core/pipeline.py:44` | `SYMBOL_TO_INSTRUMENT_KEY` | 30 symbols, not 100 |

L2 universe (F&O ban, MWPL, earnings) is not wired at all in `_run_live_cycle()`. These are Phase B concerns.

### 1.5 WebSocket subscribe-ack lies

`engine/api/websocket_manager.py:376–391` sends a hardcoded stub on `subscribe`:

```python
if "market" in channels:
    await websocket.send_json({
        "type": "L1_CONTEXT",
        "timestamp": now(),
        "payload": MarketContextFrame(
            regime=Regime.TRENDING_UP,
            regime_confidence=0.85,
        ).model_dump(),
    })
if "rankings" in channels:
    await websocket.send_json({
        "type": "L6_RANKINGS",
        "timestamp": now(),
        "payload": {"long": [], "short": []},
    })
```

The `Trending-Up` regime payload is a lie that immediately populates `RegimeBanner` on every page load, before any real pipeline cycle has run.

### 1.6 `/api/health` body is hardcoded

`engine/api/rest_routes.py:572–583`:
```python
return HealthResponse(
    status="healthy",
    websocket="connected",
    top25_long_count=25,
    top25_short_count=25,
    active_theses=4,
    token_expires_in_days=365,
    db_connected=True,
    redis_connected=True,
    scheduler_jobs=12,
)
```
None of these reflect actual runtime state.

---

## 2. Goal and Non-Goals

### 2.1 Goal (Phase A)

Make the dashboard truthful — every panel reveals whether its data is from the real pipeline, the backend mock fallback, or a stub — and remove the client-side simulator entirely so there is exactly one fabrication path (backend mock) with explicit labeling.

### 2.2 Out of scope (deferred to Phase B)

- Implementing real Upstox tick ingestion / bar accumulation in production
- Real VIX feed
- Real L2 universe (NSE scraper for F&O ban / MWPL / earnings)
- Real L4 sector RS (sector index feeds)
- Symbol universe expansion (30 → 100)
- L9 outcomes persisted to TimescaleDB so L10 edge stats accumulate
- Implementing `ALERT`, `FUNNEL_COUNTS`, `CYCLE_ACTIVITY` WS message types
- The 12 functional gaps listed in `docs/backend-api-gaps.md`

After Phase A ships, the dashboard will *show* you which Phase B gaps still produce MOCK badges, in priority order, so Phase B can write itself.

### 2.3 Success criteria

- Visiting https://kimi.intraday-edge-4zz.uk/ at 22:00 IST (market closed) shows every panel with a visible `MOCK` badge.
- Visiting at 10:30 IST (market open, pipeline running) shows badges disappear endpoint by endpoint as real data flows.
- The `DataSourceDebugPanel` reports the real pipeline phase (`closed` / `pre-market` / `live` / `closing`), real `last_cycle_at`, and real `symbols_feeding` count.
- `grep -r mulberry32 frontend/src/` returns no matches.
- `grep -r engineSimulator frontend/src/` returns no matches.

---

## 3. Design

### 3.1 Backend changes

#### 3.1.1 `engine/api/websocket_manager.py`

- **Add `source` field to every broadcast payload.** Modify the broadcast methods to wrap every payload as `{"type": ..., "timestamp": ..., "source": "pipeline", "payload": ...}`. The orchestrator's broadcasts (L1/L6/L8/L9/L10) set `source="pipeline"`. Any future stub broadcasts would set `source="stub"`.
- **Delete the subscribe-ack stub broadcasts** at the current lines 376–391. If a client subscribes and the pipeline has no data, the server simply acknowledges the subscription (the `SUBSCRIBED` message) and stays silent until a real cycle produces data. Frontend already handles the silence — that's what the `MOCK` badge on REST data is for.

#### 3.1.2 `engine/api/rest_routes.py`

- **Add `X-Data-Source` header to the endpoints missing it:**
  - `/health` — `pipeline` if `pipeline.latest_long_rankings` is non-empty AND Redis/DB pings succeed; else `mock`.
  - `/activity/events` — `pipeline` if a real activity log exists in Redis; else `mock`.
  - `/edge/tiers` — `pipeline` if `pipeline.latest_theses` has fed real outcomes to L10; else `mock`.
  - `/rankings/{symbol}/factors` — `pipeline` if Redis `factors:{symbol}` cache hit; else `mock`.
- **`/health` body becomes truthful:** read `top25_long_count` / `top25_short_count` / `active_theses` from `pipeline.latest_*` lengths. `last_bar_processed` from real aggregator state (`max(buf._current["ts"] for buf in pipeline.aggregator._buffers.values())`). `db_connected` / `redis_connected` from actual ping. `scheduler_jobs` from real APScheduler job count.

#### 3.1.3 New endpoint `GET /api/telemetry/data-sources`

Single canonical snapshot consumed by the `DataSourceDebugPanel`:

```json
{
  "timestamp": "2026-05-19T17:30:00Z",
  "endpoints": {
    "/market/context": "mock",
    "/rankings/top25/long": "mock",
    "/rankings/top25/short": "mock",
    "/funnel/counts": "mock",
    "/monitor/active-theses": "mock",
    "/pipeline/status": "mock",
    "/edge/tiers": "mock",
    "/activity/events": "mock",
    "/health": "mock",
    "/rankings/{symbol}/factors": "mock",
    "/market/candles/{symbol}": "mock"
  },
  "pipeline": {
    "phase": "closed",
    "last_cycle_at": null,
    "last_bar_at": null,
    "symbols_feeding": 0,
    "ws_connections": 1,
    "scheduler_running": true
  },
  "layers": {
    "l1_real": false,
    "l2_real": false,
    "l3_real": false,
    "l4_real": false,
    "l5_real": false,
    "l6_real": false,
    "l7_real": false,
    "l8_real": false,
    "l9_real": false,
    "l10_real": false
  }
}
```

Source values are derived from the same checks the existing REST endpoints already do (`pipeline.latest_* is empty` → mock). Layer reality flags come from: L1 real iff `pipeline.latest_context is not None and vix_value > 0 and vix_value != 15.0`; L3 real iff at least one symbol has ≥20 bars in TickBuffer; etc. — these checks live in a new helper `core/telemetry.py`.

#### 3.1.4 No backend mock fallback changes

The backend mock fallback code stays where it is. We don't remove it — the user opted explicitly for the per-component badge approach over hard empty states. The badge approach requires the mock fallback to keep working so the UI still has something to render outside market hours.

### 3.2 Frontend deletions

Delete the following from `frontend/src/`:

| Path | Action | Justification |
|---|---|---|
| `data/engineSimulator.ts` | **Delete entire file** | 501-line PRNG fabricator. Nothing in the truthful design needs it. |
| `App.tsx` lines 26–116 | Delete `useEngine` hook | Drives the 10-second client-side simulator cycle. |
| `App.tsx` lines 49–57 | Delete `syncToStore` function | Writes fake universe into Zustand. |
| `App.tsx` line 132 | Remove `useEngine` call | Top-level coupling to the simulator. |
| `App.tsx` lines 152–169 | Replace simulator-driven `funnel`, `activityEvents`, `useAlertFeed` calls | Replace with hooks fed by real REST/WS endpoints. |
| `App.tsx` lines 19–22 | Delete simulator imports | `genUniverse`, `genMarketContext`, `genPipelineStatus`, `computeFunnel`, `SimStock`, `SimSnapshot`, `SimMarketContext`. |
| `components/AlertToast.tsx` (`useAlertFeed`) | Remove simulator-coupling code paths; keep WS-driven path | Phase B will wire `ALERT` WS messages; for now `useAlerts` reads from store only. |
| `components/CycleActivity.tsx` (`useCycleActivity`) | Remove simulator-coupling code paths; replace with REST fetch from `/api/activity/events` | |

After this, `grep -r "engineSimulator\|mulberry32\|genUniverse\|genMarketContext\|genPipelineStatus" frontend/src/` returns zero matches.

### 3.3 Frontend additions

#### 3.3.1 `lib/apiFetch.ts` (new)

```ts
// Both REST and WS sources collapse into this union. REST emits 'pipeline' | 'mock';
// WS emits 'pipeline' | 'stub' (§7). 'unknown' covers missing headers / pre-spec WS messages.
export type DataSource = 'pipeline' | 'mock' | 'stub' | 'unknown';

export async function apiFetch<T>(url: string, init?: RequestInit):
    Promise<{ data: T; source: DataSource }> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  const source = (res.headers.get('X-Data-Source') ?? 'unknown') as DataSource;
  const data = (await res.json()) as T;
  return { data, source };
}
```

#### 3.3.2 `stores/marketStore.ts` — `sources` slice

Add to the existing store:

```ts
sources: Record<string, DataSource>;
setSource: (key: string, source: DataSource) => void;
```

Convention for `key`: the REST endpoint path with placeholders removed, e.g. `'rankings/top25/long'`, `'rankings/factors'`, `'market/candles'`. WS messages use the type name lowercased, e.g. `'ws/l1_context'`, `'ws/l6_rankings'`.

#### 3.3.3 `components/MockBadge.tsx` (new)

A small pill rendered inline in a panel header:

- `source === 'pipeline'` → render `null` (no badge).
- `source === 'mock'` → yellow pill `MOCK`, tooltip "Backend returned seeded mock data — pipeline has no live data for this endpoint".
- `source === 'stub'` → yellow pill `STUB`, tooltip "WebSocket pushed a placeholder payload (e.g. subscribe ack) rather than real pipeline output". (After we delete the WS subscribe-ack stub in §3.1.1 this is rare, but other planned stubs may exist.)
- `source === 'unknown'` → gray pill `?`, tooltip "Endpoint did not report a data source".

Single source of truth for the visual treatment; used by every panel. Naming the component `MockBadge` is acceptable shorthand since `mock` is the common case; the component handles all three non-pipeline states internally.

#### 3.3.4 `components/DataSourceDebugPanel.tsx` (new)

Collapsible panel pinned top-right (toggleable via header gear icon). Polls `/api/telemetry/data-sources` every 5 seconds. Renders:

- **Pipeline pulse:** phase chip, `last_cycle_at` relative time, `symbols_feeding` count, scheduler status, WS connection count.
- **Endpoints column:** one row per endpoint, green dot if `pipeline`, yellow if `mock`, gray if `unknown`.
- **Layers column:** L1 through L10, green if `*_real: true`, red otherwise. Hovering shows the criterion (e.g. "L1 real iff `vix_value != 15.0 and pipeline.latest_context is not None`").

Default state: collapsed (just a small "Truth" toggle). Expanded on first load if any layer is not real.

#### 3.3.5 Honest empty states per panel

Every panel must render a meaningful empty state when its hook returns `data === null/[]`:

| Panel | Empty state copy |
|---|---|
| `RegimeBanner` | "Market closed — no live context" (when phase=closed) / "Waiting for first L1 cycle..." (when phase=live but no data) |
| `RankingsPanel` | "No rankings yet — pipeline idle" |
| `FunnelStrip` | hide / dim with text "Pipeline has not run a cycle" |
| `PipelineStatusBar` | gray out all 10 layers; text "No cycles since startup" |
| `HealthStrip` | show last cycle "—" instead of fake "5s ago" |
| `DetailPanel` (factor breakdown) | "Select a symbol — factor breakdown will appear when L3+L5 produce real signals" |
| `ChartPanel` | "Candle data unavailable — pipeline aggregator has no bars for {symbol}" |
| `ActiveMonitor` | "No active theses" |
| `EdgePanel` | "No edge data — L10 needs at least 30 outcomes per tier" |
| `CycleActivity` | "No cycle activity yet" |
| `AlertToast` | (no change — event-driven; just no toasts when no events) |

These messages are not error states; they are honest "no data" states. The accompanying `MockBadge` clarifies whether the empty/sparse state is due to pipeline idleness (no badge) or a deliberate backend stub (yellow `MOCK`).

#### 3.3.6 WS source consumption

`hooks/useWebSocket.ts` already routes messages by `msg.type`. After backend adds `source` field, each `case` writes the source into the store:

```ts
case 'L1_CONTEXT':
  setContext(msg.payload);
  setSource('ws/l1_context', msg.source ?? 'unknown');
  break;
```

`RegimeBanner` reads `sources['ws/l1_context'] || sources['market/context']` — WS source wins when set, falls back to REST source.

### 3.4 Component → source mapping (the answer to "is it wired?")

| Component | REST endpoint key | WS message key | Where the badge renders |
|---|---|---|---|
| `RegimeBanner` | `market/context` | `ws/l1_context` | top-right of banner header |
| `RankingsPanel` (long) | `rankings/top25/long` | `ws/l6_rankings` | "Top 25 Long" header chip |
| `RankingsPanel` (short) | `rankings/top25/short` | `ws/l6_rankings` | "Top 25 Short" header chip |
| `FunnelStrip` | `funnel/counts` | `ws/funnel_counts` (Phase B) | header chip |
| `HealthStrip` | `health` + `pipeline/status` | — | footer chip |
| `PipelineStatusBar` | `pipeline/status` | — | header chip |
| `DetailPanel` | `rankings/factors` | — | header chip |
| `ChartPanel` | `market/candles` | — | header chip |
| `ActiveMonitor` | `monitor/active-theses` | `ws/l8_thesis` | header chip |
| `EdgePanel` | `edge/tiers` | `ws/l10_edge` | header chip |
| `CycleActivity` | `activity/events` | `ws/cycle_activity` (Phase B) | header chip |
| `AlertToast` | — | `ws/alert` (Phase B) | event-driven (no badge) |

### 3.5 New hooks needed

Replace the simulator-driven state with hooks fed by real endpoints:

| Hook | Endpoint | Notes |
|---|---|---|
| `useFunnelCounts()` | `/api/funnel/counts` | poll every 30s; subscribes to `ws/funnel_counts` for Phase B push |
| `useActiveTheses()` | `/api/monitor/active-theses` | poll every 30s; merge with WS `L8_THESIS` pushes |
| `useEdgeTiers()` | `/api/edge/tiers` | poll every 60s; merge with WS `L10_EDGE` pushes |
| `useActivityEvents()` | `/api/activity/events?since=` | poll every 15s; merge with WS `CYCLE_ACTIVITY` (Phase B) |
| `useCandles(symbol)` | `/api/market/candles/{symbol}` | fetch on symbol change; refresh every 60s |
| `useTelemetry()` | `/api/telemetry/data-sources` | poll every 5s; used by `DataSourceDebugPanel` only |

Existing hooks (`useRankings`, `useMarketContext`, `useFactorBreakdown`, `usePipelineStatus`, `useDataAge`) keep their REST endpoints but switch to `apiFetch` so they capture `source` and write to the store.

## 4. Testing strategy

### 4.1 Unit

- `apiFetch.test.ts` — header parsing; missing-header defaults to `unknown`; non-200 throws.
- `sourcesSlice.test.ts` — set/get; defaults; key normalization.

### 4.2 Component

- For each panel: render with `sources[key] = 'mock'` → asserts yellow `MOCK` badge present.
- For each panel: render with `sources[key] = 'pipeline'` → asserts no badge.
- For each panel: render with empty data → asserts the honest empty-state copy from §3.3.5 is shown.

### 4.3 Integration

- Pytest fixture: start backend with `pipeline.latest_* = []` → fetch each endpoint → assert all responses carry `X-Data-Source: mock`.
- Pytest fixture: monkey-patch `pipeline.latest_long_rankings = [<real RankingEntry>]` → assert `/api/rankings/top25/long` returns `X-Data-Source: pipeline`.
- Pytest: `GET /api/telemetry/data-sources` returns expected shape; layer flags flip when corresponding `pipeline.latest_*` is populated.

### 4.4 Manual smoke

After deploy:
1. Visit https://kimi.intraday-edge-4zz.uk/ outside market hours.
2. Expect: every panel has a visible yellow `MOCK` badge; `DataSourceDebugPanel` shows phase `closed`, `symbols_feeding: 0`, all 10 layers red.
3. Visit during market open tomorrow (09:15+ IST), if the orchestrator scheduler is actually firing.
4. Expect: badges should drop endpoint by endpoint as real cycles complete and `pipeline.latest_*` populates.

### 4.5 Regression — confirm simulator is fully gone

- `grep -r "mulberry32\|engineSimulator\|genUniverse\|genMarketContext\|genPipelineStatus\|computeFunnel" frontend/src/` returns zero matches.
- Frontend build (`npm run build`) succeeds with TypeScript strict mode (no unused imports).
- No console error or warning when loading the page with the backend serving only mock data.

## 5. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Removing the WS subscribe-ack stub means `RegimeBanner` shows "Waiting for first L1 cycle..." on every fresh load until first real cycle. | High | This is the intended truthful state. The MOCK badge on REST `/market/context` will appear immediately on first poll, populating the banner with the explicitly-labeled mock context within 1-2 seconds. |
| Deleting the frontend simulator removes the visually-rich demo mode used in past monitoring sessions. | Medium | Document this trade-off in the spec. A future "DEMO" URL flag could re-add the simulator behind explicit opt-in if needed — but that's deferred until the user asks for it. |
| `/api/telemetry/data-sources` polled every 5s by all open browser tabs could pressure the FastAPI process under load. | Low | Endpoint is read-only and cheap (pure introspection of `pipeline.latest_*` + scheduler state). Cap concurrent telemetry polls if measured impact > 5ms per request. |
| Per-component badge approach could be visually noisy outside market hours when everything is mock. | Low | A single global "Pipeline idle (market closed)" banner could be shown alongside the per-panel badges if user feedback is "too many badges". Defer until observed. |
| The "is this layer real?" heuristics in `core/telemetry.py` may give false positives (e.g. vix_value=15.0 by coincidence after L1 is wired). | Low | Replace heuristics with explicit `real_data: bool` flags on `pipeline.latest_context` etc. as part of Phase B wiring. For now, document the criteria in tooltips so the operator can mentally adjust. |

## 6. Rollout

Phase A is non-breaking from the user's perspective — every existing screen continues to render, but with truth labeling. Rollout in one merge:

1. Backend: add `X-Data-Source` headers + `source` WS field + `/api/telemetry/data-sources` + truthful `/health`.
2. Frontend: add `apiFetch`, `sources` slice, `MockBadge`, `DataSourceDebugPanel`, new hooks, honest empty states.
3. Frontend: delete `engineSimulator.ts` and refactor `App.tsx`.
4. Frontend: delete WS subscribe-ack stub.
5. Update `docs/superpowers/specs/2026-05-19-frontend-api-gaps.md` and `docs/backend-api-gaps.md` to reflect the new truth layer.

Recommended commit sequence:
- C1: Backend additive (headers + telemetry endpoint + truthful health) — safe alone.
- C2: Frontend additive (`apiFetch`, `sources` slice, `MockBadge`, `DataSourceDebugPanel`, hooks) — works with old simulator still present, just shows badges.
- C3: Frontend deletion (simulator + `useEngine` + `syncToStore` + WS subscribe-ack stub) — flips behavior.

## 7. Open questions / decisions deferred

- Should the `DataSourceDebugPanel` be visible to end-users in production, or dev-only? — Default: visible in production for now (this is a research tool, not a consumer dashboard); revisit when public users are added.
- Should `MOCK` badges be a different color than yellow (accessibility / colorblind)? — Use yellow + clear text label; revisit if contrast feedback comes in.
- Should the WS source field be `"pipeline" | "stub"` or `"pipeline" | "mock"`? — Use `"pipeline" | "stub"` so the WS taxonomy doesn't claim "mock" (mock implies fabricated; stub implies placeholder). REST keeps `"pipeline" | "mock"` since fallback is real fabrication.

---

*End of Phase A spec.* Phase B (wire real data layer by layer) is a separate spec, to be written after Phase A merges and the resulting badge map clarifies priority.
