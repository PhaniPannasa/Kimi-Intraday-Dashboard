"""Indian intraday cost model per system_design_final.md Section 5.8.

Rates:
  Equity Intraday (MIS):
    Brokerage: 0.03% or Rs.20/order, whichever is lower (both sides)
    STT: 0.025% (sell only)
    Exchange: 0.00297% (both)
    SEBI: Rs.10/crore = 0.0001% (both)
    Stamp: 0.003% (buy only)
    GST: 18% on (brokerage + exchange + SEBI) (both)

  Futures Intraday:
    Brokerage: Rs.20/leg flat
    STT: 0.0125% (sell)
    Exchange: 0.00173% (both)
    Stamp: 0.002% (buy)
    GST: 18% on (brokerage + exchange + SEBI)

  Slippage (Depth-Derived):
    Excellent: 5 bps normal / +8 bps SL
    Good: 10 bps / +15 bps
    Marginal: 20 bps / +25 bps
    Poor: 35 bps / +40 bps
"""

COST_RATES = {
    "equity": {
        "brokerage_pct": 0.0003,     # 0.03%
        "brokerage_cap": 20.0,       # Rs.20 per order
        "stt_pct": 0.00025,          # 0.025% sell only
        "exchange_pct": 0.0000297,   # 0.00297%
        "sebi_pct": 0.000001,        # 0.0001% (Rs.10/crore)
        "stamp_pct": 0.00003,        # 0.003% buy only
        "gst_pct": 0.18,
    },
    "futures": {
        "brokerage_flat": 20.0,      # Rs.20/leg
        "stt_pct": 0.000125,         # 0.0125% sell only
        "exchange_pct": 0.0000173,   # 0.00173%
        "sebi_pct": 0.000001,        # 0.0001%
        "stamp_pct": 0.00002,        # 0.002% buy only
        "gst_pct": 0.18,
    },
}

SLIPPAGE = {
    "Excellent": {"normal": 5, "stop": 8},
    "Good": {"normal": 10, "stop": 15},
    "Marginal": {"normal": 20, "stop": 25},
    "Poor": {"normal": 35, "stop": 40},
}

SLIPPAGE_LQS_BOUNDARIES = [
    (0.0, 0.30, "Poor"),
    (0.30, 0.55, "Marginal"),
    (0.55, 0.80, "Good"),
    (0.80, 1.00, "Excellent"),
]


def _bucket_total_slip(bucket_name: str, is_stop: bool) -> float:
    """Return total slippage in bps for a bucket, adding stop add-on when applicable."""
    slip = SLIPPAGE[bucket_name]
    total = slip["normal"]
    if is_stop:
        total += slip["stop"]
    return float(total)


def compute_slippage_continuous(lqs: float, is_stop: bool = False) -> float:
    """Return slippage in bps via linear interpolation of LQS between bucket midpoints."""
    lqs = max(0.0, min(1.0, lqs))

    for i, (lo, hi, bucket) in enumerate(SLIPPAGE_LQS_BOUNDARIES):
        if lo <= lqs <= hi:
            midpoint = (lo + hi) / 2
            bucket_slip = _bucket_total_slip(bucket, is_stop)

            if lqs <= midpoint and i > 0:
                prev_lo, prev_hi, prev_bucket = SLIPPAGE_LQS_BOUNDARIES[i - 1]
                prev_midpoint = (prev_lo + prev_hi) / 2
                prev_slip = _bucket_total_slip(prev_bucket, is_stop)
                t = (lqs - prev_midpoint) / (midpoint - prev_midpoint) if midpoint != prev_midpoint else 0
                return round(prev_slip + t * (bucket_slip - prev_slip), 1)

            elif lqs > midpoint and i < len(SLIPPAGE_LQS_BOUNDARIES) - 1:
                next_lo, next_hi, next_bucket = SLIPPAGE_LQS_BOUNDARIES[i + 1]
                next_midpoint = (next_lo + next_hi) / 2
                next_slip = _bucket_total_slip(next_bucket, is_stop)
                t = (lqs - midpoint) / (next_midpoint - midpoint) if next_midpoint != midpoint else 0
                return round(bucket_slip + t * (next_slip - bucket_slip), 1)

            return float(bucket_slip)

    return _bucket_total_slip("Good", is_stop)


