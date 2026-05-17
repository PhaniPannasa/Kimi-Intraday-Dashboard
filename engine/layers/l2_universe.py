from models.frames import MarketContextFrame
from typing import Optional


def compute_liquidity_quality_score(
    depth_lakhs: float,
    spread_pct: float,
    turnover_crores: float,
    all_depths: list,
    all_spreads: list,
    all_turnovers: list,
) -> float:
    def percentile_rank(value, distribution):
        if not distribution:
            return 0.5
        below = sum(1 for v in distribution if v < value)
        return below / len(distribution)

    d_norm = percentile_rank(depth_lakhs, all_depths)
    s_norm = 1 - percentile_rank(spread_pct, all_spreads)
    t_norm = percentile_rank(turnover_crores, all_turnovers)
    return 0.4 * d_norm + 0.35 * s_norm + 0.25 * t_norm


def bucket_lqs(lqs: float) -> str:
    if lqs >= 0.80:
        return "Excellent"
    elif lqs >= 0.55:
        return "Good"
    elif lqs >= 0.30:
        return "Marginal"
    return "Poor"


class L2Universe:
    def enrich(
        self,
        symbol: str,
        instrument_key: str,
        fo_eligible: bool = True,
        fo_ban: bool = False,
        mwpl: str = "None",
        earnings: str = "None",
        lqs: float = 0.5,
    ) -> dict:
        return {
            "symbol": symbol,
            "instrument_key": instrument_key,
            "fo_eligible": fo_eligible,
            "fo_ban": fo_ban,
            "mwpl_proximity": mwpl,
            "circuit_proximity": "None",
            "earnings_flag": earnings,
            "index_change": "None",
            "stale_data": False,
            "liquidity_quality": bucket_lqs(lqs),
            "shortability": "FUTURES_OPTIONS" if fo_eligible else "CASH_ONLY",
        }
