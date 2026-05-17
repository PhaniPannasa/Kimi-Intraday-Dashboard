import pytest
from layers.l8_thesis import setup_orb_15
from models.enums import Direction, SetupType


def test_setup_orb_15_long():
    thesis = setup_orb_15("RELIANCE", "LONG", 2500.0, 2480.0, 2490.0, 2520.0)
    assert thesis.symbol == "RELIANCE"
    assert thesis.direction == Direction.LONG
    assert thesis.setup_type == SetupType.ORB_15MIN
    assert thesis.trigger > 2500.0  # ORB high + buffer
    # invalidation = max(ORB low, VWAP*0.995) = max(2480, 2477.55) = 2480.0
    assert thesis.invalidation < 2490.0
    assert thesis.t1 > thesis.trigger  # trigger + 1.5*ORB range


def test_setup_orb_15_short():
    thesis = setup_orb_15("HDFC", "SHORT", 1800.0, 1770.0, 1790.0, 1820.0)
    assert thesis.symbol == "HDFC"
    assert thesis.direction == Direction.SHORT
    assert thesis.setup_type == SetupType.ORB_15MIN
    assert thesis.trigger < 1770.0  # ORB low - buffer
    # invalidation = min(ORB high, VWAP*1.005) = min(1800, 1798.95) = 1798.95
    assert thesis.invalidation > 1790.0
    assert thesis.t1 < thesis.trigger  # trigger - 1.5*ORB range


def test_l8_assemble_long():
    from layers.l8_thesis import L8Thesis
    l8 = L8Thesis()
    thesis = l8.assemble("RELIANCE", "LONG", 2500.0, 2480.0, 2490.0, 2520.0, confluence_score=4)
    assert thesis.symbol == "RELIANCE"
    assert thesis.direction == Direction.LONG
    assert thesis.confluence_score == 4
    assert thesis.gross_rr > 0
    assert thesis.net_rr == 0.0  # Set by cost model in pipeline
    assert thesis.grade in ("ATTRACTIVE", "MARGINAL", "UNATTRACTIVE")


def test_l8_assemble_short():
    from layers.l8_thesis import L8Thesis
    l8 = L8Thesis()
    thesis = l8.assemble("HDFC", "SHORT", 1800.0, 1770.0, 1790.0, 1820.0)
    assert thesis.symbol == "HDFC"
    assert thesis.direction == Direction.SHORT
    assert thesis.net_rr == 0.0  # Set by cost model in pipeline
    assert thesis.grade == "UNATTRACTIVE"  # net_rr 0.0 < 1.0
