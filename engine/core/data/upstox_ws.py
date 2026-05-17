import asyncio
import json

import websockets

from config import settings


class UpstoxWSClient:
    def __init__(self):
        self.ws = None
        self.url = "wss://api.upstox.com/v3/feed/market-data-feed"
        self.headers = {"Authorization": f"Bearer {settings.upstox_analytics_token}"}
        self.subscribed = set()
        self.running = False
        self.on_tick = None  # async callback (message) -> None

    async def connect(self):
        self.ws = await websockets.connect(self.url, extra_headers=self.headers)
        self.running = True

    async def subscribe(self, instrument_keys: list[str], mode: str = "full"):
        msg = {
            "guid": "intraday-engine-1",
            "method": "sub",
            "data": {
                "instrumentKeys": instrument_keys,
                "mode": mode,
            },
        }
        await self.ws.send(json.dumps(msg))
        self.subscribed.update(instrument_keys)

    async def unsubscribe(self, instrument_keys: list[str]):
        msg = {
            "guid": "intraday-engine-1",
            "method": "unsub",
            "data": {
                "instrumentKeys": instrument_keys,
            },
        }
        await self.ws.send(json.dumps(msg))
        self.subscribed.difference_update(instrument_keys)

    async def listen(self):
        async for message in self.ws:
            if self.on_tick:
                await self.on_tick(message)
            yield message

    async def close(self):
        self.running = False
        if self.ws:
            await self.ws.close()


upstox_ws = UpstoxWSClient()
