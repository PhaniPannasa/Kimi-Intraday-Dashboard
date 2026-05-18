"""Supertrend Pullback setup.

Trigger: Pullback touches ST line from above (long) / below (short)
Invalidation: ST line - 0.5 * ATR (long) / ST line + 0.5 * ATR (short)
T1: ST line + 1.5 * ATR (long) / ST line - 1.5 * ATR (short)
T2: ST line + 2.5 * ATR (long) / ST line - 2.5 * ATR (short)
Valid Window: Any (while ST direction matches)
Preferred Regime: Trending-Up / Trending-Down
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_supertrend_pullback(
    symbol: str,
    direction: Direction,
    supertrend_line: float,
    atr: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = supertrend_line + tick_size
        invalidation = supertrend_line - 0.5 * atr
        t1 = supertrend_line + 1.5 * atr
        t2 = supertrend_line + 2.5 * atr
        regime = Regime.TRENDING_UP
    else:
        trigger = supertrend_line - tick_size
        invalidation = supertrend_line + 0.5 * atr
        t1 = supertrend_line - 1.5 * atr
        t2 = supertrend_line - 2.5 * atr
        regime = Regime.TRENDING_DOWN

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.SUPERTREND_PULLBACK,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
