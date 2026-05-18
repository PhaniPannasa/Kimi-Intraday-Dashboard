# tests/test_l8_cost_model.py
import pytest
from layers.l8_cost_model import (
    compute_brokerage_equity,
    compute_brokerage_futures,
    compute_slippage,
    compute_net_rr,
    COST_RATES,
)


def test_equity_brokerage_matches_spec():
    """Verify equity intraday (MIS) rates against spec table."""
    costs = compute_brokerage_equity(entry=1000.0, exit=1010.0, qty=100, direction="LONG")
    # Brokerage: 0.03% capped at 20/order
    assert costs["brokerage"] == pytest.approx(40.0, rel=0.01)  # 20+20 both legs
    # STT: 0.025% sell only
    assert costs["stt"] == pytest.approx(1010 * 100 * 0.00025, rel=0.01)
    # Exchange: 0.00297% both sides
    assert costs["exchange"] == pytest.approx((1000 + 1010) * 100 * 0.0000297, rel=0.01)
    # SEBI: 0.0001% both sides
    assert costs["sebi"] == pytest.approx((1000 + 1010) * 100 * 0.000001, rel=0.01)
    # Stamp: 0.003% buy only
    assert costs["stamp"] == pytest.approx(1000 * 100 * 0.00003, rel=0.01)
    # GST: 18% on (brokerage + exchange + sebi)
    gst_base = costs["brokerage"] + costs["exchange"] + costs["sebi"]
    assert costs["gst"] == pytest.approx(gst_base * 0.18, rel=0.01)


def test_futures_brokerage_matches_spec():
    """Verify futures intraday rates against spec table."""
    costs = compute_brokerage_futures(entry=1000.0, exit=1010.0, qty=100, direction="LONG")
    # Brokerage: flat 20/leg
    assert costs["brokerage"] == 40.0
    # STT: 0.0125% sell only
    assert costs["stt"] == pytest.approx(1010 * 100 * 0.000125, rel=0.01)
    # Exchange: 0.00173% both sides
    assert costs["exchange"] == pytest.approx((1000 + 1010) * 100 * 0.0000173, rel=0.01)


def test_slippage_by_liquidity_bucket():
    """Verify slippage rates match spec per liquidity bucket."""
    assert compute_slippage("Excellent", is_stop=False) == 5
    assert compute_slippage("Good", is_stop=False) == 10
    assert compute_slippage("Marginal", is_stop=False) == 20
    assert compute_slippage("Poor", is_stop=False) == 35
    # Stop-leg add-ons
    assert compute_slippage("Excellent", is_stop=True) == 13   # 5+8
    assert compute_slippage("Good", is_stop=True) == 25        # 10+15
    assert compute_slippage("Marginal", is_stop=True) == 45    # 20+25
    assert compute_slippage("Poor", is_stop=True) == 75        # 35+40


def test_net_rr_formula_matches_spec():
    """Spec: Net reward = |T1-Trigger| - (cost% * Trigger)
       Net risk = |Trigger-Invalidation| + (stop_slippage * Trigger)
       Net R:R = Net reward / Net risk"""
    result = compute_net_rr(
        trigger=1000.0, t1=1020.0, invalidation=990.0,
        cost_pct=0.05, stop_slippage_pct=0.0013,
    )
    net_reward = 20.0 - (0.0005 * 1000)  # = 19.5
    net_risk = 10.0 + (0.000013 * 1000)  # = 10.013
    expected = net_reward / net_risk
    assert result["net_rr"] == pytest.approx(expected, rel=0.01)
    assert result["net_reward"] == pytest.approx(net_reward, rel=0.01)
    assert result["net_risk"] == pytest.approx(net_risk, rel=0.01)


def test_short_direction_cost_application():
    """SHORT: entry is sell, exit is buy-to-cover. STT on entry leg, stamp on exit leg."""
    costs = compute_brokerage_futures(entry=1000.0, exit=990.0, qty=100, direction="SHORT")
    # STT: 0.0125% on sell leg = entry for SHORT
    assert costs["stt"] == pytest.approx(1000 * 100 * 0.000125, rel=0.01)
    # Stamp: 0.002% on buy leg = exit for SHORT (buy to cover)
    assert costs["stamp"] == pytest.approx(990 * 100 * 0.00002, rel=0.01)
