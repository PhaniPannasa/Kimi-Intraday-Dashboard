# tests/test_l8.py
from layers.l8_thesis import L8Thesis
from models.enums import Direction, SetupType


def test_l8_orchestrator_long():
    l8 = L8Thesis()
    thesis = l8.assemble(
        symbol="RELIANCE",
        direction="LONG",
        setup_type=1,  # ORB_15MIN
        setup_params={"orb_high": 2500.0, "orb_low": 2480.0, "vwap": 2490.0, "pdh": 2520.0, "pdl": 2470.0},
        confluence_data={
            "close": 2505.0, "high": 2510.0, "low": 2495.0,
            "volume": 50000, "median_volume": 25000,
            "ema9": 2500.0, "ema20": 2485.0, "ema50": 2450.0,
            "atr": 10.0, "price": 2505.0, "invalidation": 2480.0, "t1": 2515.0,
            "bar_range": 15.0, "median_range": 20.0,
            "direction": "LONG", "is_opening": False,
        },
    )
    assert thesis.symbol == "RELIANCE"
    assert thesis.direction == Direction.LONG
    assert thesis.trigger > 0
    assert thesis.invalidation > 0
    assert thesis.gross_rr > 0
    assert thesis.grade in ("ATTRACTIVE", "MARGINAL", "UNATTRACTIVE")


def test_l8_orchestrator_short():
    l8 = L8Thesis()
    thesis = l8.assemble(
        symbol="HDFC",
        direction="SHORT",
        setup_type=1,
        setup_params={"orb_high": 1800.0, "orb_low": 1770.0, "vwap": 1790.0, "pdh": 1820.0, "pdl": 1760.0},
        confluence_data={
            "close": 1775.0, "high": 1785.0, "low": 1765.0,
            "volume": 40000, "median_volume": 20000,
            "ema9": 1785.0, "ema20": 1795.0, "ema50": 1810.0,
            "atr": 8.0, "price": 1775.0, "invalidation": 1785.0, "t1": 1760.0,
            "bar_range": 20.0, "median_range": 15.0,
            "direction": "SHORT", "is_opening": False,
        },
    )
    assert thesis.symbol == "HDFC"
    assert thesis.direction == Direction.SHORT
    assert thesis.trigger > 0
