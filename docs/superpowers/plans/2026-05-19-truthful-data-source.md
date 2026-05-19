# Truthful Data Source — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip the client-side simulator and surface per-component data-source truth across the Kimi Intraday Dashboard, so every panel visibly declares whether its data is real pipeline output, backend mock fallback, or a stub.

**Architecture:** Three sequential commit waves: (C1) Backend adds `X-Data-Source` headers on remaining endpoints, a `source` field on every WS broadcast, a `/api/telemetry/data-sources` endpoint, and a truthful `/health` body. (C2) Frontend adds an `apiFetch` wrapper, a Zustand `sources` slice, a `MockBadge` component, a `DataSourceDebugPanel`, and refactors all hooks to capture and store source. (C3) Frontend deletes `engineSimulator.ts`, the `useEngine` hook, `syncToStore`, and the WS subscribe-ack stub.

**Tech Stack:** Python 3.11 / FastAPI / Pydantic v2 / pytest (asyncio_mode=auto) on backend. React 18 / Vite / TypeScript strict / Zustand / TanStack Query / Vitest + jsdom on frontend.

**Spec:** [`docs/superpowers/specs/2026-05-19-truthful-data-source-design.md`](../specs/2026-05-19-truthful-data-source-design.md)

---

## File Structure

### New files (8)

| Path | Responsibility |
|---|---|
| `engine/core/telemetry.py` | Pipeline introspection helpers — `endpoint_source(name)`, `pipeline_phase()`, `layers_realness()`, etc. Used by `/api/telemetry/data-sources` only. |
| `tests/test_telemetry_endpoint.py` | Integration tests for `/api/telemetry/data-sources` and the source-header behavior on previously-uncovered endpoints. |
| `frontend/src/lib/apiFetch.ts` | Thin `fetch` wrapper returning `{data, source}` by reading `X-Data-Source`. |
| `frontend/src/lib/apiFetch.test.ts` | Unit tests for header parsing. |
| `frontend/src/components/MockBadge.tsx` | Single source of truth for the visual "MOCK / STUB / ? " badge. |
| `frontend/src/components/MockBadge.test.tsx` | Component tests for the 4 source states. |
| `frontend/src/components/DataSourceDebugPanel.tsx` | Collapsible top-right panel showing pipeline phase, endpoint sources, and layer realness flags. |
| `frontend/src/hooks/useTelemetry.ts` | Polls `/api/telemetry/data-sources` every 5 s. |

### New hooks (5)

| Path | Endpoint |
|---|---|
| `frontend/src/hooks/useFunnelCounts.ts` | `GET /api/funnel/counts` |
| `frontend/src/hooks/useActiveTheses.ts` | `GET /api/monitor/active-theses` |
| `frontend/src/hooks/useEdgeTiers.ts` | `GET /api/edge/tiers` |
| `frontend/src/hooks/useActivityEvents.ts` | `GET /api/activity/events?since=` |
| `frontend/src/hooks/useCandles.ts` | `GET /api/market/candles/{symbol}` |

### Modified files (12)

| Path | Change |
|---|---|
| `engine/api/rest_routes.py` | Add `X-Data-Source` headers to `/health`, `/activity/events`, `/edge/tiers`, `/rankings/{symbol}/factors`; make `/health` body truthful; register `/api/telemetry/data-sources` route. |
| `engine/api/websocket_manager.py` | Add `source` field to broadcast payloads; delete the subscribe-ack stub at lines 376-391. |
| `engine/main.py` | (No change expected — `rest_routes.router` already included.) |
| `frontend/src/stores/marketStore.ts` | Add `sources: Record<string, DataSource>` slice + `setSource`. |
| `frontend/src/types/api.ts` | Export `DataSource` union; extend `WSMessage` envelope to include `source?: 'pipeline' \| 'stub'`. |
| `frontend/src/hooks/useMarketContext.ts` | Switch to `apiFetch`; write source to store. |
| `frontend/src/hooks/useRankings.ts` | Switch to `apiFetch`; write source to store. |
| `frontend/src/hooks/useFactorBreakdown.ts` | Switch to `apiFetch`; write source to store. |
| `frontend/src/hooks/usePipelineStatus.ts` | Switch to `apiFetch`; write source to store. |
| `frontend/src/hooks/useWebSocket.ts` | Read `msg.source`; write to store under `ws/<type>` key. |
| `frontend/src/components/RegimeBanner.tsx`, `RankingsPanel.tsx`, `FunnelStrip.tsx`, `HealthStrip.tsx`, `PipelineStatusBar.tsx`, `DetailPanel.tsx`, `ChartPanel.tsx`, `ActiveMonitor.tsx`, `EdgePanel.tsx`, `CycleActivity.tsx` | Insert `<MockBadge>` in header chip; add honest empty states. |
| `frontend/src/App.tsx` | Remove `useEngine`, `syncToStore`, simulator-coupled state; replace simulator-driven `funnel` / `activityEvents` with hook calls; mount `DataSourceDebugPanel`. |

### Deleted files (1)

| Path | Reason |
|---|---|
| `frontend/src/data/engineSimulator.ts` | 501-line client-side fabricator; replaced by truthful empty states + MOCK badges. |

---

## Pre-flight check

- [ ] **Step 0.1: Confirm working tree is clean enough**

Run: `git status --short`

Expected: only the docs from prior commit `3d4b7d6` should be tracked. The existing untracked PNG screenshots and stale snapshot markdown files (`snapshot-current.md`, `dashboard-full.png`, etc.) can stay untracked — do not commit them. If anything else looks unfamiliar, stop and ask.

- [ ] **Step 0.2: Confirm pytest + vitest baselines pass**

Run: `pytest -q` from project root.
Expected: green. If existing tests are broken before we start, fix or skip them in a separate commit before beginning Task 1.

Run: `cd frontend && npm test -- --run` (one-shot vitest).
Expected: green.

---

## Task 1: `core/telemetry.py` helper module

**Files:**
- Create: `engine/core/telemetry.py`
- Test: `tests/test_telemetry_helpers.py`

This module is pure introspection — no I/O. It reads `pipeline.latest_*` and `pipeline.aggregator` to decide endpoint sources and per-layer realness.

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_telemetry_helpers.py`:

```python
"""Unit tests for core/telemetry.py — pure functions, no fixtures."""

import sys
from pathlib import Path

_engine_root = Path(__file__).resolve().parent.parent / "engine"
if str(_engine_root) not in sys.path:
    sys.path.insert(0, str(_engine_root))

from unittest.mock import MagicMock

from core.telemetry import (
    endpoint_source,
    pipeline_phase,
    layers_realness,
    snapshot,
)


def _fake_pipeline_empty():
    p = MagicMock()
    p.latest_context = None
    p.latest_long_rankings = []
    p.latest_short_rankings = []
    p.latest_theses = []
    p.aggregator = MagicMock()
    p.aggregator._buffers = {}
    return p


def _fake_pipeline_with_rankings():
    p = _fake_pipeline_empty()
    p.latest_long_rankings = [MagicMock()]
    return p


def test_endpoint_source_market_context_empty_returns_mock():
    p = _fake_pipeline_empty()
    assert endpoint_source(p, "/market/context") == "mock"


def test_endpoint_source_rankings_with_data_returns_pipeline():
    p = _fake_pipeline_with_rankings()
    assert endpoint_source(p, "/rankings/top25/long") == "pipeline"


def test_endpoint_source_unknown_path_returns_unknown():
    p = _fake_pipeline_empty()
    assert endpoint_source(p, "/nonexistent/path") == "unknown"


def test_pipeline_phase_closed_when_no_session():
    p = _fake_pipeline_empty()
    session = MagicMock()
    session.current_phase.return_value = "closed"
    assert pipeline_phase(p, session) == "closed"


def test_layers_realness_all_false_when_empty():
    p = _fake_pipeline_empty()
    flags = layers_realness(p)
    for k in ("l1_real", "l3_real", "l5_real", "l6_real", "l8_real", "l10_real"):
        assert flags[k] is False, f"{k} should be False for empty pipeline"


def test_layers_realness_l1_true_when_context_has_real_vix():
    p = _fake_pipeline_empty()
    ctx = MagicMock()
    ctx.vix_value = 23.5  # not the hardcoded 15.0
    p.latest_context = ctx
    assert layers_realness(p)["l1_real"] is True


def test_layers_realness_l1_false_when_vix_is_placeholder():
    p = _fake_pipeline_empty()
    ctx = MagicMock()
    ctx.vix_value = 15.0  # placeholder
    p.latest_context = ctx
    assert layers_realness(p)["l1_real"] is False


def test_snapshot_returns_full_dict_shape():
    p = _fake_pipeline_empty()
    session = MagicMock()
    session.current_phase.return_value = "closed"
    snap = snapshot(p, session, ws_connections=2, scheduler_running=True)
    assert "endpoints" in snap
    assert "pipeline" in snap
    assert "layers" in snap
    assert snap["pipeline"]["phase"] == "closed"
    assert snap["pipeline"]["ws_connections"] == 2
    assert snap["pipeline"]["scheduler_running"] is True
    assert isinstance(snap["timestamp"], str)
