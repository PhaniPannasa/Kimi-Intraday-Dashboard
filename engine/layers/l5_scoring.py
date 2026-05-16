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


def compute_f1_trend(ema_aligned: bool, supertrend_bull: bool, adx: float) -> float:
    score = 0
    if ema_aligned:
        score += 40
    if supertrend_bull:
        score += 35
    if adx > 25:
        score += 25
    return min(score, 100)


def compute_f2_momentum(rsi: float, macd_div: bool, roc_z: float) -> float:
    score = 0
    if 40 < rsi < 70:
        score += 30
    if macd_div:
        score += 35
    score += max(0, min(35, 35 + roc_z * 10))
    return min(score, 100)


def compute_f3_volume(above_vwap: bool, vol_z: float, vol_confirm: bool) -> float:
    score = 0
    if above_vwap:
        score += 40
    score += max(0, min(30, vol_z * 10))
    if vol_confirm:
        score += 30
    return min(score, 100)


def compute_f4_volpos(bb_pos: float, atr_pctile: float, dist_to_sup: float) -> float:
    score = max(0, 100 - bb_pos * 100)
    score += max(0, min(50, dist_to_sup * 100))
    score = min(score, 100)
    return score


def compute_f5_sector(rs_rank: int) -> float:
    return max(0, 100 - (rs_rank - 1) * 10)


def compute_f6_oi(oi_class: str, direction: str) -> float:
    if direction == "LONG" and oi_class == "Long Buildup":
        return 100
    if direction == "SHORT" and oi_class == "Short Buildup":
        return 100
    return 50


def compute_f7_posrng(pos_52w: float, cpr_dist: float) -> float:
    score = max(0, 100 - pos_52w * 100)
    score += max(0, min(50, cpr_dist * 100))
    return min(score, 100)


def compute_raw_score(factors: dict, regime: str) -> float:
    weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS[Regime.RANGE_BOUND.value])
    raw = sum(factors.get(k, 0) * weights.get(k, 0) for k in weights)
    return raw


class L5Scoring:
    def compute(self, symbol_data: dict, regime: str, sector_data: dict, oi_data: dict) -> dict:
        f1 = compute_f1_trend(
            symbol_data.get("ema_aligned", False),
            symbol_data.get("supertrend_bull", False),
            symbol_data.get("adx", 0),
        )
        f2 = compute_f2_momentum(
            symbol_data.get("rsi", 50),
            symbol_data.get("macd_divergence", False),
            symbol_data.get("roc_z", 0),
        )
        f3 = compute_f3_volume(
            symbol_data.get("above_vwap", False),
            symbol_data.get("vol_z", 0),
            symbol_data.get("vol_confirm", False),
        )
        f4 = compute_f4_volpos(
            symbol_data.get("bb_position", 0.5),
            symbol_data.get("atr_pctile", 0.5),
            symbol_data.get("dist_to_support", 0),
        )
        f5 = compute_f5_sector(sector_data.get("rank", 6))
        f6 = compute_f6_oi(
            oi_data.get("classification", "Neutral"),
            symbol_data.get("direction", "LONG"),
        )
        f7 = compute_f7_posrng(
            symbol_data.get("pos_52w", 0.5),
            symbol_data.get("cpr_dist", 0),
        )

        factors = {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "f6": f6, "f7": f7}
        raw = compute_raw_score(factors, regime)

        modifiers = 0
        if symbol_data.get("fo_ban"):
            modifiers += MODIFIERS["fo_ban"]
        if symbol_data.get("earnings"):
            modifiers += MODIFIERS["earnings"]
        if sector_data.get("tailwind"):
            modifiers += MODIFIERS["strong_sector"]
        if sector_data.get("headwind"):
            modifiers += MODIFIERS["weak_sector"]

        final = max(0, min(100, raw + modifiers))
        if symbol_data.get("direction") == "SHORT":
            final = final * 0.92

        return {
            "symbol": symbol_data["symbol"],
            "score": final,
            "factors": factors,
            "modifiers": modifiers,
        }
