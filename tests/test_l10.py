import pytest
from layers.l10_edge import L10EdgeLookup, check_min_samples, check_ci_width
from models.enums import SetupType, Regime, Direction


def test_check_min_samples():
    assert check_min_samples(30) is True
    assert check_min_samples(5) is False
    assert check_min_samples(15) is True


def test_check_ci_width():
    assert check_ci_width(0.50, 0.70, 0.15) is True   # half-width = 0.10
    assert check_ci_width(0.40, 0.80, 0.15) is False  # half-width = 0.20


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
    assert result["tier"] == 0


def test_l10_populate_and_lookup():
    l10 = L10EdgeLookup()
    l10.populate([
        {"setup_type": 1, "regime": "Trending-Up", "sector": 1, "time_bucket": 2,
         "direction": "LONG", "n": 42, "hit_rate": 0.62, "ci_lower": 0.51,
         "ci_upper": 0.73, "avg_net_return": 0.85, "std_net_return": 1.2}
    ])
    result = l10.lookup(
        setup_type=SetupType.ORB_15MIN,
        regime=Regime.TRENDING_UP,
        direction=Direction.LONG,
        sector=1,
        time_bucket=2
    )
    # n=42 passes tier1 n_min=30, CI half-width (0.73-0.51)/2=0.11 <= 0.15
    assert result["is_significant"] is True
    assert result["n"] == 42
    assert result["hit_rate"] == 0.62
    assert result["tier"] == 1


from layers.l10_edge import wilson_ci, benjamini_hochberg, beta_binomial_posterior


def test_wilson_ci_basic():
    lower, upper = wilson_ci(hit_rate=0.6, n=100)
    assert 0 < lower < 0.6 < upper < 1.0


def test_wilson_ci_zero_n():
    lower, upper = wilson_ci(hit_rate=0.0, n=0)
    assert lower == 0.0
    assert upper == 0.0


def test_benjamini_hochberg_basic():
    p_values = [0.01, 0.04, 0.03, 0.08, 0.2]
    significant = benjamini_hochberg(p_values, alpha=0.10)
    assert significant[0] is True
    assert significant[1] is True
    assert significant[2] is True
    assert significant[3] is True
    assert significant[4] is False


def test_benjamini_hochberg_monotonic():
    """BH must find largest k, scanning all p-values — not break on first failure."""
    p_values = [0.009, 0.021, 0.022, 0.023, 0.5]
    significant = benjamini_hochberg(p_values, alpha=0.10)
    # With alpha=0.10 and m=5, threshold for rank 5: 5*0.10/5=0.10, so p=0.023 <= 0.10
    assert significant == [True, True, True, True, False]


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([]) == []


def test_beta_binomial_posterior():
    post = beta_binomial_posterior(k=10, n=20, alpha_prior=6, beta_prior=6)
    assert 0.45 <= post["posterior_mean"] <= 0.55
    assert "ci_lower" in post
    assert "posterior_alpha" in post
    assert post["posterior_alpha"] == 16
    assert post["posterior_beta"] == 16
