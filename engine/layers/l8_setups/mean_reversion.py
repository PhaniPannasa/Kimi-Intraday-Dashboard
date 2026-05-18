"""Mean Reversion setup.

Trigger: Price touches lower 2-sigma BB (long) / upper 2-sigma BB (short)
Invalidation: Band breach below 2.5-sigma BB (long) / above 2.5-sigma BB (short)
T1: VWAP (min 0.6 * invalidation distance from entry)
T2: Opposite 1-sigma BB
Valid Window: Any
Preferred Regime: Range-Bound
"""
import uuid
from datetime import datetime, timezone
from models.frames import ThesisCard
from models.enums import Direction, SetupType, Regime


def assemble_mean_reversion(
    symbol: str,
    direction: Direction,
    bb_lower_2sigma: float,
    bb_upper_2sigma: float,
    bb_lower_25sigma: float,
    bb_upper_25sigma: float,
    bb_lower_1sigma: float,
    bb_upper_1sigma: float,
    vwap: float,
    tick_size: float = 0.05,
    valid_until: datetime | None = None,
) -> ThesisCard:
    if direction == Direction.LONG:
        trigger = bb_lower_2sigma - tick_size
        invalidation = bb_lower_25sigma
        raw_t1 = vwap
        min_reward = 0.6 * abs(trigger - invalidation)
        t1 = max(raw_t1, trigger + min_reward)
        t2 = bb_upper_1sigma
        regime = Regime.RANGE_BOUND
    else:
        trigger = bb_upper_2sigma + tick_size
        invalidation = bb_upper_25sigma
        raw_t1 = vwap
        min_reward = 0.6 * abs(trigger - invalidation)
        t1 = min(raw_t1, trigger - min_reward)
        t2 = bb_lower_1sigma
        regime = Regime.RANGE_BOUND

    return ThesisCard(
        thesis_id=str(uuid.uuid4()),
        symbol=symbol,
        direction=direction,
        setup_type=SetupType.MEAN_REVERSION,
        trigger=round(trigger, 2),
        invalidation=round(invalidation, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        valid_until=valid_until or datetime.now(timezone.utc),
        preferred_regime=regime,
    )
