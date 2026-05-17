import pytest
from models.frames import MarketContextFrame, RankingEntry, ThesisCard
from models.enums import Regime, SetupType, Direction


def test_market_context_default():
    ctx = MarketContextFrame()
    assert ctx.regime == Regime.RANGE_BOUND
    assert ctx.regime_confidence == 0.0


def test_ranking_entry_validation():
    entry = RankingEntry(symbol="RELIANCE", instrument_key="NSE_EQ|INE002A01018", score=84.5)
    assert entry.symbol == "RELIANCE"
    assert entry.score == 84.5


def test_thesis_card_fields():
    thesis = ThesisCard(thesis_id="test-1", symbol="TCS", direction=Direction.LONG)
    assert thesis.thesis_id == "test-1"
    assert thesis.direction == Direction.LONG
