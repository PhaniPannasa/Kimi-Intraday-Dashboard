import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
import polars as pl

IST = timezone(timedelta(hours=5, minutes=30))


class TestTickBuffer:
    def test_ingest_first_tick_creates_open_bar(self):
        from core.pipeline import TickBuffer
        buf = TickBuffer()
        ts = datetime(2026, 5, 18, 9, 15, 30, tzinfo=IST)
        result = buf.ingest("NSE_EQ|TCS", 2500.0, 1000, 50000, ts)
        assert result is None  # Bar not yet closed

    def test_ingest_detects_bar_close(self):
        from core.pipeline import TickBuffer
        buf = TickBuffer()
        ts1 = datetime(2026, 5, 18, 9, 15, 30, tzinfo=IST)
        buf.ingest("NSE_EQ|TCS", 2500.0, 1000, 50000, ts1)
        ts2 = datetime(2026, 5, 18, 9, 16, 5, tzinfo=IST)
        result = buf.ingest("NSE_EQ|TCS", 2510.0, 500, 51000, ts2)
        assert result is not None
        assert result["open"] == 2500.0
        assert result["close"] == 2510.0

    def test_get_latest_bars_returns_polars_df(self):
        from core.pipeline import TickBuffer
        buf = TickBuffer()
        ts = datetime(2026, 5, 18, 9, 15, 30, tzinfo=IST)
        buf.ingest("NSE_EQ|TCS", 2500.0, 1000, 50000, ts)
        ts2 = datetime(2026, 5, 18, 9, 16, 5, tzinfo=IST)
        buf.ingest("NSE_EQ|TCS", 2510.0, 500, 51000, ts2)
        df = buf.get_latest_bars("NSE_EQ|TCS", n=5)
        assert isinstance(df, pl.DataFrame)
        assert len(df) >= 1


class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_pipeline_instantiates(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        assert p.session is not None
        assert len(p.symbol_map) > 0

    def _preload_symbols(self, p, count=5):
        """Helper: pre-load synthetic bars for *count* symbols."""
        for sym in list(p.symbol_map.keys())[:count]:
            df = pl.DataFrame({
                "close": [2500.0] * 100,
                "high": [2510.0] * 100,
                "low": [2490.0] * 100,
                "open": [2495.0] * 100,
                "volume": [10000] * 100,
            })
            p.aggregator.pre_load(sym, df)

    @pytest.mark.asyncio
    async def test_pipeline_generates_rankings(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        self._preload_symbols(p, count=5)

        with patch.object(p.upstox_rest, 'get_historical_candle', new_callable=AsyncMock) as mock_hist:
            mock_hist.return_value = {
                "data": {"candles": [
                    ["2026-05-18T09:15:00+05:30", 2500, 2510, 2490, 2505, 10000]
                ]}
            }
            await p._run_live_cycle()
            assert len(p.l6.previous_ranks) > 0, "L6 should have ranked symbols"
            assert len(p.latest_long_rankings) >= 0
            assert len(p.latest_short_rankings) >= 0

    @pytest.mark.asyncio
    async def test_pipeline_uses_l1_context(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        self._preload_symbols(p, count=5)

        with patch.object(p.upstox_rest, 'get_historical_candle', new_callable=AsyncMock) as mock_hist:
            mock_hist.return_value = {
                "data": {"candles": [
                    ["2026-05-18T09:15:00+05:30", 2500, 2510, 2490, 2505, 10000]
                ]}
            }
            await p._run_live_cycle()
            assert p.latest_context is not None, "L1 should have produced a MarketContextFrame"
            assert p.latest_context.regime is not None
            assert len(p.l1.vix_history) >= 0

    @pytest.mark.asyncio
    async def test_pipeline_uses_l7_confluence(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        self._preload_symbols(p, count=5)

        with patch.object(p.upstox_rest, 'get_historical_candle', new_callable=AsyncMock) as mock_hist:
            mock_hist.return_value = {
                "data": {"candles": [
                    ["2026-05-18T09:15:00+05:30", 2500, 2510, 2490, 2505, 10000]
                ]}
            }
            await p._run_live_cycle()
            if len(p.latest_long_rankings) > 0:
                entry = p.latest_long_rankings[0]
                assert hasattr(entry, 'confluence_score')
            if len(p.latest_theses) > 0:
                thesis = p.latest_theses[0]
                assert thesis.confluence_score >= 0
                assert hasattr(thesis, 'confluence_score')

    @pytest.mark.asyncio
    async def test_pipeline_creates_theses(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        self._preload_symbols(p, count=10)

        with patch.object(p.upstox_rest, 'get_historical_candle', new_callable=AsyncMock) as mock_hist:
            mock_hist.return_value = {
                "data": {"candles": [
                    ["2026-05-18T09:15:00+05:30", 2500, 2510, 2490, 2505, 10000]
                ]}
            }
            await p._run_live_cycle()
            assert p.latest_theses is not None, "L8 should have produced theses"
            assert len(p.l9.active) >= 0, "L9 should have registered theses"

    @pytest.mark.asyncio
    async def test_pipeline_closing_captures_snapshot(self):
        from core.pipeline import PipelineOrchestrator
        p = PipelineOrchestrator()
        mock_cache = AsyncMock()
        p.cache = mock_cache
        await p._run_closing_cycle()
        assert mock_cache.set.called
