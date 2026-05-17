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


from layers.l10_edge import wilson_ci, benjamini_hochberg, bayesian_bootstrap


def test_wilson_ci_basic():
    lower, upper = wilson_ci(hit_rate=0.6, n=100)
    assert 0 < lower < 0.6 < upper < 1.0


def test_wilson_ci_zero_n():
    lower, upper = wilson_ci(hit_rate=0.0, n=0)
    assert lower == 0.0
    assert upper == 0.0


def test_benjamini_hochberg_basic():
    p_values = [0.01, 0.04, 0.03, 0.08, 0.2]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    assert significant[0] is True
    assert significant[1] is False
    assert significant[2] is False
    assert significant[3] is False
    assert significant[4] is False


def test_benjamini_hochberg_monotonic():
    """BH must find largest k, scanning all p-values — not break on first failure."""
    p_values = [0.009, 0.021, 0.022, 0.023, 0.5]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    # With correct BH (scan all): k=4
    assert significant == [True, True, True, True, False]


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([]) == []


def test_bayesian_bootstrap_basic():
    returns = [0.5, -0.2, 1.2, 0.8, -0.1]
    result = bayesian_bootstrap(returns, n_bootstrap=1000)
    assert "mean" in result
    assert "ci_lower" in result
    assert "ci_upper" in result
    assert result["ci_lower"] < result["mean"] < result["ci_upper"]
