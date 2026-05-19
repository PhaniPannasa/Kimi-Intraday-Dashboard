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
        "l2_real":  getattr(pipeline, '_l2_flags_populated', False),  # True when NSE scraper runs
        "l3_real":  symbols_with_bars >= 1,
        "l4_real":  getattr(pipeline, '_sector_rs_real', False),  # True when sector RS computed
        "l5_real":  symbols_with_bars >= 1 and has_rankings,
        "l6_real":  has_rankings,
        "l7_real":  has_rankings,
        "l8_real":  has_theses,
        "l9_real":  has_theses,
        "l10_real": getattr(pipeline.l10, 'edge_store', {}) and len(pipeline.l10.edge_store) > 0,
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
