from models.enums import Regime

REGIME_WEIGHTS = {
    Regime.TRENDING_UP.value: {"f1": 0.25, "f2": 0.20, "f3": 0.12, "f4": 0.05, "f5": 0.18, "f6": 0.12, "f7": 0.08},
    Regime.TRENDING_DOWN.value: {"f1": 0.25, "f2": 0.20, "f3": 0.12, "f4": 0.05, "f5": 0.18, "f6": 0.12, "f7": 0.08},
    Regime.RANGE_BOUND.value: {"f1": 0.08, "f2": 0.05, "f3": 0.18, "f4": 0.30, "f5": 0.15, "f6": 0.12, "f7": 0.12},
}

MODIFIERS = {
    "fo_ban": -4,
    "earnings": -6,
    "strong_sector": +3,
    "weak_sector": -3,
    "index_change": -2,
}

SHORT_WEIGHT_DISCOUNT = 0.92

REGIME_WEIGHTS_SHORT = {
    regime: {k: round(v * SHORT_WEIGHT_DISCOUNT, 4) for k, v in weights.items()}
    for regime, weights in REGIME_WEIGHTS.items()
}


def compute_f1_trend(ema_aligned: bool, supertrend_bull: bool, adx: float,
                     direction: str = "LONG") -> float:
    """F1 Trend: Supertrend direction + ADX strength.

    EMA alignment is intentionally NOT scored here — L7 Check 4 (HTF Alignment)
    independently gates on EMA(9)>EMA(20)>EMA(50).
    """
    score = 0
    if direction == "LONG":
        if supertrend_bull:
            score += 50
    else:
        if not supertrend_bull:
            score += 50
    if adx > 25:
        score += 25
    score += min(adx / 2, 25)
    return min(score, 100)


def compute_f2_momentum(rsi: float, macd_div: bool, roc_z: float,
                        direction: str = "LONG") -> float:
    """F2 Momentum: Trend-conditional for LONG, Inverted for SHORT."""
    score = 0
    if direction == "LONG":
        if 40 < rsi < 70:
            score += 30
        if macd_div:
            score += 35
        score += max(0, min(35, 35 + roc_z * 10))
    else:  # SHORT — inverted
        if 30 < rsi < 60:
            score += 30
        if macd_div:
            score += 35
        score += max(0, min(35, 35 - roc_z * 10))
    return min(score, 100)


def compute_f3_volume(above_vwap: bool, vol_z: float, vol_confirm: bool,
                      direction: str = "LONG") -> float:
    """F3 Volume: VWAP position + seasonally-adjusted volume strength.

    vol_confirm is intentionally NOT scored here — L7 Check 2 (Volume
    Confirmation) independently gates on V_adj >= 1.5× median.
    """
    score = 0
    if direction == "LONG":
        if above_vwap:
            score += 50
    else:
        if not above_vwap:
            score += 50
    score += max(0, min(50, abs(vol_z) * 15))
    return min(score, 100)


def compute_f4_volpos(bb_pos: float, atr_pctile: float,
                      dist_to_sup: float = 0.0, dist_to_res: float = 0.0,
                      direction: str = "LONG") -> float:
    """F4 Vol-Pos: Near support for LONG, Near resistance for SHORT."""
    if direction == "LONG":
        score = max(0, 100 - bb_pos * 100)
        score += max(0, min(50, dist_to_sup * 100))
    else:
        score = max(0, bb_pos * 100)
        score += max(0, min(50, dist_to_res * 100))
    return min(score, 100)


def compute_f5_sector(rs_rank: int, direction: str = "LONG") -> float:
    """F5 Sector: Strong sector for LONG, Weak sector for SHORT."""
    if direction == "LONG":
        return max(0, 100 - (rs_rank - 1) * 10)
    else:
        return max(0, (rs_rank - 1) * 10)


def compute_f6_oi(oi_class: str, direction: str) -> float:
    if direction == "LONG" and oi_class == "Long Buildup":
        return 100
    if direction == "SHORT" and oi_class == "Short Buildup":
        return 100
    return 50


