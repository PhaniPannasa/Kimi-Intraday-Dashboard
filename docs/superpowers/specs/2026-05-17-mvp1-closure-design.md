# MVP 1 Closure Design — Frontend Blockers & Backend Deviations

**Date:** 2026-05-17
**Scope:** Close all remaining open items from MVP 1 implementation
**Worktree:** `.worktrees/mvp1/`
**Approach:** B — Frontend-First, Then Backend

---

## 1. Remaining Open Items

### Frontend (5 items)
1. `main.tsx` — missing `QueryClientProvider` (React Query inactive)
2. `useRankings.ts` & `useMarketContext.ts` — hardcoded `http://localhost:8170/...` instead of `/api` proxy
3. `useWebSocket.ts` — missing handlers for `L8_THESIS`, `L9_INVALIDATION`, `L10_EDGE`
4. `ChartPanel.tsx` — missing entirely (Task 30 from plan)
5. `index.html` — stale `/vite.svg` favicon link

### Backend (4 items)
6. `datetime.utcnow()` deprecation warnings in `frames.py`, `rest_routes.py`
7. L8 cost model — uses placeholder math instead of exact Indian brokerage/STT formulas
8. L10 — missing `wilson_ci`, `benjamini_hochberg`, `bayesian_bootstrap`
9. L9 shadow ledger API — `register`/`check` vs planned `on_trigger`/`on_tick`

---

## 2. Phase 1: Frontend Closure

### 2.1 main.tsx — Add QueryClientProvider

Import `QueryClient` and `QueryClientProvider` from `@tanstack/react-query`. Instantiate `queryClient` at module level. Wrap `<App />` with the provider in the React root render.

### 2.2 /api Proxy + Hook Fixes

Add to `vite.config.ts` under `server.proxy`:
```ts
'/api': {
  target: 'http://localhost:8170',
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/api/, ''),
}
```

Update `useRankings.ts` to fetch `/api/rankings/top25/${direction}`.
Update `useMarketContext.ts` to fetch `/api/market/context`.
Update `useWebSocket.ts` to connect to `ws://localhost:8170/ws/v1/stream` (WS is not proxied via /api).

### 2.3 index.html — Remove Stale Favicon

Remove the `<link rel="icon" type="image/svg+xml" href="/vite.svg" />` line.

### 2.4 useWebSocket.ts — Add Missing Handlers

Extend the `switch (msg.type)` block:
- `L8_THESIS` → call `addOrUpdateThesis(msg.payload)` in store
- `L9_INVALIDATION` → call `invalidateThesis(msg.payload.thesis_id, msg.payload.reason)` in store
- `L10_EDGE` → call `updateEdgeTier(msg.payload.tier, msg.payload.promotion)` in store

Add corresponding setters to `marketStore.ts`.

### 2.5 ChartPanel.tsx — New Component

Create `frontend/src/components/ChartPanel.tsx`:
- Uses `lightweight-charts` `createChart` and `addCandlestickSeries`
- Props: `{ data: CandlestickData[] }`
- Dark theme: background `#1f2937`, text `#d1d5db`, grid lines `#374151`
- Height: 300px, width: 100% of container
- Cleans up chart instance in `useEffect` return

### 2.6 App.tsx — Integration

Import `ChartPanel`. Add it below the existing `lg:grid-cols-3` block inside a wrapper div with heading "Price Chart". Pass empty array `[]` as initial data.

### 2.7 Phase 1 Verification
- `cd frontend && npm run build` succeeds with zero errors
- `cd frontend && npx vitest run` passes

---

## 3. Phase 2: Backend Closure

### 3.1 datetime.utcnow() Deprecation

Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` in:
- `engine/models/frames.py` (default value for `valid_until`)
- `engine/api/rest_routes.py` (last_bar_processed)

Ensure `timezone` is imported from `datetime`.

### 3.2 L8 Cost Model — Exact Indian Brokerage/STT

Create `engine/core/cost_model.py` with:

```python
def estimate_net_return(
    gross_return_pct: float,
    entry_price: float,
    exit_price: float,
    quantity: int,
    brokerage_per_order: float = 20.0,
) -> dict:
    turnover = (entry_price + exit_price) * quantity
    stt = 0.000125 * exit_price * quantity  # sell-side only
    exchange = 0.00002 * turnover
    sebi = 10.0 * turnover / 1_00_00_000
    gst = 0.18 * (brokerage_per_order * 2 + exchange + sebi)
    stamp = 0.00003 * entry_price * quantity
    total_cost = brokerage_per_order * 2 + stt + exchange + sebi + gst + stamp
    gross_pnl = (exit_price - entry_price) * quantity
    net_pnl = gross_pnl - total_cost
    net_return_pct = net_pnl / (entry_price * quantity) * 100
    return {
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "total_cost": total_cost,
        "turnover": turnover,
    }
