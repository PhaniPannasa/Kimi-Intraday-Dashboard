import pathlib

import asyncpg

from config import settings


class TimescaleDB:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
            min_size=2,
            max_size=10,
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def run_migrations(self):
        mig_dir = pathlib.Path(__file__).parent / "migrations"
        for mig_file in sorted(mig_dir.glob("*.sql")):
            sql = mig_file.read_text()
            await self.execute(sql)


db = TimescaleDB()
