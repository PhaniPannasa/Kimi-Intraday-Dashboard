"""First Hour Breakout setup.

Trigger: Break above FH High after 10:15 (long) / below FH Low (short)
Invalidation: FH Low - 0.3 * FH Range (long) / FH High + 0.3 * FH Range (short)
T1: Trigger + 1.0 * FH Range (long) / Trigger - 1.0 * FH Range (short)
T2: PDH (long) / PDL (short)
Valid Window: 10:15-12:00 PM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_first_hour_breakout(
    symbol: str,
    direction: Direction,
    fh_high: float,
    fh_low: float,
    pdh: float,
    pdl: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    fh_range = fh_high - fh_low

    if direction == Direction.LONG:
        trigger = fh_high + tick_size
        invalidation = fh_low - 0.3 * fh_range
        t1 = trigger + 1.0 * fh_range
        t2 = pdh
        regime = Regime.TRENDING_UP
    else:
        trigger = fh_low - tick_size
        invalidation = fh_high + 0.3 * fh_range
        t1 = trigger - 1.0 * fh_range
        t2 = pdl
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.FIRST_HOUR_BREAKOUT,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
