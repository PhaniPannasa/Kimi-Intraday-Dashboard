import httpx


class NSEScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def get_fo_ban_list(self):
        try:
            url = "https://www.nseindia.com/api/securities/ban"
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return [item["symbol"] for item in data.get("data", [])]
        except Exception:
            return []

    async def get_corporate_actions(self):
        try:
            url = "https://www.nseindia.com/api/corporates/corporateActions"
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception:
            return []

    async def get_mwpl(self):
        """Fetch MWPL (Minimum Workable Price List) from NSE.

        MWPL restricts stocks from trading below a floor price.
        Returns list of symbols under MWPL restriction.
        """
        try:
            url = "https://www.nseindia.com/api/mwpl"
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.json() if isinstance(resp.json(), list) else []
        except Exception:
            return []

    async def close(self):
        await self.client.aclose()


nse_scraper = NSEScraper()
