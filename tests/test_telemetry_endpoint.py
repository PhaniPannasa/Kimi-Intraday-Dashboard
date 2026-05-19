"""Integration tests for X-Data-Source headers and the telemetry endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_sets_data_source_header(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_activity_events_sets_data_source_header(client):
    resp = await client.get("/activity/events?limit=5")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_edge_tiers_sets_data_source_header(client):
    resp = await client.get("/edge/tiers")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_symbol_factors_sets_data_source_header(client):
    resp = await client.get("/rankings/RELIANCE/factors")
    assert resp.status_code == 200
    assert resp.headers.get("x-data-source") in ("pipeline", "mock")


@pytest.mark.asyncio
async def test_telemetry_data_sources_returns_full_shape(client):
    resp = await client.get("/telemetry/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "timestamp" in data
    assert "endpoints" in data
    assert "pipeline" in data
    assert "layers" in data
    assert "phase" in data["pipeline"]
    assert "symbols_feeding" in data["pipeline"]
    assert "ws_connections" in data["pipeline"]
    # Layers must include all 10
    for k in ("l1_real", "l2_real", "l3_real", "l4_real", "l5_real",
              "l6_real", "l7_real", "l8_real", "l9_real", "l10_real"):
        assert k in data["layers"]


@pytest.mark.asyncio
async def test_telemetry_data_sources_reports_mock_when_pipeline_empty(client):
    """With no real pipeline data, every endpoint should report 'mock'."""
    resp = await client.get("/telemetry/data-sources")
    data = resp.json()
    assert data["endpoints"]["/market/context"] == "mock"
    assert data["endpoints"]["/rankings/top25/long"] == "mock"
    assert data["endpoints"]["/health"] == "mock"
