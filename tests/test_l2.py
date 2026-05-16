import pytest
from layers.l2_universe import L2Universe, compute_liquidity_quality_score, bucket_lqs


def test_bucket_lqs():
    assert bucket_lqs(0.85) == "Excellent"
    assert bucket_lqs(0.60) == "Good"
    assert bucket_lqs(0.40) == "Marginal"
    assert bucket_lqs(0.20) == "Poor"


def test_l2_enrich():
    l2 = L2Universe()
    result = l2.enrich("RELIANCE", "NSE_EQ|INE002A01018", lqs=0.9)
    assert result["symbol"] == "RELIANCE"
    assert result["liquidity_quality"] == "Excellent"
