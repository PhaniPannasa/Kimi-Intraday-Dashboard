import pytest


@pytest.mark.asyncio
async def test_symbol_factors(client):
    response = await client.get("/rankings/RELIANCE/factors")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE"
    assert "l2_universe" in data
    assert "l3_signals" in data
    assert "l5_scores" in data
    assert data["l7_confluence"]["score"] >= 0


@pytest.mark.asyncio
async def test_symbol_factors_different_symbol(client):
    response = await client.get("/rankings/TCS/factors")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TCS"
    assert data["l2_universe"]["fo_eligible"] is True


@pytest.mark.asyncio
async def test_symbol_factors_response_model(client):
    """Verify all top-level keys are present."""
    response = await client.get("/rankings/INFY/factors")
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "symbol", "direction", "last_updated",
        "l2_universe", "l3_signals", "l4_sector",
        "l5_scores", "l6_ranking", "l7_confluence", "l8_thesis",
    ]
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"