def compute_f7_posrng(pos_52w: float, cpr_dist: float, direction: str = "LONG") -> float:
    """F7 Pos-Rng: Bottom 20% for LONG, Top 20% for SHORT."""
    if direction == "LONG":
        score = max(0, 100 - pos_52w * 100)
    else:
        score = max(0, pos_52w * 100)
    score += max(0, min(50, cpr_dist * 100))
    return min(score, 100)


def compute_raw_score(factors: dict, regime: str, direction: str = "LONG") -> float:
    if direction == "SHORT":
        weights = REGIME_WEIGHTS_SHORT.get(regime, REGIME_WEIGHTS_SHORT[Regime.RANGE_BOUND.value])
    else:
        weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS[Regime.RANGE_BOUND.value])
    return sum(factors.get(k, 0) * weights.get(k, 0) for k in weights)


class L5Scoring:
    def __init__(self):
        self._frozen_scores: dict[str, dict] = {}

    def compute(self, symbol_data: dict, regime: str, sector_data: dict,
                oi_data: dict) -> dict:
        symbol = symbol_data["symbol"]
        direction = symbol_data.get("direction", "LONG")

        # Stale data freeze: return frozen score if data > 30s stale
        if symbol_data.get("stale_data", False):
            frozen = self._frozen_scores.get(symbol)
            if frozen is not None:
                return {
                    "symbol": symbol,
                    "score": frozen["score"],
                    "factors": frozen["factors"],
                    "modifiers": frozen["modifiers"],
                    "frozen": True,
                }

        f1 = compute_f1_trend(
            symbol_data.get("ema_aligned", False),
            symbol_data.get("supertrend_bull", False),
            symbol_data.get("adx", 0),
            direction=direction,
        )
        f2 = compute_f2_momentum(
            symbol_data.get("rsi", 50),
            symbol_data.get("macd_divergence", False),
            symbol_data.get("roc_z", 0),
            direction=direction,
        )
        f3 = compute_f3_volume(
            symbol_data.get("above_vwap", False),
            symbol_data.get("vol_z", 0),
            symbol_data.get("vol_confirm", False),
            direction=direction,
        )
        f4 = compute_f4_volpos(
            symbol_data.get("bb_position", 0.5),
            symbol_data.get("atr_pctile", 0.5),
            symbol_data.get("dist_to_support", 0),
            symbol_data.get("dist_to_resistance", 0),
            direction=direction,
        )
        f5 = compute_f5_sector(sector_data.get("rank", 6), direction=direction)
        f6 = compute_f6_oi(oi_data.get("classification", "Neutral"), direction)
        f7 = compute_f7_posrng(
            symbol_data.get("pos_52w", 0.5),
            symbol_data.get("cpr_dist", 0),
            direction=direction,
        )

        factors = {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6, "f7": f7}
        raw = compute_raw_score(factors, regime, direction=direction)

        # Apply liquidity multiplier
        liq_mult = symbol_data.get("liquidity_multiplier", 1.0)
        s_liq = raw * liq_mult

        # Apply modifiers
        modifiers = 0
        if symbol_data.get("fo_ban"):
            modifiers += MODIFIERS["fo_ban"]
        if symbol_data.get("earnings"):
            modifiers += MODIFIERS["earnings"]
        if symbol_data.get("index_change"):
            modifiers += MODIFIERS["index_change"]
        if sector_data.get("tailwind"):
            modifiers += MODIFIERS["strong_sector"]
        if sector_data.get("headwind"):
            modifiers += MODIFIERS["weak_sector"]

        s_final = max(0, min(100, s_liq + modifiers))

        result = {
            "symbol": symbol,
            "score": s_final,
            "factors": factors,
            "modifiers": modifiers,
        }

        # Cache for potential stale-data freeze
        if not symbol_data.get("stale_data", False):
            self._frozen_scores[symbol] = result

        return result
