import pytest
import respx
from httpx import Response

from core.data.upstox_rest import UpstoxRESTClient


@pytest.fixture
def client():
    return UpstoxRESTClient()


@pytest.mark.asyncio
@respx.mock
async def test_get_historical_candle(client):
    route = respx.get(
        "https://api.upstox.com/v2/historical-candle/NSE_EQ|INE002A01018/1minute/2026-05-19"
    ).mock(return_value=Response(200, json={"data": {"candles": []}}))

    result = await client.get_historical_candle("NSE_EQ|INE002A01018", date="2026-05-19")

    assert result["data"]["candles"] == []
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_option_chain(client):
    route = respx.get(
        "https://api.upstox.com/v2/option/chain",
        params={"instrument_key": "NSE_EQ|INE002A01018"},
    ).mock(return_value=Response(200, json={"data": {"options": []}}))

    result = await client.get_option_chain("NSE_EQ|INE002A01018")

    assert result["data"]["options"] == []
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_market_oi(client):
    route = respx.get(
        "https://api.upstox.com/v2/market/oi",
        params={"instrument_key": "NSE_EQ|INE002A01018"},
    ).mock(return_value=Response(200, json={"data": {"oi": 1000}}))

    result = await client.get_market_oi("NSE_EQ|INE002A01018")

    assert result["data"]["oi"] == 1000
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_charges_brokerage(client):
    route = respx.get(
        "https://api.upstox.com/v2/charges/brokerage",
        params={"instrument_key": "NSE_EQ|INE002A01018", "qty": "100"},
    ).mock(return_value=Response(200, json={"data": {"charges": 50}}))

    result = await client.get_charges_brokerage(
        instrument_key="NSE_EQ|INE002A01018", qty="100"
    )

    assert result["data"]["charges"] == 50
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_http_error_raises(client):
    respx.get(
        "https://api.upstox.com/v2/historical-candle/NSE_EQ|INE002A01018/1minute/2026-05-19"
    ).mock(return_value=Response(401, json={"error": "Unauthorized"}))

    with pytest.raises(Exception):
        await client.get_historical_candle("NSE_EQ|INE002A01018", date="2026-05-19")
