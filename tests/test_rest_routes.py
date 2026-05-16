import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_get_market_context(client):
    response = await client.get("/market/context")
    assert response.status_code == 200
    data = response.json()
    assert "regime" in data


@pytest.mark.asyncio
async def test_get_rankings_long(client):
    response = await client.get("/rankings/top25/long")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "symbol" in data[0]


@pytest.mark.asyncio
async def test_get_thesis(client):
    response = await client.get("/thesis/test-thesis-1")
    assert response.status_code == 200
    data = response.json()
    assert data["thesis_id"] == "test-thesis-1"


@pytest.mark.asyncio
async def test_get_edge_tiers(client):
    response = await client.get("/edge/tiers")
    assert response.status_code == 200
    data = response.json()
    assert "tiers" in data
