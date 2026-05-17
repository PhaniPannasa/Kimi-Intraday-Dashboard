import pytest
from layers.l7_confluence import (
    check_strong_close, check_volume_confirm,
    check_htf_alignment, L7Confluence
)


def test_strong_close_long():
    assert check_strong_close(90, 100, 50, "LONG") is True
    assert check_strong_close(60, 100, 50, "LONG") is False


def test_volume_confirm():
    assert check_volume_confirm(1500, 1000) is True
    assert check_volume_confirm(1200, 1000) is False


def test_htf_alignment():
    assert check_htf_alignment(105, 100, 95, "LONG") is True
    assert check_htf_alignment(95, 100, 105, "SHORT") is True


def test_l7_confluence():
    l7 = L7Confluence()
    data = {
        "close": 90, "high": 100, "low": 50,
        "volume": 2000, "median_volume": 1000,
        "bar_range": 10, "median_range": 20,
        "ema9": 105, "ema20": 100, "ema50": 95,
        "price": 90, "invalidation": 80, "atr": 20,
        "t1": 110, "direction": "LONG"
    }
    assert l7.compute(data) == 6
