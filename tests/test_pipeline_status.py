import pytest


@pytest.mark.asyncio
async def test_pipeline_status(client):
    response = await client.get("/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
    assert len(data["layers"]) == 10
    assert data["layers"]["l1_market_context"]["status"] == "ok"


@pytest.mark.asyncio
async def test_pipeline_status_fields(client):
    response = await client.get("/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "last_cycle_at" in data
    assert "cycle_duration_ms" in data
    assert "market_session" in data
    assert "time_bucket" in data


@pytest.mark.asyncio
async def test_pipeline_status_all_layers(client):
    response = await client.get("/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    expected_layers = [
        "l1_market_context", "l2_universe", "l3_signals",
        "l4_sector", "l5_scoring", "l6_ranking",
        "l7_confluence", "l8_thesis", "l9_monitor", "l10_edge",
    ]
    for layer in expected_layers:
        assert layer in data["layers"], f"Missing layer: {layer}"
        assert "status" in data["layers"][layer]
        assert "duration_ms" in data["layers"][layer]
