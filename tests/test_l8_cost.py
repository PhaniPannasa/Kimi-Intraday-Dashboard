import pytest
from layers.l8_thesis import compute_brokerage, compute_time_decay, L8CostModel


def test_compute_brokerage_futures_long():
    result = compute_brokerage(entry=2500, exit=2550, qty=100, lot_size=50,
                                futures=True, direction="LONG")
    assert result["turnover"] == 505000
    # Brokerage: 0.01% per leg, capped at ?20 -> ?40 total
    assert result["brokerage"] == 40
    # STT: 0.0125% on sell leg only (exit for LONG) = 2550*100*0.000125
    assert abs(result["stt"] - 31.875) < 0.01
    # Exchange: 0.0019% futures rate on turnover
    assert abs(result["exchange_txn"] - 9.595) < 0.1
    # SEBI: ?10/crore = turnover * 0.0000001
    assert abs(result["sebi"] - 0.0505) < 0.01
    # GST: 18% of (brokerage + exchange + sebi)
    expected_gst = (40 + 9.595 + 0.0505) * 0.18
    assert abs(result["gst"] - expected_gst) < 0.1
    # Stamp: 0.002% on buy leg only (entry for LONG) = 2500*100*0.00002
    assert abs(result["stamp"] - 5.0) < 0.01
    assert result["total_cost"] > 0
    assert 0 < result["cost_pct"] < 2.0


def test_compute_brokerage_futures_short():
    result = compute_brokerage(entry=2500, exit=2400, qty=100, lot_size=50,
                                futures=True, direction="SHORT")
    assert result["turnover"] == 490000
    # Brokerage: ?40 total
    assert result["brokerage"] == 40
    # STT: 0.0125% on sell leg (for SHORT, buy-to-cover is the buy leg... actually sell = entry for SHORT)
    # For SHORT: open = sell at 2500, close = buy-to-cover at 2400. Sell leg = entry.
    assert abs(result["stt"] - 31.25) < 0.01
    # Stamp: 0.002% on buy leg (for SHORT: buy-to-cover = exit)
    assert abs(result["stamp"] - 4.8) < 0.01
    assert result["total_cost"] > 0


def test_compute_time_decay():
    multiplier = compute_time_decay(45)
    assert multiplier > 0
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
