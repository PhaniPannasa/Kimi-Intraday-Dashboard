import asyncio
import json
import ssl
import threading
import websocket

from config import settings


class UpstoxWSClient:
    def __init__(self):
        self._ws: websocket.WebSocketApp | None = None
        self.url = "wss://api.upstox.com/v3/feed/market-data-feed"
        self.headers = {"Authorization": f"Bearer {settings.upstox_analytics_token}"}
        self.subscribed: set[str] = set()
        self.running = False
        self.on_tick = None  # async callback (message) -> None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    async def connect(self):
        self._loop = asyncio.get_running_loop()

        def on_open(ws):
            self.running = True

        def on_message(ws, message):
            if self.on_tick and self._loop:
                asyncio.run_coroutine_threadsafe(self.on_tick(message), self._loop)

        def on_error(ws, error):
            pass

        def on_close(ws, code, msg):
            self.running = False

        self._ws = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}},
            daemon=True,
        )
        self._thread.start()

        # Wait for connection to establish (max 5 seconds)
        for _ in range(50):
            if self.running:
                break
            await asyncio.sleep(0.1)

    async def subscribe(self, instrument_keys: list[str], mode: str = "full"):
        msg = {
            "guid": "intraday-engine-1",
            "method": "sub",
            "data": {
                "instrumentKeys": instrument_keys,
                "mode": mode,
            },
        }
        if self._ws and self._ws.sock:
            payload = json.dumps(msg).encode("utf-8")
            self._ws.send(payload, opcode=websocket.ABNF.OPCODE_BINARY)
            self.subscribed.update(instrument_keys)

    async def unsubscribe(self, instrument_keys: list[str]):
        msg = {
            "guid": "intraday-engine-1",
            "method": "unsub",
            "data": {
                "instrumentKeys": instrument_keys,
            },
        }
        if self._ws and self._ws.sock:
            self._ws.send(json.dumps(msg).encode("utf-8"), opcode=websocket.ABNF.OPCODE_BINARY)
            self.subscribed.difference_update(instrument_keys)

    async def close(self):
        self.running = False
        if self._ws:
            self._ws.close()

    async def listen(self):
        while self.running:
            await asyncio.sleep(1)


upstox_ws = UpstoxWSClient()
