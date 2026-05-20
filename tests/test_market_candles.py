"""Tests for /market/candles/{symbol} endpoint.

Phase B Fix #2: the endpoint must
  (a) never 500, even when DB is down;
  (b) return mock-fallback candles with X-Data-Source: mock on DB failure / no rows;
  (c) return DB rows with X-Data-Source: pipeline when the query succeeds;
  (d) return 404 for an unknown symbol;
  (e) use pipeline.symbol_map for the real instrument key (ISIN-based),
      not the naive f"NSE_EQ|{symbol}" string.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_candles_db_down_returns_200_with_mock_header(client):
    """When the DB raises (e.g. pool not initialized), endpoint must
    fall through to mock candles, return 200 with X-Data-Source: mock."""
    with patch("api.rest_routes.timescale_db.fetch", new=AsyncMock(side_effect=RuntimeError("db down"))):
        response = await client.get("/market/candles/RELIANCE")
    assert response.status_code == 200
    assert response.headers.get("X-Data-Source") == "mock"
    data = response.json()
    assert data["symbol"] == "RELIANCE"
    assert "candles" in data
    assert isinstance(data["candles"], list)
    assert len(data["candles"]) > 0, "mock-fallback must emit a non-empty candle series"
    # Every candle has OHLC keys
    for candle in data["candles"]:
        assert {"o", "h", "l", "c"}.issubset(candle.keys())


@pytest.mark.asyncio
async def test_candles_db_returns_rows_uses_pipeline_header(client):
    """When the DB returns real rows, endpoint returns them with
    X-Data-Source: pipeline. The query must use pipeline.symbol_map
    (ISIN-based), not f"NSE_EQ|{symbol}"."""
    fake_rows = [
        {"ts": "2026-05-20T09:15:00Z", "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5, "volume": 1000},
        {"ts": "2026-05-20T09:16:00Z", "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 2000},
    ]
    captured_args = {}

    async def fake_fetch(query, *args):
        captured_args["query"] = query
        captured_args["args"] = args
        return fake_rows

    with patch("api.rest_routes.timescale_db.fetch", new=fake_fetch):
        response = await client.get("/market/candles/RELIANCE")

    assert response.status_code == 200
    assert response.headers.get("X-Data-Source") == "pipeline"
    data = response.json()
    assert data["symbol"] == "RELIANCE"
    assert len(data["candles"]) == 2

    # Critical: the instrument_key bound to $1 must be the ISIN-based key
    # from pipeline.symbol_map, NOT the naive f"NSE_EQ|RELIANCE".
    assert captured_args["args"][0] == "NSE_EQ|INE002A01018", (
        f"expected ISIN-based instrument key, got {captured_args['args'][0]!r}"
    )


@pytest.mark.asyncio
async def test_candles_db_empty_falls_back_to_mock(client):
    """If the DB query succeeds but returns no rows, fall back to mock
    candles with X-Data-Source: mock so the chart panel never sees an
    empty payload."""
    with patch("api.rest_routes.timescale_db.fetch", new=AsyncMock(return_value=[])):
        response = await client.get("/market/candles/RELIANCE")
    assert response.status_code == 200
    assert response.headers.get("X-Data-Source") == "mock"
    data = response.json()
    assert len(data["candles"]) > 0


@pytest.mark.asyncio
async def test_candles_unknown_symbol_returns_404(client):
    """An unknown symbol must return 404, not 500 and not a mock."""
    response = await client.get("/market/candles/NOTASYMBOL")
    assert response.status_code == 404
    body = response.json()
    assert "NOTASYMBOL" in body.get("detail", "")


@pytest.mark.asyncio
async def test_candles_response_shape_has_overlays_key(client):
    """The contract is {symbol, interval, candles, overlays} — overlays
    may be None or a CandleOverlays dict, but the key must exist."""
    with patch("api.rest_routes.timescale_db.fetch", new=AsyncMock(side_effect=RuntimeError("db down"))):
        response = await client.get("/market/candles/RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert "overlays" in data
    assert "interval" in data
