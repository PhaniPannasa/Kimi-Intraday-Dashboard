# Factor Breakdown Dashboard — Design Spec

**Date:** 2026-05-17  
**Scope:** Make the L1–L10 pipeline visible to the user with data-freshness signals and per-stock factor drill-down.  
**Approach:** #2 (New Factor Breakdown API + Frontend decorations)

---

## 1. Goals

1. **Transparency** — A user clicking a Top 25 row sees *exactly* why that stock was scored and ranked (L2 universe flags, L3 indicator snapshot, L5 sub-scores, L7 confluence checklist).
2. **Trust** — Every data card shows its own age ("Updated 12 s ago"). A global pipeline bar shows the engine is alive and which layers are cycling.
3. **Actionability** — Rankings are no longer a black-box list; they become inspectable research candidates.

---

## 2. New REST Endpoints

### `GET /api/v1/rankings/{symbol}/factors`
Returns the full factor trail for a single symbol that contributed to its latest score.

**Response model:** `SymbolFactorBreakdown`

```json
{
  "symbol": "RELIANCE",
  "direction": "LONG",
  "last_updated": "2026-05-17T09:31:05+05:30",
  "l2_universe": {
    "fo_eligible": true,
    "fo_ban": false,
    "mwpl_status": "None",
    "earnings_flag": "None",
    "liquidity_quality": "Excellent",
    "lqs_score": 0.87
  },
  "l3_signals": {
    "ema_9": 2455.2,
    "ema_20": 2430.1,
    "ema_50": 2400.5,
    "ema_aligned": true,
    "supertrend_dir": 1,
    "adx": 28.4,
    "rsi": 56.2,
    "macd_hist": 1.35,
    "atr": 12.5,
    "atr_pct": 0.51,
    "bb_width": 2.1,
    "vwap": 2448.0,
    "above_vwap": true,
    "roc_20": 3.2
  },
  "l4_sector": {
    "sector_id": 8,
    "sector_name": "Energy",
    "rs_ratio": 1.08,
    "rs_momentum": 1.02,
    "rotation_rank": 3
  },
  "l5_scores": {
    "total": 84.5,
    "f1_trend": 85,
    "f2_momentum": 72,
    "f3_volume": 90,
    "f4_volpos": 68,
    "f5_structure": 88,
    "f6_sector": 75,
    "f7_risk": 82,
    "regime": "Trending-Up",
    "modifiers": {
      "fo_ban": 0,
      "earnings": 0,
      "strong_sector": 3,
      "index_change": 0
    }
  },
  "l6_ranking": {
    "previous_score": 78.2,
    "score_change": 6.3,
    "rank_movement": "UP",
    "liquidity_quality": "Excellent"
  },
  "l7_confluence": {
    "score": 5,
    "max": 6,
    "checks": {
      "strong_close": true,
      "volume_confirm": true,
      "non_exhaustion": true,
      "htf_alignment": true,
      "risk_distance": true,
      "reward_distance": false
    }
  },
  "l8_thesis": {
    "thesis_id": "RELIANCE-ORB-20260517-0931",
    "setup_type": 1,
    "trigger": 2450.5,
    "invalidation": 2420.0,
    "t1": 2495.0,
    "t2": 2530.0,
    "gross_rr": 1.5,
    "net_rr": 1.35,
    "grade": "ATTRACTIVE",
    "actionability_tier": "Tradeable"
  }
}
```

**Backend implementation notes:**
- The orchestrator already computes all of these values during the 1-min pipeline cycle. The endpoint reads the *last computed* values from Redis (not recomputing on demand).
- Redis key: `factors:{symbol}` → JSON hash, TTL 5 min.
- If Redis miss → return 404 with `"detail": "No factor data available for {symbol}. Pipeline may not have run yet."`

### `GET /api/v1/pipeline/status`
Returns the health and freshness of each pipeline layer.

**Response model:** `PipelineStatusResponse`