def compute_brokerage_equity(entry: float, exit: float, qty: int = 100,
                              direction: str = "LONG") -> dict:
    """Compute all charges for equity intraday (MIS)."""
    r = COST_RATES["equity"]
    buy_value = entry * qty
    sell_value = exit * qty
    turnover = buy_value + sell_value

    brokerage = min(r["brokerage_cap"], buy_value * r["brokerage_pct"]) + \
                min(r["brokerage_cap"], sell_value * r["brokerage_pct"])

    # STT on sell leg only
    if direction == "LONG":
        stt = sell_value * r["stt_pct"]   # exit is sell for LONG
    else:
        stt = buy_value * r["stt_pct"]    # entry is sell for SHORT

    exchange = turnover * r["exchange_pct"]
    sebi = turnover * r["sebi_pct"]
    gst = (brokerage + exchange + sebi) * r["gst_pct"]

    # Stamp on buy leg only
    if direction == "LONG":
        stamp = buy_value * r["stamp_pct"]   # entry is buy for LONG
    else:
        stamp = sell_value * r["stamp_pct"]  # exit is buy-to-cover for SHORT

    total = brokerage + stt + exchange + sebi + gst + stamp
    return {
        "turnover": turnover,
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "sebi": round(sebi, 2),
        "gst": round(gst, 2),
        "stamp": round(stamp, 2),
        "total_cost": round(total, 2),
        "cost_pct": (total / turnover) * 100 if turnover > 0 else 0.0,
    }


def compute_brokerage_futures(entry: float, exit: float, qty: int = 100,
                               direction: str = "LONG") -> dict:
    """Compute all charges for futures intraday."""
    r = COST_RATES["futures"]
    buy_value = entry * qty
    sell_value = exit * qty
    turnover = buy_value + sell_value

    brokerage = r["brokerage_flat"] * 2  # Rs.20 per leg x 2

    if direction == "LONG":
        stt = sell_value * r["stt_pct"]
    else:
        stt = buy_value * r["stt_pct"]

    exchange = turnover * r["exchange_pct"]
    sebi = turnover * r["sebi_pct"]
    gst = (brokerage + exchange + sebi) * r["gst_pct"]

    if direction == "LONG":
        stamp = buy_value * r["stamp_pct"]
    else:
        stamp = sell_value * r["stamp_pct"]

    total = brokerage + stt + exchange + sebi + gst + stamp
    return {
        "turnover": turnover,
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "sebi": round(sebi, 2),
        "gst": round(gst, 2),
        "stamp": round(stamp, 2),
        "total_cost": round(total, 2),
        "cost_pct": (total / turnover) * 100 if turnover > 0 else 0.0,
    }


def compute_brokerage(entry: float, exit: float, qty: int = 100,
                      lot_size: int = 50, futures: bool = True,
                      direction: str = "LONG") -> dict:
    """Dispatch to equity or futures cost computation."""
    if futures:
        return compute_brokerage_futures(entry, exit, qty, direction)
    return compute_brokerage_equity(entry, exit, qty, direction)


def compute_slippage(liquidity_quality: str | float, is_stop: bool = False) -> float:
    """Return slippage in basis points.

    Accepts string bucket name ("Excellent"/"Good"/"Marginal"/"Poor")
    for backward compatibility, or a float LQS value (0.0-1.0) for continuous
    interpolation.
    """
    if isinstance(liquidity_quality, (int, float)):
        return compute_slippage_continuous(float(liquidity_quality), is_stop)
    return _bucket_total_slip(liquidity_quality, is_stop)


def compute_net_rr(trigger: float, t1: float, invalidation: float,
                   cost_pct: float, stop_slippage_pct: float) -> dict:
    """Compute Net R:R per spec Section 5.8.

    Net reward = |T1 - Trigger| - (cost_pct/100 * Trigger)
    Net risk = |Trigger - Invalidation| + (stop_slippage_pct/100 * Trigger)
    Net R:R = Net reward / Net risk
    """
    cost_factor = cost_pct / 100.0
    slip_factor = stop_slippage_pct / 100.0

    gross_reward = abs(t1 - trigger)
    gross_risk = abs(trigger - invalidation)

    net_reward = gross_reward - (cost_factor * trigger)
    net_risk = gross_risk + (slip_factor * trigger)

    net_rr = net_reward / net_risk if net_risk > 0 else 0.0
    gross_rr = gross_reward / gross_risk if gross_risk > 0 else 0.0

    return {
        "gross_rr": round(gross_rr, 2),
        "net_rr": round(net_rr, 2),
        "net_reward": round(net_reward, 2),
        "net_risk": round(net_risk, 2),
        "cost_pct": round(cost_pct, 3),
    }


def compute_grade(net_rr: float) -> str:
    """ >= 1.5: ATTRACTIVE, 1.0-1.5: MARGINAL, < 1.0: UNATTRACTIVE"""
    if net_rr >= 1.5:
        return "ATTRACTIVE"
    elif net_rr >= 1.0:
        return "MARGINAL"
    return "UNATTRACTIVE"
