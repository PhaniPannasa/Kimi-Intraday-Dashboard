"""Tests for L8 cost model and time decay (verifies imports from new modules)."""
import pytest
from layers.l8_cost_model import compute_brokerage, compute_net_rr, compute_grade
from layers.l8_time_decay import compute_time_decay


def test_compute_brokerage_futures_long():
    result = compute_brokerage(entry=2500, exit=2550, qty=100, lot_size=50,
                                futures=True, direction="LONG")
    assert result["turnover"] == 505000
    # Brokerage: Rs.20/leg x 2
    assert result["brokerage"] == 40
    # STT: 0.0125% on sell leg only (exit for LONG) = 2550*100*0.000125
    assert abs(result["stt"] - 31.875) < 0.01
    assert result["total_cost"] > 0
    assert 0 < result["cost_pct"] < 1.0


def test_compute_brokerage_futures_short():
    result = compute_brokerage(entry=2500, exit=2400, qty=100, lot_size=50,
                                futures=True, direction="SHORT")
    assert result["turnover"] == 490000
    # Brokerage: Rs.40 total
    assert result["brokerage"] == 40
    # STT: 0.0125% on sell leg (for SHORT, entry is sell)
    assert abs(result["stt"] - 31.25) < 0.01
    assert result["total_cost"] > 0


def test_compute_time_decay():
    multiplier = compute_time_decay("ORB_15MIN", 45)
    assert 0 < multiplier <= 1.0
    # Earlier minutes should have higher multiplier than later minutes
    assert compute_time_decay("VWAP_RECLAIM", 30) > compute_time_decay("VWAP_RECLAIM", 90)


def test_compute_grade():
    assert compute_grade(2.0) == "ATTRACTIVE"
    assert compute_grade(1.5) == "ATTRACTIVE"
    assert compute_grade(1.25) == "MARGINAL"
    assert compute_grade(0.5) == "UNATTRACTIVE"


def test_compute_net_rr_basic():
    result = compute_net_rr(
        trigger=2500, t1=2550, invalidation=2450,
        cost_pct=0.02, stop_slippage_pct=0.001,
    )
    assert result["gross_rr"] > 0
    assert result["net_rr"] > 0
    assert result["net_rr"] < result["gross_rr"]
