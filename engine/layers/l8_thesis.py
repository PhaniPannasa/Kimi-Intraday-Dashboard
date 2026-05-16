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
