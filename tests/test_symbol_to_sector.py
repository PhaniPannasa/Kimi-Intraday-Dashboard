"""Tests for the SYMBOL_TO_SECTOR mapping in engine/core/pipeline.py.

Phase B Fix 4 — every one of the 105 Nifty constituents in
SYMBOL_TO_INSTRUMENT_KEY must map to a valid sector key in SECTOR_INDEX_MAP
so the per-symbol L4 sector-RS lookup uses the correct sector (not Bank).
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
import polars as pl


IST = timezone(timedelta(hours=5, minutes=30))


class TestSymbolToSectorMapping:
    def test_covers_all_105_symbols(self):
        from core.pipeline import SYMBOL_TO_INSTRUMENT_KEY, SYMBOL_TO_SECTOR
        assert len(SYMBOL_TO_SECTOR) >= 105, (
            f"SYMBOL_TO_SECTOR must cover all 105 symbols, "
            f"has {len(SYMBOL_TO_SECTOR)}"
        )
        # Must be a superset of SYMBOL_TO_INSTRUMENT_KEY
        instrument_symbols = set(SYMBOL_TO_INSTRUMENT_KEY.keys())
        sector_symbols = set(SYMBOL_TO_SECTOR.keys())
        missing = instrument_symbols - sector_symbols
        assert not missing, (
            f"SYMBOL_TO_SECTOR is missing these symbols from "
            f"SYMBOL_TO_INSTRUMENT_KEY: {sorted(missing)}"
        )

    def test_every_value_is_valid_sector_index_key(self):
        from core.pipeline import SYMBOL_TO_SECTOR, SECTOR_INDEX_MAP
        valid_sectors = set(SECTOR_INDEX_MAP.keys())
        invalid = {
            sym: sec
            for sym, sec in SYMBOL_TO_SECTOR.items()
            if sec not in valid_sectors
        }
        assert not invalid, (
            f"These symbols map to sector names not in SECTOR_INDEX_MAP: "
            f"{invalid}; valid sectors are {sorted(valid_sectors)}"
        )

    def test_spot_check_canonical_mappings(self):
        from core.pipeline import SYMBOL_TO_SECTOR
        assert SYMBOL_TO_SECTOR["RELIANCE"] == "Energy"
        assert SYMBOL_TO_SECTOR["TCS"] == "IT"
        assert SYMBOL_TO_SECTOR["HDFCBANK"] == "Bank"
        assert SYMBOL_TO_SECTOR["MARUTI"] == "Auto"
        assert SYMBOL_TO_SECTOR["NTPC"] == "Energy"
        assert SYMBOL_TO_SECTOR["DRREDDY"] == "Pharma"

    def test_spot_check_grouping_decisions(self):
        """The non-obvious groupings documented in pipeline.py."""
        from core.pipeline import SYMBOL_TO_SECTOR
        # Power utilities -> Energy
        for sym in ["POWERGRID", "TATAPOWER", "ADANIPOWER",
                    "ADANIGREEN", "ADANIENSOL"]:
            assert SYMBOL_TO_SECTOR[sym] == "Energy", (
                f"Power utility {sym} should map to Energy"
            )

        # Cement -> Metal
        for sym in ["ULTRACEMCO", "AMBUJACEM", "GRASIM"]:
            assert SYMBOL_TO_SECTOR[sym] == "Metal", (
                f"Cement stock {sym} should map to Metal"
            )

        # Insurance / NBFCs -> Bank
        for sym in ["HDFCLIFE", "ICICIPRULI", "ICICIGI",
                    "SBILIFE", "BAJAJFINSV", "BAJAJHLDNG"]:
            assert SYMBOL_TO_SECTOR[sym] == "Bank", (
                f"Insurance/NBFC {sym} should map to Bank"
            )

        # Aviation -> Energy
        assert SYMBOL_TO_SECTOR["INDIGO"] == "Energy"

        # Consumer durables / paints -> FMCG
        for sym in ["ASIANPAINT", "HAVELLS", "POLYCAB"]:
            assert SYMBOL_TO_SECTOR[sym] == "FMCG", (
                f"Consumer durable {sym} should map to FMCG"
            )

        # PSU banks -> PSU Bank (not Bank)
        for sym in ["SBIN", "BANKBARODA", "CANBK", "PNB"]:
            assert SYMBOL_TO_SECTOR[sym] == "PSU Bank", (
                f"PSU bank {sym} should map to 'PSU Bank'"
            )

    def test_default_fallback_returns_bank(self):
        """Unknown symbols should fall back to Bank."""
        from core.pipeline import SYMBOL_TO_SECTOR
        assert SYMBOL_TO_SECTOR.get("NONEXISTENT_SYMBOL", "Bank") == "Bank"


class TestPipelineSectorLookupIntegration:
    """The scoring loop must use the per-symbol sector — not Bank for all."""

    def _preload_symbols(self, p, symbols):
        """Pre-load synthetic bars for each given symbol."""
        for sym in symbols:
            if sym not in p.symbol_map:
                continue
            df = pl.DataFrame({
                "close": [2500.0] * 100,
                "high": [2510.0] * 100,
                "low": [2490.0] * 100,
                "open": [2495.0] * 100,
                "volume": [10000] * 100,
            })
            p.aggregator.pre_load(sym, df)

    @pytest.mark.asyncio
    async def test_different_sectors_receive_different_sector_data(self):
        """RELIANCE (Energy) and TCS (IT) and HDFCBANK (Bank) must each
        look up their own sector's data from real_sector_data, not Bank.

        We patch L5.compute to capture the sector_data dict that each
        symbol receives, then assert RELIANCE and TCS got distinct sector
        dicts when real_sector_data has both Energy and IT populated.
        """
        from core.pipeline import PipelineOrchestrator, SYMBOL_TO_SECTOR

        p = PipelineOrchestrator()
        # Pre-load bars only for the three test symbols so the scoring loop
        # processes only them.
        self._preload_symbols(p, ["RELIANCE", "TCS", "HDFCBANK"])

        # Sentinel sector_data dicts per sector so we can prove each symbol
        # picked up its own sector's entry.
        energy_entry = {"sector": "Energy", "rank": 1, "tailwind": True}
        it_entry = {"sector": "IT", "rank": 2, "tailwind": True}
        bank_entry = {"sector": "Bank", "rank": 3, "tailwind": False}

        captured: dict[str, dict] = {}

        original_compute = p.l5.compute

        def capture_compute(signals, regime, sector_data, oi_data):
            sym = signals.get("symbol") or signals.get("instrument_key", "")
            # signals dict carries "symbol" key (see _extract_l3_signals).
            captured[sym] = sector_data
            return original_compute(signals, regime, sector_data, oi_data)

        # Make the orchestrator's REST get_historical_candle return a tiny
        # OHLCV payload for every call. Then we inject real_sector_data by
        # patching rank_sectors so we can control the sector data without
        # depending on the index feed wiring.
        with patch.object(
            p.upstox_rest, "get_historical_candle", new_callable=AsyncMock
        ) as mock_hist, patch(
            "core.pipeline.rank_sectors"
        ) as mock_rank_sectors, patch.object(
            p.l5, "compute", side_effect=capture_compute
        ):
            mock_hist.return_value = {
                "data": {
                    "candles": [
                        ["2026-05-18T09:15:00+05:30",
                         2500, 2510, 2490, 2505, 10000],
                        ["2026-05-18T09:16:00+05:30",
                         2505, 2515, 2495, 2510, 11000],
                        ["2026-05-18T09:17:00+05:30",
                         2510, 2520, 2500, 2515, 12000],
                        ["2026-05-18T09:18:00+05:30",
                         2515, 2525, 2505, 2520, 13000],
                        ["2026-05-18T09:19:00+05:30",
                         2520, 2530, 2510, 2525, 14000],
                    ]
                }
            }
            mock_rank_sectors.return_value = [
                energy_entry, it_entry, bank_entry,
            ]

            await p._run_live_cycle()

        # We expect at least RELIANCE, TCS, HDFCBANK to have been scored.
        # Their captured sector_data should match each one's mapped sector.
        assert "RELIANCE" in captured, "RELIANCE should have been scored"
        assert "TCS" in captured, "TCS should have been scored"
        assert "HDFCBANK" in captured, "HDFCBANK should have been scored"

        # RELIANCE -> Energy
        assert captured["RELIANCE"] == energy_entry, (
            f"RELIANCE should receive Energy sector data, "
            f"got {captured['RELIANCE']}"
        )
        # TCS -> IT
        assert captured["TCS"] == it_entry, (
            f"TCS should receive IT sector data, got {captured['TCS']}"
        )
        # HDFCBANK -> Bank
        assert captured["HDFCBANK"] == bank_entry, (
            f"HDFCBANK should receive Bank sector data, "
            f"got {captured['HDFCBANK']}"
        )

        # Sanity: the three sector_data dicts must be distinct
        assert captured["RELIANCE"] != captured["TCS"]
        assert captured["RELIANCE"] != captured["HDFCBANK"]
        assert captured["TCS"] != captured["HDFCBANK"]

    @pytest.mark.asyncio
    async def test_unmapped_sector_falls_back_to_default(self):
        """If real_sector_data lacks a symbol's sector, fall back to default."""
        from core.pipeline import PipelineOrchestrator

        p = PipelineOrchestrator()
        # Only RELIANCE preloaded -> Energy sector lookup
        self._preload_symbols(p, ["RELIANCE"])

        captured: dict[str, dict] = {}
        original_compute = p.l5.compute

        def capture_compute(signals, regime, sector_data, oi_data):
            sym = signals.get("symbol", "")
            captured[sym] = sector_data
            return original_compute(signals, regime, sector_data, oi_data)

        # rank_sectors returns NO sector data at all -> real_sector_data is
        # empty -> sector_data should default to {"rank": 6, "tailwind": False}.
        with patch.object(
            p.upstox_rest, "get_historical_candle", new_callable=AsyncMock
        ) as mock_hist, patch(
            "core.pipeline.rank_sectors"
        ) as mock_rank_sectors, patch.object(
            p.l5, "compute", side_effect=capture_compute
        ):
            mock_hist.return_value = {
                "data": {
                    "candles": [
                        ["2026-05-18T09:15:00+05:30",
                         2500, 2510, 2490, 2505, 10000],
                    ]
                }
            }
            mock_rank_sectors.return_value = []  # empty
            await p._run_live_cycle()

        assert "RELIANCE" in captured
        assert captured["RELIANCE"] == {"rank": 6, "tailwind": False}, (
            f"Empty real_sector_data should yield default fallback, "
            f"got {captured['RELIANCE']}"
        )


