from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from models.enums import Regime
from models.frames import MarketContextFrame

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and provides broadcast support."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws/v1/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "subscribe":
                channels = data.get("channels", [])
                if "market" in channels:
                    await websocket.send_json({
                        "type": "L1_CONTEXT",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": MarketContextFrame(
                            regime=Regime.TRENDING_UP,
                            regime_confidence=0.85,
                        ).model_dump(),
                    })
                if "rankings" in channels:
                    await websocket.send_json({
                        "type": "L6_RANKINGS",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {"long": [], "short": []},
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
