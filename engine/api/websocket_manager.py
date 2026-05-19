"""WebSocket manager for the Kimi Intraday Dashboard.

Manages real-time push of L1-L10 pipeline data to connected frontends.

Message Types (existing — unchanged):
    L1_CONTEXT       → MarketContextFrame (market context, regime, VIX, breadth)
    L6_RANKINGS      → {long: [...], short: [...]}  (Top 25 rankings)
    L8_THESIS        → {thesis_id, card}  (thesis card for a stock)
    L9_INVALIDATION  → {thesis_id, reason}  (thesis stopped out)
    L10_EDGE         → {tier, promotion}  (edge tier promotion event)

Message Types (new — additive):
    ALERT            → {type, symbol, message}  (triggered, t1_hit, t2_hit, ...)
    FUNNEL_COUNTS    → {L1: {in, out}, ... L10: {in, out}}  (funnel survivors)
    CYCLE_ACTIVITY   → {id, type, symbol, direction, text, detail, cycle}
    SUBSCRIBED       → channel subscription acknowledgement
    UNSUBSCRIBED     → channel unsubscription acknowledgement
    SUBSCRIPTIONS    → current subscription listing
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from models.enums import Regime
from models.frames import MarketContextFrame

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections with per-client channel subscriptions.

    Provides broadcast methods for all pipeline message types (L1-L10) plus
    the enhanced UI message types (ALERT, FUNNEL_COUNTS, CYCLE_ACTIVITY).

    Usage (singleton):
        from api.websocket_manager import manager
        await manager.broadcast_alert("triggered", "RELIANCE", "...")
    """

    def __init__(self) -> None:
        # Each entry is (websocket, set_of_subscribed_channels)
        self._connections: list[tuple[WebSocket, set[str]]] = []

        # Pipeline cycle counter — incremented each run_cycle
        self.cycle_count: int = 0

        # Last known market context — used to detect regime changes
        self.last_context: Optional[MarketContextFrame] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and register it with no subscriptions."""
        await websocket.accept()
        self._connections.append((websocket, set()))
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection (idempotent)."""
        for i, (conn, _) in enumerate(self._connections):
            if conn is websocket:
                self._connections.pop(i)
                logger.info("WebSocket client disconnected (%d remaining)", len(self._connections))
                return

    # ------------------------------------------------------------------
    # Per-client subscription management
    # ------------------------------------------------------------------

    def subscribe(self, websocket: WebSocket, channels: list[str]) -> set[str]:
        """Add channel subscriptions for a client. Returns the updated subscription set."""
        for conn, subs in self._connections:
            if conn is websocket:
                subs.update(channels)
                return subs
        return set()

    def unsubscribe(self, websocket: WebSocket, channels: list[str]) -> set[str]:
        """Remove channel subscriptions for a client. Returns the updated subscription set."""
        for conn, subs in self._connections:
            if conn is websocket:
                subs.difference_update(channels)
                return subs
        return set()

    def get_subscriptions(self, websocket: WebSocket) -> set[str]:
        """Get the set of channels a client is currently subscribed to."""
        for conn, subs in self._connections:
            if conn is websocket:
                return subs
        return set()

    # ------------------------------------------------------------------
    # Broadcast primitives
    # ------------------------------------------------------------------

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

    async def broadcast(self, message: dict) -> None:
        """Send *message* to ALL connected clients (legacy compatibility).

        Used by the pipeline orchestrator for existing message types:
        L1_CONTEXT, L6_RANKINGS, L8_THESIS, L9_INVALIDATION, L10_EDGE.
        """
        await self._broadcast_to_channel(message, "*")

    async def broadcast_to(self, message: dict, channels: set[str]) -> None:
        """Send *message* to clients subscribed to **any** of the given *channels*."""
        stale: list[WebSocket] = []
        for conn, subs in self._connections:
            if not subs.intersection(channels):
                continue
            try:
                await conn.send_json(message)
            except Exception:
                stale.append(conn)

        for conn in stale:
            self.disconnect(conn)

    # ------------------------------------------------------------------
    # Pipeline cycle tracking
    # ------------------------------------------------------------------

    def increment_cycle(self) -> int:
        """Increment and return the current pipeline cycle number.

        Call this once at the start of each ``_run_live_cycle()`` so that
        subsequent cycle-activity events are tagged with the correct number.
        """
        self.cycle_count += 1
        return self.cycle_count

    def detect_regime_change(self, new_context: MarketContextFrame) -> Optional[tuple[str, str]]:
        """Check whether the market regime has changed since the last cycle.

        Stores *new_context* for subsequent comparisons.

        Returns ``(old_regime, new_regime)`` on change, otherwise ``None``.
        """
        old_str = (
            self.last_context.regime.value
            if self.last_context is not None and hasattr(self.last_context.regime, "value")
            else str(self.last_context.regime) if self.last_context is not None
            else None
        )
        new_str = (
            new_context.regime.value
            if hasattr(new_context.regime, "value")
            else str(new_context.regime)
        )

        self.last_context = new_context

        if old_str is not None and old_str != new_str:
            return (old_str, new_str)
        return None

    # ------------------------------------------------------------------
    # Enhanced frontend broadcast methods  (NEW — additive)
    # ------------------------------------------------------------------

    async def broadcast_alert(
        self,
        alert_type: str,
        symbol: str,
        message: str,
    ) -> None:
        """Broadcast an ALERT to clients subscribed to the ``alerts`` channel.

        Args:
            alert_type: One of ``"triggered"``, ``"t1_hit"``, ``"t2_hit"``,
                       ``"invalidation"``, ``"regime"``, ``"edge"``.
            symbol: Trading symbol (e.g. ``"RELIANCE"``).
            message: Human-readable alert text.

        Wire format::

            {
              "type": "ALERT",
              "timestamp": "2026-05-18T10:15:30+00:00",
              "payload": {
                "type": "triggered",
                "symbol": "RELIANCE",
                "message": "RELIANCE LONG triggered @ 1,290.50 (ORB-15m)",
                "ts": "2026-05-18T10:15:30+05:30"
              }
            }
        """
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "type": alert_type,
            "symbol": symbol,
            "message": message,
            "ts": now,
        }
        await self._broadcast_to_channel(
            {"type": "ALERT", "timestamp": now, "payload": payload},
            channel="alerts",
        )

    async def broadcast_funnel_counts(self, funnel_counts: dict) -> None:
        """Broadcast funnel survivor counts to clients subscribed to ``funnel``.

        Args:
            funnel_counts: Dict keyed by layer name (``"L1"`` … ``"L10"``),
                          each value being ``{"in": int, "out": int}``.

        Wire format::

            {
              "type": "FUNNEL_COUNTS",
              "timestamp": "2026-05-18T10:15:30+00:00",
              "payload": {
                "L1": {"in": 1, "out": 1},
                "L2": {"in": 50, "out": 48},
                ...
                "L10": {"in": 8, "out": 3}
              }
            }
        """
        now = datetime.now(timezone.utc).isoformat()
        await self._broadcast_to_channel(
            {"type": "FUNNEL_COUNTS", "timestamp": now, "payload": funnel_counts},
            channel="funnel",
        )

    async def broadcast_cycle_activity(self, event: dict) -> None:
        """Broadcast a single cycle-activity event to clients subscribed to ``activity``.

        Args:
            event: Dict with keys:
                - ``id`` (str): Unique event identifier (auto-generated if absent).
                - ``type`` (str): Event category — ``"NEW"``, ``"DROP"``, ``"TRIGGER"``,
                  ``"T1"``, ``"JUMP_UP"``, ``"JUMP_DN"``, ``"STATE"``.
                - ``symbol`` (str): Trading symbol.
                - ``direction`` (str): ``"LONG"`` or ``"SHORT"``.
                - ``text`` (str): Short human-readable description.
                - ``detail`` (str): Optional additional detail (score, setup, etc.).
                - ``cycle`` (int): Pipeline cycle number.

        Wire format::

            {
              "type": "CYCLE_ACTIVITY",
              "timestamp": "2026-05-18T10:15:30+00:00",
              "payload": {
                "id": "evt-a1b2c3d4",
                "type": "NEW",
                "symbol": "RELIANCE",
                "direction": "LONG",
                "text": "entered TOP 25 LONG",
                "detail": "score 84.5 · ORB-15m",
                "cycle": 42
              }
            }
        """
        now = datetime.now(timezone.utc).isoformat()
        if "id" not in event:
            event["id"] = f"evt-{uuid.uuid4().hex[:8]}"
        await self._broadcast_to_channel(
            {"type": "CYCLE_ACTIVITY", "timestamp": now, "payload": event},
            channel="activity",
        )

    # ==================================================================
    # Pipeline Integration Guide
    #
    # These integration points show where the pipeline orchestrator
    # (engine/core/pipeline.py) should call the new broadcast methods.
    #
    # ── After each cycle completes ────────────────────────────────────
    #   Call: broadcast_funnel_counts(funnel_counts)
    #   Where: End of _run_live_cycle(), after L10 edge lookup, before
    #          Redis persistence.
    #   What:  Gather {L1..L10: {"in": N, "out": N}} from each layer's
    #          input/output counts and push to the frontend FunnelStrip.
    #
    # ── When regime changes ───────────────────────────────────────────
    #   Call: if manager.detect_regime_change(context):
    #            old, new = result
    #            await manager.broadcast_alert(
    #                "regime", "MARKET",
    #                f"Regime changed from {old} to {new}",
    #            )
    #   Where: After L1 computation in _run_live_cycle(), right after
    #          self.latest_context is set.
    #
    # ── When a thesis triggers ────────────────────────────────────────
    #   Call: broadcast_alert("triggered", symbol, f"... triggered @ ...")
    #   Where: In the L9 processing loop, after l9.on_create() and
    #          l9.on_trigger() succeed.
    #
    # ── When T1 is hit ────────────────────────────────────────────────
    #   Call: broadcast_alert("t1_hit", symbol, f"... T1 hit @ ...")
    #   Where: In the L9 on_tick() result loop, when the result state
    #          is "T1_HIT".
    #
    # ── When a thesis invalidates / stops out ─────────────────────────
    #   Call: broadcast_alert("invalidation", symbol, f"... stopped @ ...")
    #   Where: Alongside the existing L9_INVALIDATION broadcast in the
    #          L9 on_tick() result loop (state == "STOPPED_OUT").
    #
    # ── When stocks enter / drop from Top 25 ──────────────────────────
    #   Call: broadcast_cycle_activity({
    #       "type": "NEW" | "DROP" | "JUMP_UP" | "JUMP_DN",
    #       "symbol": ...,
    #       "direction": "LONG" | "SHORT",
    #       "text": "entered TOP 25 LONG",
    #       "detail": f"score {score} · {setup_label}",
    #       "cycle": manager.cycle_count,
    #   })
    #   Where: After L6 ranking in _run_live_cycle(), iterating over
    #          ranked results to find rank_movement == "NEW"/"UP"/"DOWN".
    # ==================================================================


