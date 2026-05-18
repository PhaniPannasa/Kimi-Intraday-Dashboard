"""VWAP Reclaim setup.

Trigger: VWAP cross above + volume confirmation (long) / below (short)
Invalidation: VWAP - 0.8 * ATR (long) / VWAP + 0.8 * ATR (short)
T1: VWAP + 1.5 * ATR (long) / VWAP - 1.5 * ATR (short)
T2: VWAP + 2.5 * ATR (long) / VWAP - 2.5 * ATR (short)
Valid Window: After 9:45 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_vwap_reclaim(
    symbol: str,
    direction: Direction,
    vwap: float,
    atr: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = vwap + tick_size
        invalidation = vwap - 0.8 * atr
        t1 = vwap + 1.5 * atr
        t2 = vwap + 2.5 * atr
        regime = Regime.TRENDING_UP
    else:
        trigger = vwap - tick_size
        invalidation = vwap + 0.8 * atr
        t1 = vwap - 1.5 * atr
        t2 = vwap - 2.5 * atr
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.VWAP_RECLAIM,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
