import pytest
from core.scheduler.market_scheduler import MarketScheduler


def test_scheduler_init():
    s = MarketScheduler()
    assert s.scheduler is not None


@pytest.mark.asyncio
async def test_scheduler_registers_and_starts():
    s = MarketScheduler()
    async def dummy():
        pass
    s.register_job("test", dummy, trigger="interval", seconds=1)
    s.start()
    assert s.get_job_count() == 1
    s.shutdown()
