import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.scheduler.market_scheduler import MarketScheduler


@pytest.fixture
def mock_components():
    return {
        "db": AsyncMock(),
        "cache": AsyncMock(),
        "upstox": AsyncMock(),
        "l1": MagicMock(),
    }


@pytest.mark.asyncio
async def test_scheduler_init(mock_components):
    with patch("core.scheduler.market_scheduler.AsyncIOScheduler") as mock_sched_class:
        mock_sched = MagicMock()
        mock_sched_class.return_value = mock_sched
        scheduler = MarketScheduler(mock_components)
        assert scheduler.db is not None
        assert scheduler.cache is not None


@pytest.mark.asyncio
async def test_scheduler_start(mock_components):
    with patch("core.scheduler.market_scheduler.AsyncIOScheduler") as mock_sched_class:
        mock_sched = MagicMock()
        mock_sched_class.return_value = mock_sched
        scheduler = MarketScheduler(mock_components)
        scheduler.start()
        mock_sched.add_job.assert_called()
        mock_sched.start.assert_called_once()


@pytest.mark.asyncio
async def test_scheduler_shutdown(mock_components):
    with patch("core.scheduler.market_scheduler.AsyncIOScheduler") as mock_sched_class:
        mock_sched = MagicMock()
        mock_sched_class.return_value = mock_sched
        scheduler = MarketScheduler(mock_components)
        scheduler.start()
        scheduler.shutdown()
        mock_sched.shutdown.assert_called_once()
