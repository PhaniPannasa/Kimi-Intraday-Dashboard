# tests/test_l5_direction.py
from engine.layers.l5_scoring import (
    compute_f1_trend,
    compute_f2_momentum,
    compute_f3_volume,
    compute_f4_volpos,
    compute_f5_sector,
    compute_f6_oi,
    compute_f7_posrng,
    compute_raw_score,
    L5Scoring,
    REGIME_WEIGHTS,
    MODIFIERS,
)
from models.enums import Regime


class TestF1TrendDirection:
    def test_long_bullish_alignment_scores_high(self):
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=True, adx=30, direction="LONG")
        assert score >= 85

    def test_short_bearish_alignment_scores_high(self):
        score = compute_f1_trend(ema_aligned=False, supertrend_bull=False, adx=30, direction="SHORT")
        assert score >= 85

    def test_long_mixed_gives_partial(self):
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=False, adx=20, direction="LONG")
        assert score == 10

    def test_short_mixed_gives_partial(self):
        score = compute_f1_trend(ema_aligned=True, supertrend_bull=False, adx=20, direction="SHORT")
        assert score == 60


class TestF2MomentumDirection:
    def test_long_strong_momentum_scores_high(self):
        score = compute_f2_momentum(rsi=55, macd_div=True, roc_z=1.5, direction="LONG")
        assert score > 70

    def test_short_inverted_momentum_scores_high(self):
        score = compute_f2_momentum(rsi=35, macd_div=True, roc_z=-2.0, direction="SHORT")
        assert score > 70

    def test_long_rsi_overbought_penalized(self):
        score = compute_f2_momentum(rsi=75, macd_div=False, roc_z=0, direction="LONG")
        assert score <= 35

    def test_short_rsi_oversold_penalized(self):
        score = compute_f2_momentum(rsi=25, macd_div=False, roc_z=0, direction="SHORT")
        assert score <= 35


class TestF3VolumeDirection:
    def test_long_above_vwap_scores_high(self):
        score = compute_f3_volume(above_vwap=True, vol_z=3.0, vol_confirm=True, direction="LONG")
        assert score == 95

    def test_short_below_vwap_scores_high(self):
        score = compute_f3_volume(above_vwap=False, vol_z=3.0, vol_confirm=True, direction="SHORT")
        assert score == 95

    def test_long_below_vwap_loses_40(self):
        score = compute_f3_volume(above_vwap=False, vol_z=0, vol_confirm=False, direction="LONG")
        assert score == 0


class TestF4VolPosDirection:
    def test_long_near_support_scores_high(self):
        score = compute_f4_volpos(bb_pos=0.1, atr_pctile=0.2, dist_to_sup=0.03, direction="LONG")
        assert score > 80

    def test_short_near_resistance_scores_high(self):
        score = compute_f4_volpos(bb_pos=0.9, atr_pctile=0.8, dist_to_res=0.03, direction="SHORT")
        assert score > 80

    def test_long_high_bb_pos_penalized(self):
        score = compute_f4_volpos(bb_pos=0.95, atr_pctile=0.5, dist_to_sup=0.0, direction="LONG")
        assert score < 10


class TestF5SectorDirection:
    def test_long_strong_sector_scores_high(self):
        score = compute_f5_sector(rs_rank=1, direction="LONG")
        assert score == 100

    def test_short_weak_sector_scores_high(self):
        score = compute_f5_sector(rs_rank=11, direction="SHORT")
        assert score == 100

    def test_long_weak_sector_scores_low(self):
        score = compute_f5_sector(rs_rank=11, direction="LONG")
        assert score == 0

    def test_short_strong_sector_scores_low(self):
        score = compute_f5_sector(rs_rank=1, direction="SHORT")
        assert score == 0


