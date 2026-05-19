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
