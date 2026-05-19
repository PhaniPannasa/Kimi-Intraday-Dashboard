from fastapi.testclient import TestClient
from main import app


def test_websocket_connect_and_subscribe():
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/stream") as websocket:
        websocket.send_json({"action": "subscribe", "channels": ["market"]})
        data = websocket.receive_json()
        assert data["type"] == "SUBSCRIBED"
