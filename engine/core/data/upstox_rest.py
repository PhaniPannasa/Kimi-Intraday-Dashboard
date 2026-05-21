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
        self,
        instrument_key: str,
        interval: str = "1minute",
        date: str | None = None,
    ):
        """Fetch historical candles from Upstox v2.

        ``date`` must be ``YYYY-MM-DD`` in IST. Defaults to yesterday
        (the latest completed trading day with full intraday data).
        """
        if date is None:
            from datetime import datetime as dt_utc, timedelta, timezone
            ist = timezone(timedelta(hours=5, minutes=30))
            date = (dt_utc.now(ist) - timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"/v2/historical-candle/{instrument_key}/{interval}/{date}"
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

    async def get_ltpc(self, instrument_keys: list[str]):
        """Fetch LTPC for one or more instruments.

        Upstox V3 endpoint: GET /v3/market/ltpc
        Accepts comma-separated instrument_keys as query param.
        Returns: {"data": {"NSE_INDEX|India VIX": {"ltp": 14.5, ...}, ...}}
        """
        url = "/v3/market/ltpc"
        keys_str = ",".join(instrument_keys)
        response = await self.client.get(url, params={"instrument_key": keys_str})
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


upstox_rest = UpstoxRESTClient()
