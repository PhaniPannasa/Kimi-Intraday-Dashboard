import uuid
from datetime import datetime, timedelta, timezone
from models.frames import ThesisCard
from models.enums import SetupType, Direction, Regime, ActionabilityTier


def setup_orb_15(
    symbol: str,
    direction: str,
    orb_high: float,
    orb_low: float,
    vwap: float,
    pdh: float,
) -> ThesisCard:
    trigger = orb_high + 0.05 if direction == "LONG" else orb_low - 0.05

    if direction == "LONG":
        invalidation = max(orb_low, vwap * 0.995)
    else:
        invalidation = min(orb_high, vwap * 1.005)

    orb_range = orb_high - orb_low
    if direction == "LONG":
        t1 = trigger + 1.5 * orb_range
    else:
        t1 = trigger - 1.5 * orb_range

    t2 = pdh  # previous day high for both directions

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=Direction(direction),
        setup_type=SetupType.ORB_15MIN,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=datetime.now(timezone.utc) + timedelta(hours=2),
    )


class L8Thesis:
    def assemble(
        self,
        symbol: str,
        direction: str,
        orb_high: float,
        orb_low: float,
        vwap: float,
        pdh: float,
        confluence_score: int = 0,
    ) -> ThesisCard:
        thesis = setup_orb_15(symbol, direction, orb_high, orb_low, vwap, pdh)
        thesis.confluence_score = confluence_score
        risk = abs(thesis.trigger - thesis.invalidation)
        reward = abs(thesis.t1 - thesis.trigger)
        thesis.gross_rr = round(reward / risk, 2) if risk > 0 else 0
        thesis.net_rr = round(thesis.gross_rr * 0.9, 2)  # approximating costs

        if thesis.net_rr >= 1.5:
            thesis.grade = "ATTRACTIVE"
        elif thesis.net_rr >= 1.0:
            thesis.grade = "MARGINAL"
        else:
            thesis.grade = "UNATTRACTIVE"

        return thesis


def compute_brokerage(entry: float, exit: float, qty: int = 100,
                      lot_size: int = 50, futures: bool = True,
                      direction: str = "LONG") -> dict:
    turnover = entry * qty + exit * qty
    brokerage = min(20, turnover * 0.0001)
    stt = turnover * (0.00025 if futures else 0.001)
    exchange_txn = turnover * 0.0000345
    gst = brokerage * 0.18
    sebi = turnover * 0.000001
    stamp = turnover * 0.00002
    total = brokerage + stt + exchange_txn + gst + sebi + stamp
    return {
        "turnover": turnover,
        "brokerage": brokerage,
        "stt": stt,
        "exchange_txn": exchange_txn,
        "gst": gst,
        "sebi": sebi,
        "stamp": stamp,
        "total_cost": total,
        "cost_pct": (total / turnover) * 100
    }


def compute_time_decay(time_remaining_min: int) -> float:
    import math
    if time_remaining_min <= 0:
        return 0.6
    return 1.0 - math.exp(-time_remaining_min / 30)


class L8CostModel:
    def apply(self, thesis_data: dict) -> dict:
        entry = thesis_data["trigger"]
        exit_price = thesis_data["t1"]
        qty = thesis_data.get("qty", 100)
        lot_size = thesis_data.get("lot_size", 50)
        futures = thesis_data.get("futures", True)
        direction = thesis_data.get("direction", "LONG")
        time_remaining = thesis_data.get("time_remaining_min", 60)

        costs = compute_brokerage(entry, exit_price, qty, lot_size, futures, direction)
        time_mult = compute_time_decay(time_remaining)

        risk = abs(entry - thesis_data["invalidation"])
        reward = abs(exit_price - entry)
        gross_rr = reward / risk if risk > 0 else 0
        net_rr = gross_rr * (1 - costs["cost_pct"] / 100)
        adjusted_rr = net_rr * time_mult

        return {
            "gross_rr": round(gross_rr, 2),
            "net_rr": round(net_rr, 2),
            "adjusted_rr": round(adjusted_rr, 2),
            "cost_pct": round(costs["cost_pct"], 3),
            "time_decay_multiplier": round(time_mult, 3),
            "cost_details": costs
        }
