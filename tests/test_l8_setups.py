# tests/test_l8_setups.py
import pytest
from models.enums import Direction, SetupType, Regime
from engine.layers.l8_setups.orb_15 import assemble_orb_15
from engine.layers.l8_setups.vwap_reclaim import assemble_vwap_reclaim
from engine.layers.l8_setups.supertrend_pullback import assemble_supertrend_pullback
from engine.layers.l8_setups.mean_reversion import assemble_mean_reversion
from engine.layers.l8_setups.first_hour_breakout import assemble_first_hour_breakout
from engine.layers.l8_setups.cpr_breakout import assemble_cpr_breakout


class TestORB15Setup:
    def test_long_thesis_levels(self):
        t = assemble_orb_15("RELIANCE", Direction.LONG, orb_high=2500, orb_low=2480, vwap=2490, pdh=2520, pdl=2470)
        assert t.direction == Direction.LONG
        assert t.setup_type == SetupType.ORB_15MIN
        assert t.trigger == 2500.05
        assert t.invalidation == max(2480, 2490 * 0.995)
        assert t.t2 == 2520

    def test_short_t2_is_pdl(self):
        t = assemble_orb_15("RELIANCE", Direction.SHORT, orb_high=2500, orb_low=2480, vwap=2490, pdh=2520, pdl=2470)
        assert t.direction == Direction.SHORT
        assert t.trigger == 2479.95
        assert t.t2 == 2470


class TestVWAPReclaim:
    def test_long_levels(self):
        t = assemble_vwap_reclaim("SBIN", Direction.LONG, vwap=600, atr=10)
        assert t.trigger == 600.05
        assert t.invalidation == 600 - 8
        assert t.t1 == 600 + 15
        assert t.t2 == 600 + 25

    def test_short_levels(self):
        t = assemble_vwap_reclaim("SBIN", Direction.SHORT, vwap=600, atr=10)
        assert t.trigger == 599.95
        assert t.invalidation == 600 + 8
        assert t.t1 == 600 - 15


class TestSupertrendPullback:
    def test_long_levels(self):
        t = assemble_supertrend_pullback("INFY", Direction.LONG, supertrend_line=1500, atr=20)
        assert t.trigger == 1500.05
        assert t.invalidation == 1500 - 10
        assert t.t1 == 1500 + 30

    def test_short_levels(self):
        t = assemble_supertrend_pullback("INFY", Direction.SHORT, supertrend_line=1500, atr=20)
        assert t.trigger == 1499.95
        assert t.invalidation == 1500 + 10


class TestMeanReversion:
    def test_long_t1_respects_min_reward(self):
        t = assemble_mean_reversion("TATAMOTORS", Direction.LONG,
            bb_lower_2sigma=450, bb_upper_2sigma=500,
            bb_lower_25sigma=445, bb_upper_25sigma=505,
            bb_lower_1sigma=460, bb_upper_1sigma=490,
            vwap=455,
        )
        min_t1 = 449.95 + 0.6 * abs(449.95 - 445)
        assert t.t1 >= min_t1
        assert t.preferred_regime == Regime.RANGE_BOUND


class TestFirstHourBreakout:
    def test_long_levels(self):
        t = assemble_first_hour_breakout("HDFC", Direction.LONG,
            fh_high=1650, fh_low=1630, pdh=1670, pdl=1620)
        fh_range = 20
        assert t.trigger == 1650.05
        assert t.invalidation == 1630 - 0.3 * fh_range
        assert t.t1 == 1650.05 + fh_range
        assert t.t2 == 1670


class TestCPRBreakout:
    def test_long_levels(self):
        t = assemble_cpr_breakout("ICICIBANK", Direction.LONG,
            tc=950, bc=945, r1=960, r2=970, s1=940, s2=930)
        assert t.trigger == 950.05
        cpr_width = 5
        assert t.invalidation == 945 - 0.2 * cpr_width
        assert t.t1 == 960
        assert t.t2 == 970


class TestAllSetupsProduceValidCards:
    @pytest.mark.parametrize("assembler, kwargs", [
        (assemble_orb_15, {"symbol": "X", "direction": Direction.LONG, "orb_high": 100, "orb_low": 90, "vwap": 95, "pdh": 105, "pdl": 85}),
        (assemble_vwap_reclaim, {"symbol": "X", "direction": Direction.LONG, "vwap": 100, "atr": 5}),
        (assemble_supertrend_pullback, {"symbol": "X", "direction": Direction.LONG, "supertrend_line": 100, "atr": 5}),
        (assemble_mean_reversion, {"symbol": "X", "direction": Direction.LONG, "bb_lower_2sigma": 90, "bb_upper_2sigma": 110, "bb_lower_25sigma": 87, "bb_upper_25sigma": 113, "bb_lower_1sigma": 93, "bb_upper_1sigma": 107, "vwap": 100}),
        (assemble_first_hour_breakout, {"symbol": "X", "direction": Direction.LONG, "fh_high": 102, "fh_low": 98, "pdh": 105, "pdl": 95}),
        (assemble_cpr_breakout, {"symbol": "X", "direction": Direction.LONG, "tc": 100, "bc": 97, "r1": 105, "r2": 110, "s1": 95, "s2": 90}),
    ])
    def test_card_has_positive_risk(self, assembler, kwargs):
        t = assembler(**kwargs)
        risk = abs(t.trigger - t.invalidation)
        assert risk > 0, f"{assembler.__name__} produced zero-risk thesis"
