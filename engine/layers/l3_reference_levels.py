"""Reference levels computed at 9:15 AM, fixed for the session."""
import numpy as np


def compute_floor_pivots(prev_high: float, prev_low: float, prev_close: float) -> dict:
    pivot = (prev_high + prev_low + prev_close) / 3
    range_hl = prev_high - prev_low
    return {
        "pivot": round(pivot, 2),
        "r1": round(2 * pivot - prev_low, 2),
        "r2": round(pivot + range_hl, 2),
        "r3": round(prev_high + 2 * (pivot - prev_low), 2),
        "s1": round(2 * pivot - prev_high, 2),
        "s2": round(pivot - range_hl, 2),
        "s3": round(prev_low - 2 * (prev_high - pivot), 2),
    }


def compute_cpr_levels(prev_high: float, prev_low: float, prev_close: float) -> dict:
    pivot = (prev_high + prev_low + prev_close) / 3
    bc = (prev_high + prev_low) / 2
    tc = pivot + (pivot - bc)
    return {"pivot": round(pivot, 2), "bc": round(bc, 2), "tc": round(tc, 2), "cpr_width": round(abs(tc - bc), 2)}


def compute_orb_levels(orb_highs: dict, orb_lows: dict) -> dict:
    result = {}
    for key, label in [("15min", "15"), ("2hour", "2h")]:
        h, l = orb_highs.get(key), orb_lows.get(key)
        if h is not None and l is not None:
            result[f"orb_{label}_high"] = h
            result[f"orb_{label}_low"] = l
            result[f"orb_{label}_range"] = round(h - l, 2)
    return result


def compute_first_hour_levels(fh_high: float, fh_low: float) -> dict:
    return {"fh_high": fh_high, "fh_low": fh_low, "fh_range": round(fh_high - fh_low, 2)}


def compute_reference_levels(
    prev_high: float, prev_low: float, prev_close: float,
    orb_high_15: float, orb_low_15: float,
    orb_high_2h: float, orb_low_2h: float,
    fh_high: float, fh_low: float,
) -> dict:
    levels = {}
    levels.update(compute_floor_pivots(prev_high, prev_low, prev_close))
    levels.update(compute_cpr_levels(prev_high, prev_low, prev_close))
    levels.update(compute_orb_levels(
        {"15min": orb_high_15, "2hour": orb_high_2h},
        {"15min": orb_low_15, "2hour": orb_low_2h},
    ))
    levels.update(compute_first_hour_levels(fh_high, fh_low))
    levels["pdh"] = prev_high
    levels["pdl"] = prev_low
    levels["pdc"] = prev_close
    return levels
