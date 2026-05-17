import pytest
import respx
from httpx import Response

from core.data.nse_scraper import NSEScraper


@pytest.mark.asyncio
@respx.mock
async def test_get_fo_ban_list():
    route = respx.get("https://www.nseindia.com/api/securities/ban").mock(
        return_value=Response(200, json={"data": [{"symbol": "RELIANCE"}, {"symbol": "TCS"}]})
    )
    scraper = NSEScraper()
    result = await scraper.get_fo_ban_list()
    assert result == ["RELIANCE", "TCS"]
    assert route.called
    await scraper.close()


@pytest.mark.asyncio
@respx.mock
async def test_get_fo_ban_list_http_error_returns_empty():
    route = respx.get("https://www.nseindia.com/api/securities/ban").mock(
        return_value=Response(500)
    )
    scraper = NSEScraper()
    result = await scraper.get_fo_ban_list()
    assert result == []
    assert route.called
    await scraper.close()


@pytest.mark.asyncio
@respx.mock
async def test_get_fo_ban_list_malformed_json_returns_empty():
    route = respx.get("https://www.nseindia.com/api/securities/ban").mock(
        return_value=Response(200, json={"no_data_key": []})
    )
    scraper = NSEScraper()
    result = await scraper.get_fo_ban_list()
    assert result == []
    assert route.called
    await scraper.close()


@pytest.mark.asyncio
@respx.mock
async def test_get_corporate_actions_returns_empty():
    route = respx.get("https://www.nseindia.com/api/corporates/corporateActions").mock(
        return_value=Response(200, json=[])
    )
    scraper = NSEScraper()
    result = await scraper.get_corporate_actions()
    assert result == []
    assert route.called
    await scraper.close()
