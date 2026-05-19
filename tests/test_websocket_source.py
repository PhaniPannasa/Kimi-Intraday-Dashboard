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
    ws.accept = AsyncMock()
    ws.receive_json = AsyncMock(side_effect=[
        {"action": "subscribe", "channels": ["market", "rankings"]},
        # Second call: simulate disconnect
        Exception("disconnect"),
    ])

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
