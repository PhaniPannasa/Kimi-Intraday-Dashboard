import pytest
from layers.l8_thesis import compute_brokerage, compute_time_decay, L8CostModel


def test_compute_brokerage():
    result = compute_brokerage(entry=2500, exit=2550, qty=100, lot_size=50,
                                futures=True, direction="LONG")
    assert result["turnover"] > 0
    assert result["total_cost"] > 0
    assert 0 < result["cost_pct"] < 2.0


def test_compute_time_decay():
    multiplier = compute_time_decay(45)  # 45 minutes remaining
    assert multiplier > 0
    # More time remaining should give higher multiplier
    assert compute_time_decay(90) > compute_time_decay(30)


def test_l8_cost_model():
    model = L8CostModel()
    thesis_data = {
        "trigger": 2500, "t1": 2550, "invalidation": 2450,
        "lot_size": 50, "futures": True, "direction": "LONG",
        "time_remaining_min": 60
    }
    result = model.apply(thesis_data)
    assert "net_rr" in result
    assert "adjusted_rr" in result
    assert result["adjusted_rr"] <= result["net_rr"]
