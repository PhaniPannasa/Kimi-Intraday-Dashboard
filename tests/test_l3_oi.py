import pytest
from layers.l3_signals import classify_oi, compute_volume_zscore

def test_classify_oi_long_buildup():
    assert classify_oi(1.0, 3.0) == "Long Buildup"

def test_classify_oi_short_buildup():
    assert classify_oi(-1.0, 3.0) == "Short Buildup"

def test_classify_oi_long_unwinding():
    assert classify_oi(-1.0, -3.0) == "Long Unwinding"

def test_classify_oi_short_covering():
    assert classify_oi(1.0, -3.0) == "Short Covering"

def test_classify_oi_neutral():
    assert classify_oi(0.2, 0.5) == "Neutral"

def test_volume_zscore():
    assert compute_volume_zscore(150, 100, 25) == 2.0

def test_volume_zscore_zero_std():
    assert compute_volume_zscore(150, 100, 0) == 0