class TestL9SectorPersistence:
    """Regression: the sector passed to l9.on_create (which is later persisted
    to the thesis_outcomes hypertable feeding L10 edge stats) must be the
    symbol's actual sector, not the hardcoded "Bank" placeholder.

    The pre-fix code at engine/core/pipeline.py:906 read:
        "sector": "Bank",
    which contaminated every per-sector edge tier in L10 historical data.
    """

    def _preload_symbols(self, p, symbols):
        for sym in symbols:
            if sym not in p.symbol_map:
                continue
            df = pl.DataFrame({
                "close": [2500.0] * 100,
                "high": [2510.0] * 100,
                "low": [2490.0] * 100,
                "open": [2495.0] * 100,
                "volume": [10000] * 100,
            })
            p.aggregator.pre_load(sym, df)

    @pytest.mark.asyncio
    async def test_l9_on_create_receives_per_symbol_sector(self):
        """Verify l9.on_create() is invoked with sector matching
        SYMBOL_TO_SECTOR[sym] for the synthesised thesis."""
        from core.pipeline import PipelineOrchestrator, SYMBOL_TO_SECTOR
        from models.frames import ThesisCard
        from models.enums import Direction, SetupType

        p = PipelineOrchestrator()
        # Pre-load three symbols spanning three distinct sectors so a single
        # cycle exercises the per-symbol lookup at the L9 write site.
        self._preload_symbols(p, ["RELIANCE", "TCS", "HDFCBANK"])

        def fake_assemble(sym, direction, bars, pd_df, l3_df, sigs,
                          l2_flag, sector_data):
            return ThesisCard(
                thesis_id=f"test-{sym}",
                symbol=sym,
                direction=Direction.LONG,
                setup_type=SetupType.ORB_15MIN,
                trigger=2500.0,
                invalidation=2480.0,
                t1=2520.0,
                t2=2540.0,
                cost_breakdown={"total_cost_pct": 0.05},
            )

        captured_payloads = []

        async def capture_on_create(payload):
            captured_payloads.append(payload)

        with patch.object(
            p.upstox_rest, "get_historical_candle", new_callable=AsyncMock
        ) as mock_hist, patch(
            "core.pipeline.rank_sectors"
        ) as mock_rank_sectors, patch.object(
            p, "_try_assemble_thesis", side_effect=fake_assemble
        ), patch.object(
            p.l9, "on_create", side_effect=capture_on_create
        ):
            mock_hist.return_value = {
                "data": {
                    "candles": [
                        ["2026-05-18T09:15:00+05:30",
                         2500, 2510, 2490, 2505, 10000],
                        ["2026-05-18T09:16:00+05:30",
                         2505, 2515, 2495, 2510, 11000],
                        ["2026-05-18T09:17:00+05:30",
                         2510, 2520, 2500, 2515, 12000],
                        ["2026-05-18T09:18:00+05:30",
                         2515, 2525, 2505, 2520, 13000],
                        ["2026-05-18T09:19:00+05:30",
                         2520, 2530, 2510, 2525, 14000],
                    ]
                }
            }
            mock_rank_sectors.return_value = [
                {"sector": "Energy", "rank": 1, "tailwind": True},
                {"sector": "IT", "rank": 2, "tailwind": True},
                {"sector": "Bank", "rank": 3, "tailwind": False},
            ]

            await p._run_live_cycle()

        # At least one of the three symbols must have produced an L9 record.
        assert captured_payloads, (
            "l9.on_create was never called — no thesis assembled by L8 loop"
        )

        # For every captured payload, the sector MUST match SYMBOL_TO_SECTOR.
        # If any payload has sector="Bank" for a non-Bank-sector symbol, the
        # pre-fix regression has returned.
        for payload in captured_payloads:
            sym = payload["symbol"]
            expected_sector = SYMBOL_TO_SECTOR.get(sym, "Bank")
            assert payload["sector"] == expected_sector, (
                f"L9 on_create payload for {sym} got sector "
                f"{payload['sector']!r}, expected {expected_sector!r} "
                f"(this is the Phase B Fix 4b regression — "
                f"sector was hardcoded to 'Bank' before fix)"
            )
