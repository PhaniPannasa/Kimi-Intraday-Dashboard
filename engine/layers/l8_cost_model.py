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


def compute_slippage(liquidity_quality: str, is_stop: bool = False) -> int:
    """Return slippage in basis points for a given liquidity bucket.

    For stop orders, the total slippage is normal + stop add-on.
    """
    bucket = SLIPPAGE.get(liquidity_quality, SLIPPAGE["Good"])
    normal = bucket["normal"]
    if is_stop:
        return normal + bucket["stop"]
    return normal


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