# Module-level singleton
manager = ConnectionManager()


@router.websocket("/ws/v1/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint supporting channel subscriptions.

    Subscribe to channels by sending::

        {"action": "subscribe", "channels": ["market", "rankings", "alerts", "funnel", "activity"]}

    Unsubscribe from channels::

        {"action": "unsubscribe", "channels": ["alerts"]}

    List current subscriptions::

        {"action": "subscriptions"}
    """
    now = datetime.now(timezone.utc).isoformat
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "subscribe":
                channels = data.get("channels", [])
                manager.subscribe(websocket, channels)
                # Acknowledge — no stub payloads. Real data arrives via pipeline broadcasts.
                await websocket.send_json({
                    "type": "SUBSCRIBED",
                    "timestamp": now(),
                    "payload": {"channels": list(manager.get_subscriptions(websocket))},
                })

            elif action == "unsubscribe":
                channels = data.get("channels", [])
                manager.unsubscribe(websocket, channels)
                await websocket.send_json({
                    "type": "UNSUBSCRIBED",
                    "timestamp": now(),
                    "payload": {"channels": list(manager.get_subscriptions(websocket))},
                })

            elif action == "subscriptions":
                await websocket.send_json({
                    "type": "SUBSCRIPTIONS",
                    "timestamp": now(),
                    "payload": {"channels": list(manager.get_subscriptions(websocket))},
                })

            else:
                await websocket.send_json({
                    "type": "ERROR",
                    "timestamp": now(),
                    "payload": {"message": f"Unknown action: {action}"},
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
