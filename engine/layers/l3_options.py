"""Options-derived signals for F&O stocks."""
import numpy as np
import math


def compute_iv_percentile(current_iv: float, iv_history: list[float]) -> float:
    if not iv_history:
        return 0.5
    below = sum(1 for v in iv_history if v < current_iv)
    return below / len(iv_history)


def compute_expected_range(atm: float, iv: float, days: int = 1) -> dict:
    expected_move = atm * iv / math.sqrt(252 / days)
    return {"expected_move": round(expected_move, 2), "upper": round(atm + expected_move, 2), "lower": round(atm - expected_move, 2)}


def compute_pcr_zscore(current_pcr: float, pcr_history: list[float]) -> float:
    if len(pcr_history) < 2:
        return 0.0
    mean = np.mean(pcr_history)
    std = np.std(pcr_history)
    return (current_pcr - mean) / std if std != 0 else 0.0


def compute_rv_iv_ratio(realized_vol: float, iv: float) -> float:
    return realized_vol / iv if iv != 0 else 1.0


def classify_oi(price_change_pct: float, oi_change_pct: float) -> str:
    if price_change_pct > 0.5 and oi_change_pct > 2:
        return "Long Buildup"
    elif price_change_pct < -0.5 and oi_change_pct > 2:
        return "Short Buildup"
    elif price_change_pct < -0.5 and oi_change_pct < -2:
        return "Long Unwinding"
    elif price_change_pct > 0.5 and oi_change_pct < -2:
        return "Short Covering"
    return "Neutral"