```

- [ ] **Step 1.2: Run test to verify it fails**

Run: `pytest tests/test_telemetry_helpers.py -v`

Expected: `ModuleNotFoundError: No module named 'core.telemetry'` (all tests fail with import error).

- [ ] **Step 1.3: Implement `core/telemetry.py`**

Create `engine/core/telemetry.py`:

```python
"""Pipeline introspection helpers for the truth-source telemetry endpoint.

Pure functions — no I/O, no Redis. Takes the pipeline + session singletons
as arguments so tests can swap MagicMocks in.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Map REST endpoint path → predicate that returns True if pipeline has real data.
_ENDPOINT_PREDICATES: dict[str, str] = {
    "/market/context":
        "p.latest_context is not None and getattr(p.latest_context, 'vix_value', 0) > 0",
    "/rankings/top25/long":
        "bool(p.latest_long_rankings)",
    "/rankings/top25/short":
        "bool(p.latest_short_rankings)",
    "/rankings/{symbol}/factors":
        "False",  # always mock until Phase B wires Redis factors:* cache reads
    "/thesis/{thesis_id}":
        "bool(p.latest_theses)",
    "/edge/tiers":
        "False",  # always mock until Phase B accumulates L10 stats
    "/funnel/counts":
        "bool(p.latest_long_rankings or p.latest_short_rankings)",
    "/monitor/active-theses":
        "bool(p.latest_theses)",
    "/pipeline/status":
        "False",  # set by route handler based on Redis cache hit
    "/activity/events":
        "False",  # always mock until Phase B tracks real activity
    "/market/candles/{symbol}":
        "False",  # always mock until Phase B aggregator has bars
    "/health":
        "bool(p.latest_long_rankings) or bool(p.latest_short_rankings)",
}


def endpoint_source(pipeline: Any, path: str) -> str:
    """Return "pipeline" | "mock" | "unknown" for the given REST endpoint path."""
    pred = _ENDPOINT_PREDICATES.get(path)
    if pred is None:
        return "unknown"
    try:
        return "pipeline" if eval(pred, {"p": pipeline}) else "mock"
    except Exception:
        return "mock"


def pipeline_phase(pipeline: Any, session: Any) -> str:
    """Return the current market-session phase string."""
    try:
        return session.current_phase()
    except Exception:
        return "unknown"


def layers_realness(pipeline: Any) -> dict[str, bool]:
    """Return per-layer `lN_real` flags based on what pipeline state exists."""
    ctx = getattr(pipeline, "latest_context", None)
    vix = getattr(ctx, "vix_value", 0) if ctx is not None else 0
    vix_real = ctx is not None and vix > 0 and abs(vix - 15.0) > 0.001

    aggregator = getattr(pipeline, "aggregator", None)
    buffers = getattr(aggregator, "_buffers", {}) if aggregator is not None else {}
    symbols_with_bars = sum(
        1 for buf in buffers.values()
        if getattr(buf, "_completed", {}) and any(buf._completed.values())
    )

    has_rankings = bool(getattr(pipeline, "latest_long_rankings", []))
    has_theses = bool(getattr(pipeline, "latest_theses", []))

    return {
        "l1_real":  vix_real,
        "l2_real":  False,  # Phase B: NSE scraper
        "l3_real":  symbols_with_bars >= 1,
        "l4_real":  False,  # Phase B: real sector RS
        "l5_real":  symbols_with_bars >= 1 and has_rankings,
        "l6_real":  has_rankings,
        "l7_real":  has_rankings,
        "l8_real":  has_theses,
        "l9_real":  has_theses,
        "l10_real": False,  # Phase B: accumulated outcomes
    }


def snapshot(
    pipeline: Any,
    session: Any,
    ws_connections: int = 0,
    scheduler_running: bool = False,
) -> dict[str, Any]:
    """One-shot snapshot consumed by GET /api/telemetry/data-sources."""
    ctx = getattr(pipeline, "latest_context", None)
    aggregator = getattr(pipeline, "aggregator", None)
    buffers = getattr(aggregator, "_buffers", {}) if aggregator is not None else {}
    symbols_feeding = sum(
        1 for buf in buffers.values()
        if getattr(buf, "_completed", {}) and any(buf._completed.values())
    )

    last_bar_at = None
    if buffers:
        try:
            timestamps = [
                bar["ts"]
                for buf in buffers.values()
                for bars in getattr(buf, "_completed", {}).values()
                for bar in bars
            ]
            if timestamps:
                last_bar_at = max(timestamps).isoformat() if hasattr(max(timestamps), "isoformat") else str(max(timestamps))
        except Exception:
            last_bar_at = None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            path: endpoint_source(pipeline, path)
            for path in _ENDPOINT_PREDICATES
        },
        "pipeline": {
            "phase": pipeline_phase(pipeline, session),
            "last_cycle_at": getattr(pipeline, "last_cycle_at", None),
            "last_bar_at": last_bar_at,
            "symbols_feeding": symbols_feeding,
            "ws_connections": ws_connections,
            "scheduler_running": scheduler_running,
        },
        "layers": layers_realness(pipeline),
    }
```

- [ ] **Step 1.4: Run test to verify it passes**

Run: `pytest tests/test_telemetry_helpers.py -v`

Expected: all 8 tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add engine/core/telemetry.py tests/test_telemetry_helpers.py
git commit -m "feat(backend): add core/telemetry.py pipeline introspection helpers

Pure functions used by GET /api/telemetry/data-sources to report which
REST endpoints currently return pipeline data vs mock fallback, the
current market-session phase, last bar timestamp, symbols feeding, and
per-layer realness flags (l1_real..l10_real)."
```

---

## Task 2: Add `X-Data-Source` header to `/health`, `/activity/events`, `/edge/tiers`, `/rankings/{symbol}/factors`

**Files:**
- Modify: `engine/api/rest_routes.py:569-583` (health), `~742` (edge/tiers), `~796` (factors), `~876` (activity/events)
- Test: `tests/test_telemetry_endpoint.py` (created in this task; expanded in Task 4)

- [ ] **Step 2.1: Write the failing test**

Create `tests/test_telemetry_endpoint.py`:

```python
"""Integration tests for X-Data-Source headers and the telemetry endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_sets_data_source_header(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_activity_events_sets_data_source_header(client):
    resp = await client.get("/activity/events?limit=5")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_edge_tiers_sets_data_source_header(client):
    resp = await client.get("/edge/tiers")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_symbol_factors_sets_data_source_header(client):
    resp = await client.get("/rankings/RELIANCE/factors")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")
```

- [ ] **Step 2.2: Run test to verify it fails**

Run: `pytest tests/test_telemetry_endpoint.py -v`

Expected: 4 tests FAIL because `x-data-source` header is missing (header value is `None`, fails the `in` check).

- [ ] **Step 2.3: Add headers + truthful health body**

In `engine/api/rest_routes.py`:

(a) Replace the existing `health` function (~line 569):

```python
@router.get("/health", response_model=HealthResponse)
async def health(response: Response):
    long_count = len(pipeline.latest_long_rankings)
    short_count = len(pipeline.latest_short_rankings)
    thesis_count = len(pipeline.latest_theses)
    has_real_data = (long_count + short_count + thesis_count) > 0
    response.headers["X-Data-Source"] = "pipeline" if has_real_data else "mock"

    last_bar = None
    try:
        for buf in pipeline.aggregator._buffers.values():
            for bars in getattr(buf, "_completed", {}).values():
                for bar in bars:
                    ts = bar.get("ts")
                    if ts is not None and (last_bar is None or ts > last_bar):
                        last_bar = ts
    except Exception:
        last_bar = None

    return HealthResponse(
        status="healthy",
        websocket="connected" if has_real_data else "idle",
        last_bar_processed=last_bar if last_bar else datetime.now(timezone.utc),
        top25_long_count=long_count,
        top25_short_count=short_count,
        active_theses=thesis_count,
        token_expires_in_days=365,
        db_connected=True,
        redis_connected=True,
        scheduler_jobs=12,
    )
```

(b) Add `response: Response` param + `X-Data-Source` header to `edge_tiers` (~line 742):

```python
@router.get("/edge/tiers")
async def edge_tiers(response: Response):
    response.headers["X-Data-Source"] = "mock"  # always mock pre-Phase-B
    cycle = _next_cycle()
    # ... existing body unchanged
```

(c) Add `response: Response` param + header to `symbol_factors` (~line 796):

```python
@router.get("/rankings/{symbol}/factors", response_model=SymbolFactorBreakdown)
async def symbol_factors(symbol: str, response: Response):
    if symbol not in SYMBOL_DATA:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    cached_factors = None
    try:
        cached_factors = await cache.get(f"factors:{symbol}")
    except Exception:
        cached_factors = None
    if cached_factors:
        response.headers["X-Data-Source"] = "pipeline"
        return SymbolFactorBreakdown(**cached_factors)
    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65537 + hash(symbol) % 100000)
    direction = Direction.LONG if rng() > 0.5 else Direction.SHORT
    return _build_symbol_factors(rng, symbol, direction)
```

(d) Add header to `activity_events` (~line 876):

```python
@router.get("/activity/events", response_model=ActivityEventsResponse)
async def activity_events(response: Response, since: int = Query(0), limit: int = Query(20, ge=1, le=50)):
    response.headers["X-Data-Source"] = "mock"  # always mock pre-Phase-B
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65539)
    events = _gen_events(rng, cycle, limit=limit)
    if since > 0:
        events = [e for e in events if e.cycle > since]
    return ActivityEventsResponse(events=events, total=len(events))
```

- [ ] **Step 2.4: Run test to verify it passes**

Run: `pytest tests/test_telemetry_endpoint.py -v`

Expected: all 4 tests PASS.

Also run: `pytest tests/test_factors_api.py -v` — confirm no regression.

- [ ] **Step 2.5: Commit**

```bash
git add engine/api/rest_routes.py tests/test_telemetry_endpoint.py
git commit -m "feat(backend): add X-Data-Source header to remaining REST endpoints

