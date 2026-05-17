import pytest
from unittest.mock import AsyncMock, MagicMock

from db.timescale import TimescaleDB


@pytest.mark.asyncio
async def test_timescale_execute_calls_pool():
    ts = TimescaleDB()
    ts.pool = MagicMock()
    mock_conn = AsyncMock()
    ts.pool.acquire.return_value.__aenter__.return_value = mock_conn
    await ts.execute("SELECT 1")
    mock_conn.execute.assert_called_once_with("SELECT 1")