class TestF7PosRngDirection:
    def test_long_bottom_20pct_scores_high(self):
        score = compute_f7_posrng(pos_52w=0.1, cpr_dist=0.02, direction="LONG")
        assert score >= 90

    def test_short_top_20pct_scores_high(self):
        score = compute_f7_posrng(pos_52w=0.9, cpr_dist=0.02, direction="SHORT")
        assert score >= 90

    def test_long_top_80pct_scores_low(self):
        score = compute_f7_posrng(pos_52w=0.85, cpr_dist=0.0, direction="LONG")
        assert score < 20

    def test_short_bottom_20pct_scores_low(self):
        score = compute_f7_posrng(pos_52w=0.1, cpr_dist=0.0, direction="SHORT")
        assert score < 20


class TestCollinearityRemoved:
    def test_f1_ema_aligned_does_nothing(self):
        score_with_ema = compute_f1_trend(ema_aligned=True, supertrend_bull=True, adx=30, direction="LONG")
        score_without_ema = compute_f1_trend(ema_aligned=False, supertrend_bull=True, adx=30, direction="LONG")
        assert score_with_ema == score_without_ema

    def test_f3_vol_confirm_does_nothing(self):
        score_with_confirm = compute_f3_volume(above_vwap=True, vol_z=1.0, vol_confirm=True, direction="LONG")
        score_without_confirm = compute_f3_volume(above_vwap=True, vol_z=1.0, vol_confirm=False, direction="LONG")
        assert score_with_confirm == score_without_confirm


class TestL5ScoringIntegration:
    def test_liquidity_multiplier_applied(self):
        scorer = L5Scoring()
        data = {
            "symbol": "RELIANCE", "direction": "LONG",
            "ema_aligned": True, "supertrend_bull": True, "adx": 30,
            "rsi": 55, "macd_divergence": True, "roc_z": 1.0,
            "above_vwap": True, "vol_z": 1.0, "vol_confirm": True,
            "bb_position": 0.2, "atr_pctile": 0.3, "dist_to_support": 0.02,
            "pos_52w": 0.2, "cpr_dist": 0.01,
            "fo_ban": False, "earnings": False,
            "liquidity_multiplier": 0.85,
        }
        sector = {"rank": 1, "tailwind": False, "headwind": False}
        oi = {"classification": "Long Buildup"}
        result = scorer.compute(data, "Trending-Up", sector, oi)
        assert result["score"] < 90

    def test_stale_data_freezes_score(self):
        scorer = L5Scoring()
        data = {"symbol": "X", "direction": "LONG", "stale_data": True,
                "ema_aligned": True, "supertrend_bull": True, "adx": 30,
                "rsi": 55, "macd_divergence": False, "roc_z": 0,
                "above_vwap": True, "vol_z": 0, "vol_confirm": False,
                "bb_position": 0.5, "atr_pctile": 0.5, "dist_to_support": 0,
                "pos_52w": 0.5, "cpr_dist": 0,
                "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0}
        sector = {"rank": 6}
        oi = {"classification": "Neutral"}
        result1 = scorer.compute(data, "Trending-Up", sector, oi)
        result2 = scorer.compute(data, "Trending-Up", sector, oi)
        assert result1["score"] == result2["score"]

    def test_index_change_modifier_applied(self):
        scorer = L5Scoring()
        data = {"symbol": "X", "direction": "LONG", "index_change": True,
                "ema_aligned": True, "supertrend_bull": True, "adx": 30,
                "rsi": 55, "macd_divergence": False, "roc_z": 0,
                "above_vwap": True, "vol_z": 0, "vol_confirm": False,
                "bb_position": 0.5, "atr_pctile": 0.5, "dist_to_support": 0,
                "pos_52w": 0.5, "cpr_dist": 0,
                "fo_ban": False, "earnings": False, "liquidity_multiplier": 1.0}
        sector = {"rank": 6}
        oi = {"classification": "Neutral"}
        result = scorer.compute(data, "Trending-Up", sector, oi)
        assert result["modifiers"] == -2