```json
{
  "last_cycle_at": "2026-05-17T09:31:05+05:30",
  "cycle_duration_ms": 4200,
  "market_session": "Open",
  "time_bucket": "Trend Establishment",
  "layers": {
    "l1_market_context":  { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 45 },
    "l2_universe":        { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 120 },
    "l3_signals":         { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 890 },
    "l4_sector":          { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 30 },
    "l5_scoring":         { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 560 },
    "l6_ranking":         { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 80 },
    "l7_confluence":      { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 340 },
    "l8_thesis":          { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 210 },
    "l9_monitor":         { "status": "ok", "last_run": "2026-05-17T09:31:05+05:30", "duration_ms": 150 },
    "l10_edge":           { "status": "ok", "last_run": "2026-05-17T09:31:04+05:30", "duration_ms": 95 }
  }
}
```

**Backend implementation notes:**
- The pipeline orchestrator writes layer timings to Redis at the end of each cycle.
- Redis key: `pipeline:status` → JSON hash, TTL 2 min.
- `status` values: `ok` (ran within last 2 min), `stale` (last run > 2 min), `error` (exception logged).

---

## 3. WebSocket Changes

No new WS channels required. Existing messages keep their current shape, but we **add a `timestamp` field** to every broadcast so the frontend can compute data age:

| Type | Existing fields | Added |
|---|---|---|
| `L1_CONTEXT` | `payload: MarketContextFrame` | `timestamp` (already present) |
| `L6_RANKINGS` | `payload: {long, short}` | `timestamp` (already present) |
| `L8_THESIS` | `payload: {thesis_id, card}` | `timestamp` (already present) |
| `L9_INVALIDATION` | `payload: {thesis_id, reason}` | `timestamp` (already present) |
| `L10_EDGE` | `payload: {tier, promotion}` | `timestamp` (already present) |

The frontend uses these ISO timestamps to render relative age ("12 s ago").

---

## 4. Frontend Architecture

### New Components

| Component | Source | Purpose |
|---|---|---|
| `PipelineStatusBar` | New | Global top strip: L1→L10 dots + last cycle time + market session |
| `DataAgeBadge` | New | Reusable pill: "Updated 12 s ago" / "Updated 1 m ago" / stale warning |
| `RankingRowExpanded` | New | Inline expansion beneath a Top 25 row; fetches `/rankings/{sym}/factors` |
| `FactorGrid` | New | Sub-component inside expansion: L2/L3/L4/L5/L7 mini cards |
| `ConfluenceChecklist` | New | 6 pass/fail items with icons inside FactorGrid |
| `ScoreBreakdown` | New | Horizontal bar chart of f1–f7 sub-scores |

### Component Hierarchy (updated)

```
App.tsx
├── PipelineStatusBar            ← NEW: global layer health
├── RegimeBanner
│   └── DataAgeBadge             ← NEW: "Updated X ago"
├── DashboardGrid
│   ├── Top25Table
│   │   └── RankingRow
│   │       └── RankingRowExpanded   ← NEW: inline factor drill-down
│   │           ├── FactorGrid
│   │           │   ├── L2Flags
│   │           │   ├── L3SignalSnapshot
│   │           │   ├── L4SectorBadge
│   │           │   ├── ScoreBreakdown
│   │           │   └── ConfluenceChecklist
│   │           └── ThesisQuickLink
│   ├── ThesisPanel
│   ├── ActiveMonitor
│   ├── EdgePanel
│   └── ChartPanel
└── AlertToast
```

### State & Data Flow

- **Pipeline status** — TanStack Query polling `GET /pipeline/status` every 15 s, stale-time 10 s.
- **Factor breakdown** — TanStack Query fetching `GET /rankings/{sym}/factors` on row expand, cached 60 s.
- **Data age** — Each WS message carries a timestamp. A lightweight `useDataAge(timestamp)` hook computes relative time and returns a freshness enum (`fresh`, `aging`, `stale`).

### Responsive Behaviour

- **Mobile (< 768 px):** PipelineStatusBar collapses to a compact row (dots + last cycle time only). FactorGrid stacks vertically (L2 → L3 → L4 → L5 → L7).
- **Tablet (768–1024 px):** FactorGrid uses 2 columns.
- **Desktop (> 1024 px):** FactorGrid uses 3 columns. PipelineStatusBar shows full layer labels on hover.

---

## 5. UI Details

### PipelineStatusBar

```
[● L1] [● L2] [● L3] [● L4] [● L5] [● L6] [● L7] [● L8] [● L9] [● L10]   Open · Trend Establishment   Last cycle: 09:31:05 IST (4.2 s)
```

