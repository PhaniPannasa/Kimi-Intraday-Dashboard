import numpy as np


def check_strong_close(close: float, high: float, low: float, direction: str) -> bool:
    range_val = high - low
    if range_val == 0:
        return False
    position = (close - low) / range_val
    if direction == "LONG":
        return position >= 0.67
    return position <= 0.33


def check_volume_confirm(current_vol: float, median_vol: float, is_opening: bool = False) -> bool:
    threshold = 2.0 if is_opening else 1.5
    return current_vol >= threshold * median_vol


def check_non_exhaustion(bar_range: float, median_range: float) -> bool:
    return bar_range <= 1.5 * median_range


def check_htf_alignment(ema9: float, ema20: float, ema50: float, direction: str) -> bool:
    if direction == "LONG":
        return ema9 > ema20 > ema50
    return ema9 < ema20 < ema50


def check_risk_distance(price: float, invalidation: float, atr: float) -> bool:
    return abs(price - invalidation) >= 0.5 * atr


def check_reward_distance(t1: float, price: float, invalidation: float) -> bool:
    risk = abs(price - invalidation)
    reward = abs(t1 - price)
    return reward >= 1.2 * risk


class L7Confluence:
    def compute(self, data: dict) -> int:
        score = 0
        if check_strong_close(data["close"], data["high"], data["low"], data["direction"]):
            score += 1
        if check_volume_confirm(data["volume"], data["median_volume"], data.get("is_opening", False)):
            score += 1
        if check_non_exhaustion(data["bar_range"], data["median_range"]):
            score += 1
        if check_htf_alignment(data["ema9"], data["ema20"], data["ema50"], data["direction"]):
            score += 1
        if check_risk_distance(data["price"], data["invalidation"], data["atr"]):
            score += 1
        if check_reward_distance(data["t1"], data["price"], data["invalidation"]):
            score += 1
        return score