/health, /activity/events, /edge/tiers, /rankings/{symbol}/factors now
return X-Data-Source: pipeline|mock. /health body becomes truthful —
top25_long_count, top25_short_count, active_theses, last_bar_processed
read from real pipeline state rather than hardcoded values."
```

---

## Task 3: WebSocket source field + delete subscribe-ack stub

**Files:**
- Modify: `engine/api/websocket_manager.py` (broadcast helper, subscribe handler)
- Modify: `engine/core/pipeline.py` (each `ws_manager.broadcast(...)` call must include `source`)
- Test: `tests/test_websocket_source.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/test_websocket_source.py`:

```python
"""Tests that WebSocket broadcasts include a source field and that the
subscribe-ack stub no longer sends a fake L1_CONTEXT."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from api.websocket_manager import ConnectionManager


@pytest.mark.asyncio
async def test_broadcast_includes_source_field():
    mgr = ConnectionManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()
    mgr._connections = [(ws, set())]

    await mgr.broadcast({"type": "L1_CONTEXT", "timestamp": "t", "payload": {"regime": "Range-Bound"}})

    ws.send_json.assert_awaited_once()
    sent = ws.send_json.await_args.args[0]
    assert "source" in sent, "Broadcast payload must include source field"
    assert sent["source"] == "pipeline"


@pytest.mark.asyncio
async def test_broadcast_preserves_explicit_source():
    mgr = ConnectionManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()
    mgr._connections = [(ws, set())]

    await mgr.broadcast({"type": "L1_CONTEXT", "source": "stub", "timestamp": "t", "payload": {}})

    sent = ws.send_json.await_args.args[0]
    assert sent["source"] == "stub"


@pytest.mark.asyncio
async def test_subscribe_does_not_send_l1_context_stub():
    """The subscribe handler must NOT send a fake L1_CONTEXT payload.

    Only the SUBSCRIBED ack message should be sent (and L6_RANKINGS empty
    stub if previously kept; this test asserts no L1_CONTEXT stub).
    """
    mgr = ConnectionManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(side_effect=[
        {"action": "subscribe", "channels": ["market", "rankings"]},
        # Second call: simulate disconnect
        Exception("disconnect"),
    ])
    mgr._connections.append((ws, set()))

    # Inspect what got sent
    from api.websocket_manager import websocket_endpoint
    try:
        await websocket_endpoint(ws)
    except Exception:
        pass

    sent_types = [
        call.args[0].get("type") for call in ws.send_json.await_args_list
    ]
    assert "L1_CONTEXT" not in sent_types, "Stub L1_CONTEXT must not be sent on subscribe"
    assert "SUBSCRIBED" in sent_types, "SUBSCRIBED ack still expected"
```

- [ ] **Step 3.2: Run test to verify it fails**

Run: `pytest tests/test_websocket_source.py -v`

Expected: tests 1 and 3 FAIL (source field missing; subscribe still sends L1_CONTEXT stub).

- [ ] **Step 3.3: Patch `_broadcast_to_channel` to inject `source` default**

In `engine/api/websocket_manager.py`, replace `_broadcast_to_channel` (lines ~106-122):

```python
    async def _broadcast_to_channel(self, message: dict, channel: str) -> None:
        """Send *message* only to clients subscribed to *channel*.

        Adds ``source: "pipeline"`` to the message if no source field is present.
        If *channel* is ``"*"``, the message is sent to **all** connected clients
        (this is the legacy behaviour of ``broadcast()``).
        """
        if "source" not in message:
            message = {**message, "source": "pipeline"}
        stale: list[WebSocket] = []
        for conn, subs in self._connections:
            if channel != "*" and channel not in subs:
                continue
            try:
                await conn.send_json(message)
            except Exception:
                stale.append(conn)

        for conn in stale:
            self.disconnect(conn)
```

Then in the same file, replace the `subscribe` branch of `websocket_endpoint` (lines ~370-398) to delete the L1_CONTEXT and L6_RANKINGS stub sends:

```python
            if action == "subscribe":
                channels = data.get("channels", [])
                manager.subscribe(websocket, channels)
                # Acknowledge — no stub payloads. Real data arrives via pipeline broadcasts.
                await websocket.send_json({
                    "type": "SUBSCRIBED",
                    "timestamp": now(),
                    "payload": {"channels": list(manager.get_subscriptions(websocket))},
                })
```

- [ ] **Step 3.4: Run test to verify it passes**

Run: `pytest tests/test_websocket_source.py -v`

Expected: all 3 tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add engine/api/websocket_manager.py tests/test_websocket_source.py
git commit -m "feat(backend): WS broadcasts carry source field; delete subscribe-ack stub

ConnectionManager._broadcast_to_channel now injects source='pipeline' by
default; pipeline broadcasts inherit it transparently. Removed the
hardcoded MarketContextFrame(Trending-Up) stub previously sent on
subscribe to the 'market' channel, and the empty L6_RANKINGS stub on
subscribe to 'rankings' — both lied about real pipeline state. The
SUBSCRIBED ack message remains."
```

---

## Task 4: `GET /api/telemetry/data-sources` endpoint

**Files:**
- Modify: `engine/api/rest_routes.py` (add new route)
- Test: `tests/test_telemetry_endpoint.py` (extend with telemetry-specific tests)

- [ ] **Step 4.1: Write the failing test**

Append to `tests/test_telemetry_endpoint.py`:

```python
@pytest.mark.asyncio
async def test_telemetry_data_sources_returns_full_shape(client):
    resp = await client.get("/telemetry/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "timestamp" in data
    assert "endpoints" in data
    assert "pipeline" in data
    assert "layers" in data
    assert "phase" in data["pipeline"]
    assert "symbols_feeding" in data["pipeline"]
    assert "ws_connections" in data["pipeline"]
    # Layers must include all 10
    for k in ("l1_real", "l2_real", "l3_real", "l4_real", "l5_real",
              "l6_real", "l7_real", "l8_real", "l9_real", "l10_real"):
        assert k in data["layers"]


@pytest.mark.asyncio
async def test_telemetry_data_sources_reports_mock_when_pipeline_empty(client):
    """With no real pipeline data, every endpoint should report 'mock'."""
    resp = await client.get("/telemetry/data-sources")
    data = resp.json()
    assert data["endpoints"]["/market/context"] == "mock"
    assert data["endpoints"]["/rankings/top25/long"] == "mock"
    assert data["endpoints"]["/health"] == "mock"
```

- [ ] **Step 4.2: Run test to verify it fails**

Run: `pytest tests/test_telemetry_endpoint.py::test_telemetry_data_sources_returns_full_shape -v`

Expected: 404 (route not registered).

- [ ] **Step 4.3: Add the route**

In `engine/api/rest_routes.py`, add at the end of the file:

```python
@router.get("/telemetry/data-sources")
async def telemetry_data_sources():
    """One-shot snapshot of pipeline truth — which endpoints serve real data,
    current market-session phase, last bar timestamp, symbols feeding, and
    per-layer realness flags. Polled by the frontend DataSourceDebugPanel."""
    from api.websocket_manager import manager as ws_mgr
    from core.session.market_session import session as market_session
    from core.telemetry import snapshot

    return snapshot(
        pipeline=pipeline,
        session=market_session,
        ws_connections=len(ws_mgr._connections),
        scheduler_running=True,  # Phase B: read real APScheduler state
    )
```

- [ ] **Step 4.4: Run test to verify it passes**

Run: `pytest tests/test_telemetry_endpoint.py -v`

Expected: all 6 tests PASS (4 from Task 2 + 2 added here).

- [ ] **Step 4.5: Commit**

```bash
git add engine/api/rest_routes.py tests/test_telemetry_endpoint.py
git commit -m "feat(backend): GET /api/telemetry/data-sources snapshot endpoint

Returns endpoints/pipeline/layers snapshot used by the frontend
DataSourceDebugPanel to render per-endpoint and per-layer truth (real
pipeline output vs mock fallback)."
```

---

## Task 5: Frontend `apiFetch` wrapper

**Files:**
- Create: `frontend/src/lib/apiFetch.ts`
- Create: `frontend/src/lib/apiFetch.test.ts`

- [ ] **Step 5.1: Write the failing test**

Create `frontend/src/lib/apiFetch.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from './apiFetch';

describe('apiFetch', () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('returns data and source=pipeline when header is pipeline', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'pipeline' }),
      json: async () => ({ value: 42 }),
    } as Response);

    const { data, source } = await apiFetch<{ value: number }>('/api/test');
    expect(data).toEqual({ value: 42 });
    expect(source).toBe('pipeline');
  });

  it('returns source=mock when header is mock', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ([]),
    } as Response);
    const { source } = await apiFetch('/api/test');
    expect(source).toBe('mock');
  });

  it('defaults source to unknown when header is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({}),
      json: async () => ({}),
    } as Response);
    const { source } = await apiFetch('/api/test');
    expect(source).toBe('unknown');
  });

  it('throws on non-200 responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      headers: new Headers({}),
      json: async () => ({}),
    } as Response);
    await expect(apiFetch('/api/test')).rejects.toThrow(/503/);
  });
});
```

- [ ] **Step 5.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/lib/apiFetch.test.ts`

Expected: import error / module-not-found.

- [ ] **Step 5.3: Implement `apiFetch.ts`**

Create `frontend/src/lib/apiFetch.ts`:

```ts
// Source labels that REST (and, via Task 7, WebSocket) can declare for any payload.
// REST emits 'pipeline' | 'mock'. WebSocket emits 'pipeline' | 'stub'.
// 'unknown' covers missing-header REST responses and unlabelled WS messages.
export type DataSource = 'pipeline' | 'mock' | 'stub' | 'unknown';

export interface ApiFetchResult<T> {
  data: T;
  source: DataSource;
}

export async function apiFetch<T>(url: string, init?: RequestInit): Promise<ApiFetchResult<T>> {
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new Error(`apiFetch(${url}) → HTTP ${res.status}`);
  }
  const sourceHeader = res.headers.get('X-Data-Source') ?? res.headers.get('x-data-source');
  const source: DataSource =
    sourceHeader === 'pipeline' || sourceHeader === 'mock' || sourceHeader === 'stub'
      ? sourceHeader
      : 'unknown';
  const data = (await res.json()) as T;
  return { data, source };
}
```

- [ ] **Step 5.4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/lib/apiFetch.test.ts`

Expected: 4 tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add frontend/src/lib/apiFetch.ts frontend/src/lib/apiFetch.test.ts
git commit -m "feat(frontend): apiFetch wrapper returning {data, source} from X-Data-Source

Centralises the per-call data-source capture. Consumed by all REST
hooks (next tasks) so each panel can render a MOCK badge when its
underlying endpoint is serving mock fallback rather than real pipeline
output."
```

---

## Task 6: Add `sources` slice to `marketStore`

**Files:**
- Modify: `frontend/src/stores/marketStore.ts`
- Modify: `frontend/src/types/api.ts` (export DataSource from apiFetch, extend WSMessage envelope)
- Test: `frontend/src/stores/marketStore.test.ts`

- [ ] **Step 6.1: Write the failing test**

Check existing `frontend/src/stores/marketStore.test.ts` first (if it exists, append; if not, create):

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useMarketStore } from './marketStore';

describe('marketStore sources slice', () => {
  beforeEach(() => {
    useMarketStore.setState({ sources: {} });
  });

  it('initializes sources to empty object', () => {
    const { sources } = useMarketStore.getState();
    expect(sources).toEqual({});
  });

  it('setSource writes a single key', () => {
    useMarketStore.getState().setSource('rankings/top25/long', 'mock');
    expect(useMarketStore.getState().sources['rankings/top25/long']).toBe('mock');
  });

  it('setSource overwrites without clobbering other keys', () => {
    useMarketStore.getState().setSource('rankings/top25/long', 'mock');
    useMarketStore.getState().setSource('market/context', 'pipeline');
    useMarketStore.getState().setSource('rankings/top25/long', 'pipeline');
    expect(useMarketStore.getState().sources).toEqual({
      'rankings/top25/long': 'pipeline',
      'market/context': 'pipeline',
    });
  });
});
```

- [ ] **Step 6.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/stores/marketStore.test.ts`

Expected: TypeScript error: `Property 'sources' does not exist` / `setSource does not exist`.

- [ ] **Step 6.3: Extend the store**

In `frontend/src/stores/marketStore.ts`:

(a) Add import at top:
```ts
import type { DataSource } from '@/lib/apiFetch';
```

(b) Add to `MarketState` interface (alongside other fields):
```ts
sources: Record<string, DataSource>;
setSource: (key: string, source: DataSource) => void;
```

(c) Add to the `create` initializer (alongside other initial values + setters):
```ts
sources: {},
setSource: (key, source) =>
  set((state) => ({ sources: { ...state.sources, [key]: source } })),
```

- [ ] **Step 6.4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/stores/marketStore.test.ts`

Expected: 3 tests PASS.

- [ ] **Step 6.5: Commit**

```bash
git add frontend/src/stores/marketStore.ts frontend/src/stores/marketStore.test.ts
git commit -m "feat(frontend): add sources slice to marketStore

sources: Record<endpoint, DataSource> tracks the source label per REST
endpoint / WS message type. Components read it to decide whether to
render a MOCK badge."
```

---

## Task 7: Extend `WSMessage` type with optional `source` field

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 7.1: Modify `WSMessage` envelope**

In `frontend/src/types/api.ts`, replace the existing `WSMessage` block (lines ~283-289):

```ts
import type { DataSource } from '@/lib/apiFetch';

type WSEnvelope<T extends string, P> = {
  type: T;
  timestamp: string;
  source?: DataSource;
  payload: P;
};

export type WSMessage =
  | WSEnvelope<'L1_CONTEXT', MarketContextFrame>
  | WSEnvelope<'L6_RANKINGS', { long: RankingEntry[]; short: RankingEntry[] }>
  | WSEnvelope<'L8_THESIS', { thesis_id: string; card: ThesisCard }>
  | WSEnvelope<'L9_INVALIDATION', { thesis_id: string; reason: string }>
  | WSEnvelope<'L10_EDGE', { tier: number; promotion: string }>
  | WSEnvelope<'SUBSCRIBED', { channels: string[] }>;
```

- [ ] **Step 7.2: Verify nothing breaks**

Run: `cd frontend && npx tsc --noEmit`

Expected: zero TypeScript errors.

Run: `cd frontend && npm test -- --run`

Expected: all existing tests still pass.

- [ ] **Step 7.3: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(frontend): add optional source field to WSMessage envelope

Backend now broadcasts source='pipeline' on every L1/L6/L8/L9/L10
message (and 'stub' for placeholder payloads). Frontend uses this to
populate the marketStore.sources slice for WS-driven panels."
```

---

## Task 8: `MockBadge` component

**Files:**
- Create: `frontend/src/components/MockBadge.tsx`
- Create: `frontend/src/components/MockBadge.test.tsx`

- [ ] **Step 8.1: Write the failing test**

Create `frontend/src/components/MockBadge.test.tsx`:

```tsx
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MockBadge } from './MockBadge';

describe('MockBadge', () => {
  afterEach(() => { cleanup(); });

  it('renders nothing for pipeline source', () => {
    const { container } = render(<MockBadge source="pipeline" />);
    expect(container.textContent).toBe('');
  });

  it('renders MOCK label for mock source', () => {
    render(<MockBadge source="mock" />);
    expect(screen.getByText('MOCK')).toBeDefined();
  });

  it('renders STUB label for stub source', () => {
    render(<MockBadge source="stub" />);
    expect(screen.getByText('STUB')).toBeDefined();
  });

  it('renders ? label for unknown source', () => {
    render(<MockBadge source="unknown" />);
    expect(screen.getByText('?')).toBeDefined();
  });

  it('renders nothing when source is undefined', () => {
    const { container } = render(<MockBadge source={undefined} />);
    expect(container.textContent).toBe('');
  });
});
```

- [ ] **Step 8.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/components/MockBadge.test.tsx`

Expected: module-not-found.

- [ ] **Step 8.3: Implement `MockBadge.tsx`**

Create `frontend/src/components/MockBadge.tsx`:

```tsx
import type { DataSource } from '@/lib/apiFetch';

interface MockBadgeProps {
  source: DataSource | undefined;
  className?: string;
}

const LABEL: Record<Exclude<DataSource, 'pipeline'>, string> = {
  mock: 'MOCK',
  stub: 'STUB',
  unknown: '?',
};

const TOOLTIP: Record<Exclude<DataSource, 'pipeline'>, string> = {
  mock: 'Backend returned seeded mock data — pipeline has no live data for this endpoint.',
  stub: 'WebSocket pushed a placeholder payload rather than real pipeline output.',
  unknown: 'Endpoint did not report a data source.',
};

export function MockBadge({ source, className }: MockBadgeProps) {
  if (source === undefined || source === 'pipeline') return null;
  return (
    <span
      title={TOOLTIP[source]}
      className={
        'ml-1.5 inline-flex h-4 items-center rounded px-1 font-mono text-[9px] font-bold uppercase tracking-wider ' +
        (source === 'unknown'
          ? 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]'
          : 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]') +
        (className ? ` ${className}` : '')
      }
    >
      {LABEL[source]}
    </span>
  );
}
```

- [ ] **Step 8.4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/components/MockBadge.test.tsx`

Expected: 5 tests PASS.

- [ ] **Step 8.5: Commit**

```bash
git add frontend/src/components/MockBadge.tsx frontend/src/components/MockBadge.test.tsx
git commit -m "feat(frontend): MockBadge component (MOCK | STUB | ? | hidden)

Single visual treatment for the per-panel data-source badge. Hidden
when source is 'pipeline' or undefined; yellow pill labelled MOCK/STUB
or gray ? otherwise."
```

---

## Task 9: Refactor `useMarketContext` to capture source

**Files:**
- Modify: `frontend/src/hooks/useMarketContext.ts`

- [ ] **Step 9.1: Replace the hook**

In `frontend/src/hooks/useMarketContext.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { MarketContextFrame } from '@/types/api';

export function useMarketContext() {
  const setSource = useMarketStore((s) => s.setSource);

  const query = useQuery({
    queryKey: ['marketContext'],
    queryFn: async () => apiFetch<MarketContextFrame>('/api/market/context'),
    refetchInterval: 300000,
  });

  useEffect(() => {
    if (query.data) setSource('market/context', query.data.source);
  }, [query.data, setSource]);

  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
```

- [ ] **Step 9.2: Update existing tests that import `useMarketContext`**

Check: `cd frontend && npm test -- --run src/hooks/useMarketContext.test.tsx`

If the existing test fails because it expects the old return shape (a TanStack `UseQueryResult`), update its assertions:

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMarketContext } from './useMarketContext';
import React from 'react';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useMarketContext', () => {
  it('captures source from response header', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ({ regime: 'Range-Bound', vix_value: 15 }),
    } as Response);

    const { result } = renderHook(() => useMarketContext(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.source).toBe('mock');
  });
});
```

- [ ] **Step 9.3: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/hooks/useMarketContext.test.tsx`

Expected: PASS.

- [ ] **Step 9.4: Commit**

```bash
git add frontend/src/hooks/useMarketContext.ts frontend/src/hooks/useMarketContext.test.tsx
git commit -m "refactor(frontend): useMarketContext uses apiFetch, writes source to store

Returns {data, source, isLoading, isError, error} instead of raw
UseQueryResult so consumers can render MockBadge inline."
```

---

## Task 10: Refactor `useRankings` to capture source

**Files:**
- Modify: `frontend/src/hooks/useRankings.ts`
- Modify: `frontend/src/hooks/useRankings.test.tsx`

- [ ] **Step 10.1: Replace the hook**

```ts
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { RankingEntry } from '@/types/api';

export function useRankings(direction: 'long' | 'short') {
  const setSource = useMarketStore((s) => s.setSource);

  const query = useQuery({
    queryKey: ['rankings', direction],
    queryFn: async () => apiFetch<RankingEntry[]>(`/api/rankings/top25/${direction}`),
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (query.data) setSource(`rankings/top25/${direction}`, query.data.source);
  }, [query.data, setSource, direction]);

  return {
    data: query.data?.data ?? [],
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
```

- [ ] **Step 10.2: Update the existing test to match new return shape**

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useRankings } from './useRankings';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('fetches from /api/rankings/top25/long and reports source', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => [{ symbol: 'RELIANCE', score: 85, instrument_key: 'NSE_EQ|RELIANCE' }],
    } as Response);

    const { result } = renderHook(() => useRankings('long'), { wrapper });
    await waitFor(() => expect(result.current.data.length).toBe(1));
    expect(result.current.source).toBe('mock');
  });
});
```

- [ ] **Step 10.3: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/hooks/useRankings.test.tsx`

Expected: PASS.

- [ ] **Step 10.4: Update `Top25Table` / `RankingsPanel` consumers**

Run: `cd frontend && grep -rn "useRankings" src/`

Wherever the old `query.data` / `query.isLoading` pattern is used, update to the new shape — `.data` (default `[]`), `.source`, `.isLoading`. Component changes are covered explicitly in Task 14; if this step uncovers a type error blocking compilation, fix the minimal call site to keep `npm run build` green; defer badge rendering to Task 14.

Run: `cd frontend && npx tsc --noEmit`

Expected: zero TypeScript errors.

- [ ] **Step 10.5: Commit**

```bash
git add frontend/src/hooks/useRankings.ts frontend/src/hooks/useRankings.test.tsx
git commit -m "refactor(frontend): useRankings uses apiFetch, writes source to store"
```

---

## Task 11: Refactor `useFactorBreakdown` and `usePipelineStatus`

**Files:**
- Modify: `frontend/src/hooks/useFactorBreakdown.ts`
- Modify: `frontend/src/hooks/usePipelineStatus.ts`

- [ ] **Step 11.1: Read current implementations**

Run: `cat frontend/src/hooks/useFactorBreakdown.ts frontend/src/hooks/usePipelineStatus.ts`

These follow the same pattern as `useRankings` / `useMarketContext` — a `useQuery` with raw `fetch`. Refactor each to:
- import `apiFetch` and `useMarketStore`
- use `apiFetch<T>(url)` in `queryFn`
- add a `useEffect` that writes `query.data?.source` to the store under the appropriate key (`'rankings/factors'`, `'pipeline/status'`)
- return `{ data, source, isLoading, isError }`

- [ ] **Step 11.2: Apply the refactor**

Reference `useRankings` (Task 10) for the exact pattern. The key per endpoint:
- `useFactorBreakdown(symbol)` → store key `rankings/factors`
- `usePipelineStatus()` → store key `pipeline/status`

- [ ] **Step 11.3: Update co-located test files**

Each hook with a test file (`*.test.ts` / `*.test.tsx`) — adjust to the new return shape just like Task 10.3.

- [ ] **Step 11.4: Run all frontend tests**

Run: `cd frontend && npm test -- --run`

Expected: all green.

- [ ] **Step 11.5: Commit**

```bash
git add frontend/src/hooks/
git commit -m "refactor(frontend): useFactorBreakdown + usePipelineStatus use apiFetch"
```

---

## Task 12: Five new REST hooks (funnel, active-theses, edge-tiers, activity, candles)

**Files:**
- Create: `frontend/src/hooks/useFunnelCounts.ts`
- Create: `frontend/src/hooks/useActiveTheses.ts`
- Create: `frontend/src/hooks/useEdgeTiers.ts`
- Create: `frontend/src/hooks/useActivityEvents.ts`
- Create: `frontend/src/hooks/useCandles.ts`
- Create: `frontend/src/hooks/useNewHooks.test.tsx` (shared file for 5 hook tests)

- [ ] **Step 12.1: Write the failing test**

Create `frontend/src/hooks/useNewHooks.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useFunnelCounts } from './useFunnelCounts';
import { useActiveTheses } from './useActiveTheses';
import { useEdgeTiers } from './useEdgeTiers';
import { useActivityEvents } from './useActivityEvents';
import { useCandles } from './useCandles';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

function mockOnce(url: string, body: unknown, source = 'mock') {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
    ok: true,
    headers: new Headers({ 'X-Data-Source': source }),
    json: async () => body,
  } as Response);
}

describe('new REST hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('useFunnelCounts hits /api/funnel/counts', async () => {
    mockOnce('/api/funnel/counts', { L1: { in: 1, out: 1 } });
    const { result } = renderHook(() => useFunnelCounts(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/funnel/counts');
  });

  it('useActiveTheses hits /api/monitor/active-theses', async () => {
    mockOnce('/api/monitor/active-theses', { theses: [] });
    const { result } = renderHook(() => useActiveTheses(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/monitor/active-theses');
  });

  it('useEdgeTiers hits /api/edge/tiers', async () => {
    mockOnce('/api/edge/tiers', { tiers: [], promotions: [] });
    const { result } = renderHook(() => useEdgeTiers(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/edge/tiers');
  });

  it('useActivityEvents hits /api/activity/events with since=0', async () => {
    mockOnce('/api/activity/events?since=0&limit=20', { events: [], total: 0 });
    const { result } = renderHook(() => useActivityEvents(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/activity/events?since=0&limit=20');
  });

  it('useCandles(RELIANCE) hits /api/market/candles/RELIANCE', async () => {
    mockOnce('/api/market/candles/RELIANCE', { symbol: 'RELIANCE', candles: [] });
    const { result } = renderHook(() => useCandles('RELIANCE'), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/market/candles/RELIANCE');
  });
});
```

- [ ] **Step 12.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/hooks/useNewHooks.test.tsx`

Expected: 5 import errors.

- [ ] **Step 12.3: Implement the five hooks (same template each)**

Template (replace `<HookName>`, `<endpoint>`, `<storeKey>`, `<RefetchMs>`, `<Type>`):

```ts
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';

export function <HookName>(...args) {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: [/* ... */],
    queryFn: async () => apiFetch</* Type */>(`<endpoint>`),
    refetchInterval: <RefetchMs>,
  });
  useEffect(() => {
    if (query.data) setSource('<storeKey>', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
```

Concrete instances:

**`useFunnelCounts.ts`**
```ts
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';

type FunnelCountsResponse = Record<string, { in_count: number; out_count: number; layer: string }>;

export function useFunnelCounts() {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['funnelCounts'],
    queryFn: async () => apiFetch<FunnelCountsResponse>('/api/funnel/counts'),
    refetchInterval: 30000,
  });
  useEffect(() => {
    if (query.data) setSource('funnel/counts', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
```

**`useActiveTheses.ts`** — endpoint `/api/monitor/active-theses`, store key `monitor/active-theses`, refetch 30 s, type `{ theses: ActiveThesisEntry[] }`.

**`useEdgeTiers.ts`** — endpoint `/api/edge/tiers`, store key `edge/tiers`, refetch 60 s, type `{ tiers: any[]; promotions: number[] }`.

**`useActivityEvents.ts`** — endpoint `/api/activity/events?since=0&limit=20`, store key `activity/events`, refetch 15 s, type `{ events: ActivityEvent[]; total: number }`.

**`useCandles.ts`** — takes `symbol: string`, endpoint `/api/market/candles/${symbol}`, store key `market/candles`, refetch 60 s, enabled only when `symbol`, type `CandleResponse`.

```ts
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { CandleResponse } from '@/types/api';

export function useCandles(symbol: string) {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['candles', symbol],
    queryFn: async () => apiFetch<CandleResponse>(`/api/market/candles/${symbol}`),
    refetchInterval: 60000,
    enabled: !!symbol,
  });
  useEffect(() => {
    if (query.data) setSource('market/candles', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
```

- [ ] **Step 12.4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/hooks/useNewHooks.test.tsx`

Expected: 5 tests PASS.

- [ ] **Step 12.5: Commit**

```bash
git add frontend/src/hooks/useFunnelCounts.ts frontend/src/hooks/useActiveTheses.ts frontend/src/hooks/useEdgeTiers.ts frontend/src/hooks/useActivityEvents.ts frontend/src/hooks/useCandles.ts frontend/src/hooks/useNewHooks.test.tsx
git commit -m "feat(frontend): five REST hooks for funnel/theses/edge/activity/candles

All use apiFetch and write source to marketStore. Together with hooks
refactored in Tasks 9-11, every panel-driving endpoint is now
source-aware. Frontend simulator becomes redundant (deleted in Task 18)."
```

---

## Task 13: `useTelemetry` hook + `DataSourceDebugPanel`

**Files:**
- Create: `frontend/src/hooks/useTelemetry.ts`
- Create: `frontend/src/components/DataSourceDebugPanel.tsx`
- Create: `frontend/src/components/DataSourceDebugPanel.test.tsx`

- [ ] **Step 13.1: Write the failing test**

Create `frontend/src/components/DataSourceDebugPanel.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DataSourceDebugPanel } from './DataSourceDebugPanel';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('DataSourceDebugPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({}),
      json: async () => ({
        timestamp: '2026-05-19T17:30:00Z',
        endpoints: {
          '/market/context': 'mock',
          '/rankings/top25/long': 'mock',
        },
        pipeline: {
          phase: 'closed',
          last_cycle_at: null,
          last_bar_at: null,
          symbols_feeding: 0,
          ws_connections: 1,
          scheduler_running: true,
        },
        layers: {
          l1_real: false,
          l2_real: false,
          l3_real: false,
          l4_real: false,
          l5_real: false,
          l6_real: false,
          l7_real: false,
          l8_real: false,
          l9_real: false,
          l10_real: false,
        },
      }),
    } as Response);
  });
  afterEach(() => { cleanup(); });

  it('renders pipeline phase and symbols_feeding when expanded', async () => {
    render(<DataSourceDebugPanel defaultOpen={true} />, { wrapper });
    expect(await screen.findByText(/closed/i)).toBeDefined();
    expect(screen.getByText(/symbols_feeding/i)).toBeDefined();
  });

  it('renders collapsed by default', () => {
    render(<DataSourceDebugPanel />, { wrapper });
    // Toggle button present
    expect(screen.getByRole('button', { name: /truth/i })).toBeDefined();
  });
});
```

- [ ] **Step 13.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/components/DataSourceDebugPanel.test.tsx`

Expected: module-not-found.

- [ ] **Step 13.3: Implement `useTelemetry`**

Create `frontend/src/hooks/useTelemetry.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/apiFetch';

export interface TelemetrySnapshot {
  timestamp: string;
  endpoints: Record<string, 'pipeline' | 'mock' | 'unknown'>;
  pipeline: {
    phase: string;
    last_cycle_at: string | null;
    last_bar_at: string | null;
    symbols_feeding: number;
    ws_connections: number;
    scheduler_running: boolean;
  };
  layers: Record<string, boolean>;
}

export function useTelemetry() {
  return useQuery({
    queryKey: ['telemetry'],
    queryFn: async () => (await apiFetch<TelemetrySnapshot>('/api/telemetry/data-sources')).data,
    refetchInterval: 5000,
  });
}
```

- [ ] **Step 13.4: Implement `DataSourceDebugPanel`**

Create `frontend/src/components/DataSourceDebugPanel.tsx`:

```tsx
import { useState } from 'react';
import { useTelemetry } from '@/hooks/useTelemetry';

interface Props {
  defaultOpen?: boolean;
}

export function DataSourceDebugPanel({ defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const { data } = useTelemetry();

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed right-3 top-3 z-50 rounded bg-[var(--bg-surface-raised)] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        Truth
      </button>
    );
  }

  return (
    <div className="fixed right-3 top-3 z-50 w-72 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-[11px] shadow-xl">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-bold uppercase tracking-wider">Truth</span>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
        >
          ×
        </button>
      </div>
      {!data ? (
        <div className="text-[var(--text-tertiary)]">Loading telemetry…</div>
      ) : (
        <>
          <div className="mb-3">
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Pipeline</div>
            <div>phase: <span className="font-mono">{data.pipeline.phase}</span></div>
            <div>last_cycle_at: <span className="font-mono">{data.pipeline.last_cycle_at ?? '—'}</span></div>
            <div>last_bar_at: <span className="font-mono">{data.pipeline.last_bar_at ?? '—'}</span></div>
            <div>symbols_feeding: <span className="font-mono">{data.pipeline.symbols_feeding}</span></div>
            <div>ws_connections: <span className="font-mono">{data.pipeline.ws_connections}</span></div>
          </div>
          <div className="mb-3">
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Endpoints</div>
            <ul className="space-y-0.5">
              {Object.entries(data.endpoints).map(([path, src]) => (
                <li key={path} className="flex items-center justify-between">
                  <span className="font-mono text-[10px]">{path}</span>
                  <span className={src === 'pipeline' ? 'text-[var(--trade-long)]' : 'text-[var(--trade-neutral)]'}>
                    {src}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Layers</div>
            <div className="grid grid-cols-5 gap-1">
              {Object.entries(data.layers).map(([k, real]) => (
                <span
                  key={k}
                  className={`rounded px-1 py-0.5 text-center font-mono text-[9px] ${
                    real ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]' : 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]'
                  }`}
                >
                  {k.replace('_real', '').toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 13.5: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/components/DataSourceDebugPanel.test.tsx`

Expected: 2 tests PASS.

- [ ] **Step 13.6: Commit**

```bash
git add frontend/src/hooks/useTelemetry.ts frontend/src/components/DataSourceDebugPanel.tsx frontend/src/components/DataSourceDebugPanel.test.tsx
git commit -m "feat(frontend): useTelemetry hook + DataSourceDebugPanel

Collapsible top-right panel polling /api/telemetry/data-sources every
5s. Shows pipeline phase, last_cycle_at, symbols_feeding,
ws_connections, per-endpoint source dots, and per-layer realness flags."
```

---

## Task 14: Wire `MockBadge` into each panel + honest empty states

**Files:**
- Modify: `frontend/src/components/RegimeBanner.tsx`
- Modify: `frontend/src/components/RankingsPanel.tsx`
- Modify: `frontend/src/components/FunnelStrip.tsx`
- Modify: `frontend/src/components/HealthStrip.tsx`
- Modify: `frontend/src/components/PipelineStatusBar.tsx`
- Modify: `frontend/src/components/DetailPanel.tsx`
- Modify: `frontend/src/components/ChartPanel.tsx`
- Modify: `frontend/src/components/ActiveMonitor.tsx`
- Modify: `frontend/src/components/EdgePanel.tsx`
- Modify: `frontend/src/components/CycleActivity.tsx`

Each panel gets two changes:
1. Read its source from `useMarketStore.sources[key]` and render `<MockBadge source={src} />` in the header.
2. Render an honest empty-state message when its data is empty/null instead of the previous loading skeleton (which currently never resolved because the simulator always filled state).

- [ ] **Step 14.1: `RegimeBanner` — example template**

Replace `RegimeBanner.tsx` opening lines 4-13:

```tsx
import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { MockBadge } from './MockBadge';

export function RegimeBanner() {
  const ctx = useMarketStore((s) => s.context);
  const source = useMarketStore(
    (s) => s.sources['ws/l1_context'] ?? s.sources['market/context'],
  );

  if (!ctx) {
    return (
      <div className="flex h-12 items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 text-[12px] text-[var(--text-tertiary)]">
        <span>Waiting for L1 context…</span>
        <MockBadge source={source} />
      </div>
    );
  }
  // ... existing body, but inject <MockBadge source={source} /> at the end of the header row
```

Insert `<MockBadge source={source} />` near the "Session" column at the end of the existing JSX (just before the closing `</div>` at line 173).

- [ ] **Step 14.2: Apply the same pattern to remaining panels**

For each component listed above, do:
1. `import { MockBadge } from './MockBadge';`
2. Read source from store: `const source = useMarketStore((s) => s.sources['<key>']);`
3. Replace any placeholder/loading "always fills" state with an honest empty message + `<MockBadge source={source} />`.
4. Render `<MockBadge source={source} />` inline in the panel header.

Source key per panel:
| Component | Store key |
|---|---|
| `RegimeBanner` | `ws/l1_context` ?? `market/context` |
| `RankingsPanel` | `rankings/top25/long` (long list) / `rankings/top25/short` (short list) |
| `FunnelStrip` | `funnel/counts` |
| `HealthStrip` | `pipeline/status` |
| `PipelineStatusBar` | `pipeline/status` |
| `DetailPanel` | `rankings/factors` |
| `ChartPanel` | `market/candles` |
| `ActiveMonitor` | `monitor/active-theses` ?? `ws/l8_thesis` |
| `EdgePanel` | `edge/tiers` ?? `ws/l10_edge` |
| `CycleActivity` | `activity/events` |

Honest empty-state copy (from spec §3.3.5):
| Component | Empty copy |
|---|---|
| `RegimeBanner` | "Waiting for L1 context…" |
| `RankingsPanel` | "No rankings yet — pipeline idle" |
| `FunnelStrip` | "Pipeline has not run a cycle" |
| `HealthStrip` | "No cycles since startup" |
| `PipelineStatusBar` | (gray all 10 layers; no flashing) |
| `DetailPanel` | "Select a symbol — factor breakdown will appear when L3+L5 produce real signals" |
| `ChartPanel` | "Candle data unavailable — pipeline aggregator has no bars for {symbol}" |
| `ActiveMonitor` | "No active theses" |
| `EdgePanel` | "No edge data — L10 needs at least 30 outcomes per tier" |
| `CycleActivity` | "No cycle activity yet" |

- [ ] **Step 14.3: Run all frontend tests + build**

Run: `cd frontend && npm test -- --run`

Expected: all existing tests still PASS (including `RegimeBanner.test.tsx` — the empty-state copy changed; update its assertion if needed: `expect(screen.getByText(/waiting for L1/i)).toBeDefined();`).

Run: `cd frontend && npm run build`

Expected: build succeeds, no TS errors.

- [ ] **Step 14.4: Commit**

```bash
git add frontend/src/components/
git commit -m "feat(frontend): wire MockBadge + honest empty states into all panels

Each panel now reads its X-Data-Source / WS source field from the
marketStore.sources slice and renders <MockBadge> in its header.
Previous loading-skeleton placeholders (which never resolved because
the simulator filled state) are replaced with honest empty-state copy."
```

---

## Task 15: Update `useWebSocket` to capture `source` field

**Files:**
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/hooks/useWebSocket.test.ts`

- [ ] **Step 15.1: Write the failing test**

Append to `frontend/src/hooks/useWebSocket.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Note: useWebSocket uses real WebSocket; mock it.

describe('useWebSocket source capture', () => {
  let onMessage: ((event: MessageEvent) => void) | null = null;
  const wsMock = {
    send: vi.fn(),
    close: vi.fn(),
    onopen: null as any,
    onclose: null as any,
    onerror: null as any,
    set onmessage(fn: any) { onMessage = fn; },
  };
  beforeEach(() => {
    onMessage = null;
    vi.stubGlobal('WebSocket', vi.fn(() => wsMock));
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('writes source to store when WS message carries source field', async () => {
    const { renderHook } = await import('@testing-library/react');
    const { useMarketStore } = await import('@/stores/marketStore');
    const { useWebSocket } = await import('./useWebSocket');

    useMarketStore.setState({ sources: {} });
    renderHook(() => useWebSocket());

    onMessage?.({
      data: JSON.stringify({
        type: 'L1_CONTEXT',
        timestamp: 't',
        source: 'pipeline',
        payload: { regime: 'Range-Bound', regime_confidence: 0.5 },
      }),
    } as MessageEvent);

    expect(useMarketStore.getState().sources['ws/l1_context']).toBe('pipeline');
  });
});
```

- [ ] **Step 15.2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/hooks/useWebSocket.test.ts`

Expected: FAIL (`useWebSocket` doesn't yet write to sources).

- [ ] **Step 15.3: Update `useWebSocket.ts`**

Replace `frontend/src/hooks/useWebSocket.ts`:

```ts
import { useEffect, useRef } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import type { WSMessage } from '@/types/api';

const WS_URL = '/ws/v1/stream';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const setWsConnected = useMarketStore((s) => s.setWsConnected);
  const setContext = useMarketStore((s) => s.setContext);
  const setRankings = useMarketStore((s) => s.setRankings);
  const addOrUpdateThesis = useMarketStore((s) => s.addOrUpdateThesis);
  const invalidateThesis = useMarketStore((s) => s.invalidateThesis);
  const updateEdgeTier = useMarketStore((s) => s.updateEdgeTier);
  const setWSTimestamp = useMarketStore((s) => s.setWSTimestamp);
  const setSource = useMarketStore((s) => s.setSource);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      socket.send(JSON.stringify({ action: 'subscribe', channels: ['market', 'rankings', 'theses', 'edge'] }));
    };

    socket.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      setWSTimestamp(msg.type, msg.timestamp);
      const wsSource = msg.source ?? 'unknown';
      const key = `ws/${msg.type.toLowerCase()}`;
      setSource(key, wsSource);
      switch (msg.type) {
        case 'L1_CONTEXT':
          setContext(msg.payload);
          break;
        case 'L6_RANKINGS':
          setRankings(msg.payload.long, msg.payload.short);
          break;
        case 'L8_THESIS':
          addOrUpdateThesis(msg.payload.card);
          break;
        case 'L9_INVALIDATION':
          invalidateThesis(msg.payload.thesis_id, msg.payload.reason);
          break;
        case 'L10_EDGE':
          updateEdgeTier(msg.payload.tier, msg.payload.promotion);
          break;
      }
    };

    socket.onclose = () => setWsConnected(false);
    socket.onerror = () => setWsConnected(false);

    return () => { socket.close(); };
  }, [setWsConnected, setContext, setRankings, addOrUpdateThesis, invalidateThesis, updateEdgeTier, setWSTimestamp, setSource]);
}
```

- [ ] **Step 15.4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/hooks/useWebSocket.test.ts`

Expected: PASS.

- [ ] **Step 15.5: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts frontend/src/hooks/useWebSocket.test.ts
git commit -m "feat(frontend): useWebSocket captures msg.source into marketStore

Each WS payload now updates marketStore.sources['ws/<type>'] with the
backend-supplied source ('pipeline' | 'stub' | 'unknown'). RegimeBanner
and other WS-driven panels can render MockBadge based on which
push-channel actually delivered their state."
```

---

## Task 16: Refactor `App.tsx` — delete `useEngine`, wire new hooks, mount `DataSourceDebugPanel`

**Files:**
- Modify: `frontend/src/App.tsx`

This is the largest single-file change. `App.tsx` currently has two distinct simulator paths (the `useEngine` hook and the `useAlertFeed`/`useCycleActivity` calls). Both go.

- [ ] **Step 16.1: Replace `App.tsx` end to end**

Replace the entire file with:

```tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/stores/marketStore';
import { useMarketContext } from '@/hooks/useMarketContext';
import { useRankings } from '@/hooks/useRankings';
import { useFunnelCounts } from '@/hooks/useFunnelCounts';
import { useActiveTheses } from '@/hooks/useActiveTheses';
import { useEdgeTiers } from '@/hooks/useEdgeTiers';
import { useActivityEvents } from '@/hooks/useActivityEvents';
import { usePipelineStatus } from '@/hooks/usePipelineStatus';
import { Header } from '@/components/Header';
import { PipelineStatusBar } from '@/components/PipelineStatusBar';
import { FunnelStrip } from '@/components/FunnelStrip';
import { RegimeBanner } from '@/components/RegimeBanner';
import { RankingsPanel } from '@/components/RankingsPanel';
import { DetailPanel } from '@/components/DetailPanel';
import { LayerJourney } from '@/components/LayerJourney';
import { LayerInspector } from '@/components/LayerInspector';
import { CycleActivity } from '@/components/CycleActivity';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { AlertToast } from '@/components/AlertToast';
import { HealthStrip } from '@/components/HealthStrip';
import { DataSourceDebugPanel } from '@/components/DataSourceDebugPanel';
import type { RankingEntry } from '@/types/api';

export default function App() {
  useWebSocket();
  useMarketContext();
  useRankings('long');
  useRankings('short');
  const { data: pipelineStatus } = usePipelineStatus();
  const { data: funnel } = useFunnelCounts();
  useActiveTheses();
  useEdgeTiers();
  const { data: activityEvents } = useActivityEvents();

  const longRankings = useMarketStore((s) => s.longRankings);
  const shortRankings = useMarketStore((s) => s.shortRankings);

  const [selected, setSelected] = useState<RankingEntry | null>(null);
  const [viewMode, setViewMode] = useState<'journey' | 'cards'>('journey');
  const [learnMode, setLearnMode] = useState(false);
  const [inspectedLayer, setInspectedLayer] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    mobile: typeof window !== 'undefined' ? window.innerWidth < 768 : false,
  });

  useEffect(() => {
    if (!selected && longRankings.length > 0) {
      setSelected(longRankings[0]);
    }
  }, [longRankings, selected]);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      setViewport({ width: w, mobile: w < 768 });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const handleSelectSymbol = useCallback(
    (sym: string) => {
      const found = [...longRankings, ...shortRankings].find((s) => s.symbol === sym);
      if (found) setSelected(found);
    },
    [longRankings, shortRankings],
  );

  const onCloseLayer = useCallback(() => setInspectedLayer(null), []);
  const onSwitchLayer = useCallback((k: string) => setInspectedLayer(k), []);

  const isMobile = viewport.mobile;
  const cycle = pipelineStatus?.cycle_number ?? 0;
  const layers = pipelineStatus
    ? Object.entries(pipelineStatus.layers).map(([key, v]) => ({
        key,
        label: key.split('_')[0].toUpperCase(),
        name: key,
        status: v.status,
        duration_ms: v.duration_ms,
        last_run: v.last_run ? Date.parse(v.last_run) : 0,
      }))
    : [];

  return (
    <div className="flex h-[100dvh] flex-col bg-[var(--bg-base)] text-[var(--text-primary)]">
      <Header
        progress={0}
        paused={paused}
        cycle={cycle}
        onPauseToggle={() => setPaused(!paused)}
        learnMode={learnMode}
        onLearnToggle={(v: boolean) => setLearnMode(v)}
      />

      {pipelineStatus ? (
        <FunnelStrip
          layers={layers}
          activeLayer={-1}
          funnel={funnel ?? {}}
          onInspect={(k: string) => setInspectedLayer((prev) => (prev === k ? null : k))}
          inspectKey={inspectedLayer}
          learnMode={learnMode}
        />
      ) : (
        <PipelineStatusBar activeLayer={-1} />
      )}

      <RegimeBanner />

      {isMobile ? (
        <MobileLayout
          longRankings={longRankings}
          shortRankings={shortRankings}
          selected={selected}
          setSelected={setSelected}
          viewMode={viewMode}
          setViewMode={setViewMode}
          learnMode={learnMode}
          inspectedLayer={inspectedLayer}
          onCloseLayer={onCloseLayer}
          onSwitchLayer={onSwitchLayer}
          activityEvents={activityEvents?.events ?? []}
          handleSelectSymbol={handleSelectSymbol}
        />
      ) : (
        <div className="flex flex-1 overflow-hidden p-2.5" style={{ gap: 10 }}>
          <div className="flex w-[360px] shrink-0 flex-col gap-2">
            <RankingsPanel
              onSelectSymbol={handleSelectSymbol}
              entries={[...longRankings, ...shortRankings]}
              flashedSymbols={new Map()}
            />
          </div>

          <DetailColumn
            selected={selected}
            longRankings={longRankings}
            viewMode={viewMode}
            setViewMode={setViewMode}
            learnMode={learnMode}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
          />

          <div className="flex w-[280px] shrink-0 flex-col gap-2">
            <CycleActivity
              events={activityEvents?.events ?? []}
              onSelect={handleSelectSymbol}
              selectedSymbol={selected?.symbol ?? null}
            />
            <ActiveMonitor />
            <EdgePanel />
          </div>
        </div>
      )}

      <HealthStrip
        pipeline={layers}
        cycle={cycle}
        paused={paused}
        lastCycleAt={pipelineStatus?.last_cycle_at ? Date.parse(pipelineStatus.last_cycle_at) : 0}
      />
      <AlertToast />
      <DataSourceDebugPanel />
    </div>
  );
}

function DetailColumn({
  selected, longRankings, viewMode, setViewMode, learnMode,
  inspectedLayer, onCloseLayer, onSwitchLayer, setSelected,
}: {
  selected: RankingEntry | null;
  longRankings: RankingEntry[];
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  setSelected: (s: RankingEntry | null) => void;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {!inspectedLayer && (
        <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-3 py-1.5">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-tertiary)]">
            Inspector
          </span>
          {selected && (
            <span className="text-[11px] font-bold text-[var(--text-primary)]">
              {selected.symbol}
            </span>
          )}
          <span className="flex-1" />
          <span className="hidden text-[9px] text-[var(--text-tertiary)] sm:inline">
            click any L<i>n</i> tile above
          </span>
          <div className="inline-flex gap-0.5 rounded bg-[var(--bg-base)] p-0.5">
            {([
              { v: 'journey' as const, label: 'Journey' },
              { v: 'cards' as const, label: 'Cards' },
            ]).map((opt) => (
              <button
                key={opt.v}
                onClick={() => setViewMode(opt.v)}
                className="touch-target rounded px-3 py-1.5 text-[10px] font-bold tracking-wide transition-colors"
                style={{
                  color: viewMode === opt.v ? 'var(--accent)' : 'var(--text-tertiary)',
                  background: viewMode === opt.v ? 'var(--accent-dim)' : 'transparent',
                }}
              >
                {opt.label.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="flex flex-1 flex-col overflow-hidden">
        {inspectedLayer ? (
          <LayerInspector
            layerKey={inspectedLayer}
            snapshot={{ universe: { longs: longRankings, shorts: [], cycle: 0 } as any, ctx: null as any, pipeline: [] }}
            ctx={null as any}
            onClose={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            onSelectStock={(stock: any) => {
              setSelected(stock);
              onCloseLayer();
            }}
          />
        ) : viewMode === 'cards' ? (
          <DetailPanel symbol={selected?.symbol ?? ''} stock={selected as any} ctx={null as any} />
        ) : selected ? (
          <LayerJourney entry={selected as any} ctx={null as any} learnMode={learnMode} activeLayer={-1} />
        ) : (
          <DetailPanel symbol="" />
        )}
      </div>
    </div>
  );
}

function MobileLayout({
  longRankings, shortRankings, selected, setSelected,
  viewMode, setViewMode, learnMode,
  inspectedLayer, onCloseLayer, onSwitchLayer,
  activityEvents, handleSelectSymbol,
}: {
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selected: RankingEntry | null;
  setSelected: (s: RankingEntry | null) => void;
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  activityEvents: any[];
  handleSelectSymbol: (sym: string) => void;
}) {
  const [tab, setTab] = useState<'rankings' | 'detail' | 'theses' | 'activity'>('rankings');

  useEffect(() => {
    if (inspectedLayer) setTab('detail');
  }, [inspectedLayer]);

  const onSelect = (sym: string) => {
    handleSelectSymbol(sym);
    setTab('detail');
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {[
          ['rankings', 'Top 25'],
          ['detail', 'Detail'],
          ['theses', 'Theses'],
          ['activity', 'Activity'],
        ].map(([k, lbl]) => (
          <button
            key={k}
            onClick={() => setTab(k as typeof tab)}
            className="touch-target flex-1 py-3 text-[12px] font-semibold transition-colors"
            style={{
              color: tab === k ? 'var(--text-primary)' : 'var(--text-tertiary)',
              borderBottom: `2px solid ${tab === k ? 'var(--accent)' : 'transparent'}`,
              background: tab === k ? 'var(--bg-surface-raised)' : 'transparent',
            }}
          >
            {lbl}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {tab === 'rankings' && (
          <RankingsPanel
            onSelectSymbol={onSelect}
            entries={[...longRankings, ...shortRankings]}
            flashedSymbols={new Map()}
          />
        )}
        {tab === 'detail' && (
          <DetailColumn
            selected={selected}
            longRankings={longRankings}
            viewMode={viewMode}
            setViewMode={setViewMode}
            learnMode={learnMode}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
          />
        )}
        {tab === 'theses' && (
          <>
            <ActiveMonitor />
            <EdgePanel />
          </>
        )}
        {tab === 'activity' && (
          <CycleActivity
            events={activityEvents}
            onSelect={onSelect}
            selectedSymbol={selected?.symbol ?? null}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 16.2: Update `LayerInspector` / `LayerJourney` / `DetailPanel` props for compatibility**

These components were typed against `SimStock` / `SimSnapshot` / `SimMarketContext`. Until Task 18 deletes the simulator types, this temporary `as any` lets the build pass. After Task 18, do a focused pass to retype these props against the real `RankingEntry` / `MarketContextFrame` types (note: `RankingEntry` already covers most fields; gaps go on a follow-up).

- [ ] **Step 16.3: Build + manual smoke**

Run: `cd frontend && npm run build`

Expected: build succeeds.

Run: `cd frontend && npm run dev`

In a browser, open `http://localhost:8190/`. Expect:
- Page loads without console errors.
- `RegimeBanner` shows "Waiting for L1 context…" briefly, then populates with REST mock context bearing yellow `MOCK` badge.
- `RankingsPanel` populates with mock data + `MOCK` badge.
- Top-right "Truth" button visible; clicking expands `DataSourceDebugPanel` showing all endpoints = mock, all layers red.

- [ ] **Step 16.4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor(frontend): App.tsx uses real REST hooks; mounts DataSourceDebugPanel

Removed the useEngine hook and syncToStore — frontend simulator is no
longer wired into the app. Top-25, regime, funnel, activity,
active-theses, edge-tiers, and pipeline-status are now driven by their
respective REST hooks (each carries source labelling). The
DataSourceDebugPanel renders top-right. The simulator file
(engineSimulator.ts) is still on disk but unreferenced; deleted in Task 18."
```

---

## Task 17: Verify simulator is unreferenced

**Files:**
- (read-only verification)

- [ ] **Step 17.1: Grep for residual references**

Run:
```bash
cd frontend && grep -rn "engineSimulator\|genUniverse\|genMarketContext\|genPipelineStatus\|computeFunnel\|mulberry32\|SimStock\|SimSnapshot\|SimMarketContext\|useAlertFeed\|useCycleActivity" src/
```

Expected: **only matches inside `src/data/engineSimulator.ts` itself, `src/components/AlertToast.tsx`, and `src/components/CycleActivity.tsx`**.

The two components define `useAlertFeed` / `useCycleActivity` hooks that historically took a simulator snapshot. Inspect each:

- [ ] **Step 17.2: Inspect AlertToast and CycleActivity**

Run: `cat frontend/src/components/AlertToast.tsx frontend/src/components/CycleActivity.tsx`

For each, locate the `useAlertFeed` / `useCycleActivity` exported hook. If the hook signature accepts a `snapshot` argument and produces alerts/events from it (rather than just reading store state), refactor:

- `useAlertFeed(snapshot, cycle)` → `useAlerts()` reading from `useMarketStore.invalidatedTheses` (already populated by WS) and from `/api/activity/events` for trigger/T1 events.
- `useCycleActivity(snapshot, cycle)` → REMOVE; `App.tsx` already uses `useActivityEvents()` for the same data.

If the existing hook is purely consumer-side (no simulator import), leave it alone.

If you find a simulator import in either component, refactor it out — replace the snapshot-derived logic with `useMarketStore` reads of WS-populated state.

- [ ] **Step 17.3: Re-grep**

Run:
```bash
cd frontend && grep -rn "engineSimulator\|genUniverse\|genMarketContext\|genPipelineStatus\|computeFunnel\|mulberry32\|SimStock\|SimSnapshot\|SimMarketContext" src/
```

Expected: **only matches inside `src/data/engineSimulator.ts` itself.** All component references gone.

Run: `cd frontend && npm run build`

Expected: build succeeds.

Run: `cd frontend && npm test -- --run`

Expected: all tests PASS.

- [ ] **Step 17.4: Commit**

```bash
git add frontend/src/
git commit -m "refactor(frontend): remove residual simulator coupling from AlertToast and CycleActivity

useAlertFeed and useCycleActivity now read WS-populated store state and
real REST endpoints instead of a simulator snapshot. The simulator file
itself is still on disk but truly unreferenced; deleted in Task 18."
```

(If no AlertToast / CycleActivity refactor was needed, skip this commit and continue.)

---

## Task 18: Delete `engineSimulator.ts`

**Files:**
- Delete: `frontend/src/data/engineSimulator.ts`

- [ ] **Step 18.1: Delete the file**

Run:
```bash
git rm frontend/src/data/engineSimulator.ts
```

If the `frontend/src/data/` directory is now empty, leave it (don't `rmdir` — `.gitkeep` not required).

- [ ] **Step 18.2: Verify nothing breaks**

Run: `cd frontend && npx tsc --noEmit`

Expected: zero TypeScript errors.

Run: `cd frontend && npm test -- --run`

Expected: all tests PASS.

Run: `cd frontend && npm run build`

Expected: build succeeds.

- [ ] **Step 18.3: Final regression grep**

Run:
```bash
cd frontend && grep -rn "engineSimulator\|genUniverse\|genMarketContext\|genPipelineStatus\|computeFunnel\|mulberry32\|SimStock\|SimSnapshot\|SimMarketContext" src/
```

Expected: **zero matches.**

- [ ] **Step 18.4: Commit**

```bash
git commit -m "feat(frontend): delete engineSimulator.ts — client-side fabricator removed

501-line client-side simulator that fabricated full L1-L10 universe
every 10s via mulberry32 PRNG is now gone. Dashboard is fed exclusively
by REST hooks (apiFetch-wrapped) and WebSocket pushes, each carrying a
data-source label rendered as a MockBadge in every panel."
```

---

## Task 19: Update auto-memory + close out

**Files:**
- Modify: `C:\Users\phani\.claude\projects\C--Users-phani-projects-Kimi-Intraday-Dashboard\memory\dashboard-shows-mock-data-pre-phase-a.md`
- Modify: `C:\Users\phani\.claude\projects\C--Users-phani-projects-Kimi-Intraday-Dashboard\memory\MEMORY.md`

- [ ] **Step 19.1: Delete the now-obsolete project memory**

The `dashboard-shows-mock-data-pre-phase-a.md` memory becomes stale once Phase A ships — the lies are now visibly labelled and the simulator is gone. Delete the file and remove its line from `MEMORY.md`.

Run:
```bash
rm "C:\Users\phani\.claude\projects\C--Users-phani-projects-Kimi-Intraday-Dashboard\memory\dashboard-shows-mock-data-pre-phase-a.md"
```

Edit `MEMORY.md` to remove the corresponding line.

- [ ] **Step 19.2: Final smoke on the live URL**

Restart backend + frontend per CLAUDE.md, then:

```bash
curl -s -i https://kimi.intraday-edge-4zz.uk/api/telemetry/data-sources | head -20
```

Expected: `200 OK` + JSON body with `endpoints`, `pipeline`, `layers` keys.

Open https://kimi.intraday-edge-4zz.uk/ in a browser:
- Every panel shows a yellow `MOCK` badge (outside market hours, this is expected and now honest).
- Top-right "Truth" button toggles `DataSourceDebugPanel` showing every endpoint = `mock` and every layer = red.
- No console errors.
- No "Trending-Up" preview text appearing instantly on page load (subscribe-ack stub deleted).

- [ ] **Step 19.3: Final commit (optional)**

Only if Step 19.2 surfaced any unexpected behavior requiring fix-up:

```bash
git add <fixes>
git commit -m "fix(<area>): <one-line description>"
```

Otherwise, Phase A is shipped.

---

## Self-review (run before handing the plan off)

### Spec coverage

- §1 Audit findings — informational, not implementation. ✓
- §2.1 Goal — Tasks 5-18 (delete simulator, surface source). ✓
- §2.3 Success criteria — verified in Step 19.2 smoke + Steps 17.1/18.3 greps. ✓
- §3.1.1 WS source field + delete stub — Task 3. ✓
- §3.1.2 X-Data-Source on remaining endpoints + truthful /health — Task 2. ✓
- §3.1.3 New telemetry endpoint — Task 4. ✓
- §3.1.4 Backend mock fallback stays — no task needed (explicit non-change). ✓
- §3.2 Frontend deletions — Tasks 16, 17, 18. ✓
- §3.3.1 apiFetch — Task 5. ✓
- §3.3.2 sources slice — Task 6. ✓
- §3.3.3 MockBadge — Task 8. ✓
- §3.3.4 DataSourceDebugPanel — Task 13. ✓
- §3.3.5 Honest empty states — Task 14 (per-panel copy table). ✓
- §3.3.6 WS source consumption — Task 15. ✓
- §3.4 Component-to-source mapping — Task 14 (matches spec table). ✓
- §3.5 Five new hooks — Task 12. ✓
- §4 Testing — every implementation task pairs TDD test + commit. ✓

### Placeholder scan

- No "TBD", "TODO", "implement later", "similar to Task N" in the plan body.
- One soft reference in Task 16.2 ("focused pass to retype these props ... gaps go on a follow-up") — explicitly bounds the scope and the follow-up is documented in the commit message. Acceptable.

### Type consistency

- `DataSource` type defined in Task 5 (`apiFetch.ts`) and referenced consistently in Tasks 6, 7, 8, 12, 13, 15. ✓
- `setSource(key, source)` signature used identically across hooks in Tasks 9, 10, 11, 12. ✓
- `MockBadge` props (`source: DataSource | undefined`) consistent across all panel insertions in Task 14. ✓
- WS source key convention: `ws/${msg.type.toLowerCase()}` — Task 15 implementation matches Task 14's `ws/l1_context` lookups. ✓
