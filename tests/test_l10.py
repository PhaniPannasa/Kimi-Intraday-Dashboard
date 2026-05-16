import pytest
from layers.l10_edge import L10EdgeLookup, check_confidence_interval, check_min_samples
from models.enums import SetupType, Regime, Direction


def test_check_min_samples():
    assert check_min_samples(30) is True
    assert check_min_samples(5) is False
    assert check_min_samples(15) is True


def test_check_confidence_interval():
    assert check_confidence_interval(0.60, 0.50, 0.70) is True
    assert check_confidence_interval(0.40, 0.50, 0.70) is False


def test_l10_lookup_empty():
    l10 = L10EdgeLookup()
    result = l10.lookup(
        setup_type=SetupType.ORB_15MIN,
        regime=Regime.TRENDING_UP,
        direction=Direction.LONG,
        sector=1,
        time_bucket=2
    )
    assert result["is_significant"] is False
    assert result["n"] == 0


def test_l10_populate_and_lookup():
    l10 = L10EdgeLookup()
    l10.populate([
        {"setup_type": 1, "regime": "Trending-Up", "sector": 1, "time_bucket": 2,
         "direction": "LONG", "n": 42, "hit_rate": 0.62, "ci_lower": 0.48,
         "ci_upper": 0.74, "avg_net_return": 0.85, "std_net_return": 1.2}
    ])
    result = l10.lookup(
        setup_type=SetupType.ORB_15MIN,
        regime=Regime.TRENDING_UP,
        direction=Direction.LONG,
        sector=1,
        time_bucket=2
    )
    assert result["is_significant"] is True
    assert result["n"] == 42
    assert result["hit_rate"] == 0.62