```

Update `L8Thesis.assemble()` to call `estimate_net_return` and set `net_rr` on the returned `ThesisCard`.

### 3.3 L9 Shadow Ledger API Alignment

Rename methods in `L9ShadowLedger`:
- `register(thesis)` → `on_trigger(thesis)`
- `check(price)` → `on_tick(price)`
- `force_expire()` → `on_force_expire()`

Update all call sites in `rest_routes.py` and `websocket_manager.py` to use the new names. No logic changes.

### 3.4 L10 Statistical Methods

Add three internal helpers to `l10_edge.py`:

**wilson_ci(hit_rate, n, z=1.96)**
```python
def wilson_ci(hit_rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = hit_rate
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))
```

**benjamini_hochberg(p_values, alpha=0.05)**
```python
def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    if not p_values:
        return []
    sorted_idx = sorted(range(len(p_values)), key=lambda i: p_values[i])
    m = len(p_values)
    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            significant[idx] = True
    return significant
```

**bayesian_bootstrap(returns, n_bootstrap=10000)**
```python
def bayesian_bootstrap(returns: list[float], n_bootstrap: int = 10000) -> dict:
    import random
    means = []
    n = len(returns)
    for _ in range(n_bootstrap):
        weights = [random.random() for _ in range(n)]
        total = sum(weights)
        weights = [w / total for w in weights]
        mean = sum(w * r for w, r in zip(weights, returns))
        means.append(mean)
    means.sort()
    return {
        "mean": sum(means) / len(means),
        "ci_lower": means[int(0.025 * n_bootstrap)],
        "ci_upper": means[int(0.975 * n_bootstrap)],
    }
```

Update `L10EdgeLookup.lookup()` to use `wilson_ci` for confidence interval computation when raw `ci_lower`/`ci_upper` are not provided in the store. Update `populate()` to accept an optional `run_fdr` flag that runs BH correction across all loaded rows.

### 3.5 Phase 2 Verification
- `cd engine && pytest` passes (77 existing + new tests)
- No `DeprecationWarning` for `utcnow`

---

## 4. Data Flow

### Frontend WebSocket Flow
```
Server ──L8_THESIS──────► useWebSocket ──► marketStore.theses ──► ThesisCard
Server ──L9_INVALIDATION──► useWebSocket ──► marketStore.invalidate ──► AlertToast
Server ──L10_EDGE────────► useWebSocket ──► marketStore.edgeTiers ──► EdgePanel
```

### Backend Cost Model Flow
```
l8_thesis.py assemble()
  └── cost_model.estimate_net_return()
        └── ThesisCard.net_rr (accurate after STT/brokerage/GST)
```

---

## 5. Testing Strategy

| Phase | What | How |
|---|---|---|
| 1 | Hook proxy URLs | Vitest unit test mocking fetch |
| 1 | WebSocket handlers | Vitest unit test with mock WebSocket |
| 1 | ChartPanel render | Vitest + React Testing Library |
| 1 | Build integrity | `npm run build` |
| 2 | Cost model accuracy | pytest with known price/quantity |
| 2 | Wilson CI correctness | pytest against scipy.stats proportion_confint or hand-calculated |
| 2 | BH FDR correctness | pytest with known p-value arrays |
| 2 | Bayesian bootstrap | pytest verifying CI contains mean |
| 2 | L9 rename | pytest verifying `on_trigger`/`on_tick` exist and behave like old methods |
| 2 | utcnow deprecation | pytest with `warnings` filter assertion |

---

## 6. Success Criteria

- [ ] Frontend `npm run build` succeeds with zero errors
- [ ] Frontend Vitest suite passes
- [ ] Backend `pytest` passes (77 existing + new tests)
- [ ] No `datetime.utcnow()` deprecation warnings in test output
- [ ] L8 `net_rr` reflects real Indian F&O brokerage + STT + GST + stamp duty
- [ ] L10 uses Wilson score CI and optionally BH FDR correction
- [ ] L9 API names match implementation plan (`on_trigger` / `on_tick` / `on_force_expire`)
- [ ] `index.html` has no stale `vite.svg` reference
- [ ] WebSocket delivers `L8_THESIS`, `L9_INVALIDATION`, `L10_EDGE` to frontend store
