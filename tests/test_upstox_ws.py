import json
from unittest.mock import AsyncMock

import pytest

from core.data.upstox_ws import UpstoxWSClient


@pytest.mark.asyncio
async def test_subscribe_sends_correct_message():
    client = UpstoxWSClient()
    client.ws = AsyncMock()
    await client.subscribe(["NSE_EQ|INE002A01018"])
    sent = client.ws.send.call_args[0][0]
    data = json.loads(sent)
    assert data["method"] == "sub"
    assert "NSE_EQ|INE002A01018" in data["data"]["instrumentKeys"]
