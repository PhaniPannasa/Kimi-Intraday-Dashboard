"""ORB 15-min setup.

Trigger: ORB High + 1 tick (long) / ORB Low - 1 tick (short)
Invalidation: max(ORB Low, VWAP-0.5%) / min(ORB High, VWAP+0.5%)
T1: Trigger + 1.5 * ORB Range
T2: PDH (long) / PDL (short)
Valid Window: Until 11:00 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_orb_15(
    symbol: str,
    direction: Direction,
    orb_high: float,
    orb_low: float,
    vwap: float,
    pdh: float,
    pdl: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    orb_range = orb_high - orb_low

    if direction == Direction.LONG:
        trigger = orb_high + tick_size
        invalidation = max(orb_low, vwap * 0.995)
        t1 = trigger + 1.5 * orb_range
        t2 = pdh
        regime = Regime.TRENDING_UP
    else:
        trigger = orb_low - tick_size
        invalidation = min(orb_high, vwap * 1.005)
        t1 = trigger - 1.5 * orb_range
        t2 = pdl
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.ORB_15MIN,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
