"""E2E smoke test — starts the FastAPI app and hits all REST + WebSocket endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from main import app


@pytest.mark.asyncio
async def test_smoke_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_smoke_market_context():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/market/context")
        assert response.status_code == 200
        data = response.json()
        assert "regime" in data


@pytest.mark.asyncio
async def test_smoke_rankings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/rankings/top25/long")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_smoke_thesis():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/thesis/smoke-test-id")
        assert response.status_code == 200
        data = response.json()
        assert data["thesis_id"] == "smoke-test-id"


@pytest.mark.asyncio
async def test_smoke_edge():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/edge/tiers")
        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data


def test_smoke_websocket():
    """Verify WebSocket stream connection works (sync TestClient)."""
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/stream") as websocket:
        websocket.send_json({"action": "subscribe", "channels": ["market"]})
        data = websocket.receive_json()
        assert data["type"] == "SUBSCRIBED"
