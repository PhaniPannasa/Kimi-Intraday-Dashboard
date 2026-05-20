import json
from unittest.mock import MagicMock

import pytest

from core.data.upstox_ws import UpstoxWSClient


@pytest.mark.asyncio
async def test_subscribe_sends_correct_message():
    """V3 feed: subscribe() now calls websocket-client's synchronous send()
    with a UTF-8-encoded payload and an explicit binary opcode."""
    client = UpstoxWSClient()
    # The new client checks `if self._ws and self._ws.sock` before sending,
    # so both attributes must be truthy mocks.
    client._ws = MagicMock()
    client._ws.sock = MagicMock()
    await client.subscribe(["NSE_EQ|INE002A01018"])
    sent_bytes = client._ws.send.call_args[0][0]
    assert isinstance(sent_bytes, bytes), "subscribe must send a bytes payload"
    data = json.loads(sent_bytes.decode("utf-8"))
    assert data["method"] == "sub"
    assert "NSE_EQ|INE002A01018" in data["data"]["instrumentKeys"]
