import httpx
from config import settings


class UpstoxRESTClient:
    def __init__(self):
        self.base_url = "https://api.upstox.com"
        self.headers = {
            "Authorization": f"Bearer {settings.upstox_analytics_token}",
            "Accept": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
        )

    async def get_historical_candle(
        self, instrument_key: str, interval: str = "1minute"
    ):
        url = f"/v3/historical-candle/intraday/{instrument_key}/{interval}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_option_chain(self, instrument_key: str):
        url = "/v2/option/chain"
        response = await self.client.get(url, params={"instrument_key": instrument_key})
        response.raise_for_status()
        return response.json()

    async def get_market_oi(self, instrument_key: str):
        url = "/v2/market/oi"
        response = await self.client.get(url, params={"instrument_key": instrument_key})
        response.raise_for_status()
        return response.json()

    async def get_charges_brokerage(self, **params):
        url = "/v2/charges/brokerage"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


upstox_rest = UpstoxRESTClient()