- Dot color: `green` (ok, < 2 min), `yellow` (stale, 2–5 min), `red` (error or > 5 min).
- Hovering a dot shows a tooltip: `"L3 Signals — last run 09:31:05 · 890 ms"`.
- If any layer is stale/error, the bar background subtly tints yellow/red.

### DataAgeBadge

- `fresh` (< 60 s): `text-[var(--text-secondary)]` — "Updated 12 s ago"
- `aging` (60–180 s): `text-[var(--trade-neutral)]` — "Updated 2 m ago"
- `stale` (> 180 s): `text-[var(--trade-short)]` + pulse icon — "Updated 5 m ago"

Placed in the top-right corner of RegimeBanner, Top25Table headers, ThesisPanel, ActiveMonitor, EdgePanel.

### RankingRowExpanded (inline expansion)

Triggered by clicking a row in Top25Table. Expands beneath the row with a smooth height transition.

**Layout (desktop):**
```
┌─────────────────────────────────────────────────────────────┐
│  L2 Universe          L3 Signals          L4 Sector         │
│  [F&O ✓] [MWPL ✓]     EMA 9/20/50 ▲      Energy #3         │
│  [Earn ✓] [LQS 87%]   RSI 56  ADX 28     RS-Ratio 1.08    │
├─────────────────────────────────────────────────────────────┤
│  Score Breakdown (f1–f7 bars)                               │
│  Trend ████████░░ 85   Momentum ██████░░░░ 72  ...         │
├─────────────────────────────────────────────────────────────┤
│  Confluence 5/6                                             │
│  ✓ Strong close  ✓ Volume  ✓ Non-exhaustion                │
│  ✓ HTF align     ✓ Risk     ✗ Reward distance              │
├─────────────────────────────────────────────────────────────┤
│  [View Full Thesis →]                                       │
└─────────────────────────────────────────────────────────────┘
```

**Mobile:** stacks all sections vertically.

### ScoreBreakdown

- 7 horizontal bars, one per factor (f1–f7).
- Bar width = score / 100.
- Color: green ≥ 70, yellow 40–69, red < 40.
- Show numeric score at the end of each bar.
- On hover, show the factor name + weight for the current regime.

### ConfluenceChecklist

- 6 items in a 2×3 grid (desktop), 1×6 stack (mobile).
- Each item: icon (✓ or ✗) + label + optional tooltip explaining the check.
- Passed items: green tint. Failed items: red tint with strike-through.

---

## 6. Backend Implementation Notes

### Redis Schema Additions

```
factors:{symbol} → JSON (SymbolFactorBreakdown), TTL 300
pipeline:status  → JSON (PipelineStatusResponse), TTL 120
pipeline:layer:{layer_name} → Hash {last_run, duration_ms, status}, TTL 120
```

### Pipeline Orchestrator Changes

At the end of each 1-min cycle, after L10 completes:
1. Write each symbol's factor breakdown to `factors:{symbol}`.
2. Write layer timings to `pipeline:layer:{name}`.
3. Aggregate all layer statuses into `pipeline:status`.

### Pydantic Models

New files in `engine/models/frames.py` (or a new `engine/models/factors.py`):
- `L2UniverseFrame`
- `L3SignalFrame`
- `L4SectorFrame`
- `L5ScoreBreakdown`
- `L6RankSnapshot`
- `L7ConfluenceFrame`
- `SymbolFactorBreakdown`
- `PipelineLayerStatus`
- `PipelineStatusResponse`

### REST Routes

New routes in `engine/api/rest_routes.py`:
- `GET /rankings/{symbol}/factors`
- `GET /pipeline/status`

---

## 7. Out of Scope (for this spec)

- Historical factor comparison ("what was RELIANCE's score 10 min ago?")
- Animated transitions on the pipeline bar
- Push notifications for layer errors
- Export factor data to CSV/PDF

---

## 8. Testing Strategy

- **Backend:** Unit tests for new Redis writes in pipeline; FastAPI TestClient for `/rankings/{sym}/factors` and `/pipeline/status`.
- **Frontend:** Vitest for `useDataAge` hook, `DataAgeBadge` states, `ScoreBreakdown` rendering. MSW mocks for new REST endpoints.
- **E2E:** Open dashboard → verify pipeline bar renders → click a ranking row → verify inline expansion fetches and displays factor grid.

---

END OF SPEC
