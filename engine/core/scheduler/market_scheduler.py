from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime


class MarketScheduler:
    def __init__(self, components: dict):
        self.db = components.get("db")
        self.cache = components.get("cache")
        self.upstox = components.get("upstox")
        self.l1 = components.get("l1")
        self.scheduler = AsyncIOScheduler()

    def start(self):
        self.scheduler.add_job(
            self._health_check,
            "interval",
            minutes=1,
            id="health_check"
        )
        self.scheduler.add_job(
            self._l1_refresh,
            "interval",
            minutes=5,
            id="l1_refresh"
        )
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    async def _health_check(self):
        if self.db:
            try:
                await self.db.execute("SELECT 1")
            except Exception:
                pass

    async def _l1_refresh(self):
        pass  # Stub — will be wired to real L1 computation
