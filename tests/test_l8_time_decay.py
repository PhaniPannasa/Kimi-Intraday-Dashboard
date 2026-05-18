# tests/test_l8_time_decay.py
import pytest
import math
from engine.layers.l8_time_decay import compute_time_decay, LAMBDA_VALUES, TIME_WINDOWS


def test_orb_time_decay_at_creation():
    """At t=0 minutes elapsed (just created), multiplier = 1.0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=0)
    assert result == 1.0


def test_orb_time_decay_after_60_min():
    """ORB: M(t) = exp(-0.0003 * max(0, 60-30)^2) = exp(-0.0003*900) = exp(-0.27) ~ 0.763"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=60)
    expected = math.exp(-0.0003 * (60 - 30)**2)
    assert result == pytest.approx(expected, rel=0.001)


def test_vwap_time_decay_after_90_min():
    """VWAP/ST: lambda=0.00015, t_window=15"""
    result = compute_time_decay("VWAP_RECLAIM", minutes_since_creation=90)
    expected = math.exp(-0.00015 * (90 - 15)**2)
    assert result == pytest.approx(expected, rel=0.001)


def test_time_decay_before_window_is_1():
    """Before t_window, multiplier stays at 1.0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=15)
    assert result == 1.0


def test_time_decay_deep_decay():
    """After 4 hours, multiplier approaches 0"""
    result = compute_time_decay("ORB_15MIN", minutes_since_creation=240)
    assert result < 0.01


def test_custom_setup_decay():
    """Setup not in LAMBDA_VALUES uses default lambda=0.0002"""
    result = compute_time_decay("UNKNOWN_SETUP", minutes_since_creation=90)
    expected = math.exp(-0.0002 * (90 - 30)**2)
    assert result == pytest.approx(expected, rel=0.001)
