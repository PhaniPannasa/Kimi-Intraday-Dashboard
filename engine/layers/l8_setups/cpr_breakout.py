"""CPR Breakout setup.

Trigger: Break above TC + volume (long) / below BC + volume (short)
Invalidation: BC - 0.2 * CPR Width (long) / TC + 0.2 * CPR Width (short)
T1: R1 Floor Pivot (long) / S1 Floor Pivot (short)
T2: R2 Floor Pivot (long) / S2 Floor Pivot (short)
Valid Window: After 9:45 AM
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_cpr_breakout(
    symbol: str,
    direction: Direction,
    tc: float,
    bc: float,
    r1: float,
    r2: float,
    s1: float,
    s2: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    cpr_width = abs(tc - bc)

    if direction == Direction.LONG:
        trigger = tc + tick_size
        invalidation = bc - 0.2 * cpr_width
        t1 = r1
        t2 = r2
        regime = Regime.TRENDING_UP
    else:
        trigger = bc - tick_size
        invalidation = tc + 0.2 * cpr_width
        t1 = s1
        t2 = s2
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.CPR_BREAKOUT,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
