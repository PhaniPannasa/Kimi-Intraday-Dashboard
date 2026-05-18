from engine.layers.l10_edge import L10EdgeLookup, beta_binomial_posterior, benjamini_hochberg
from models.enums import SetupType, Regime, Direction


def test_tier1_found():
    l = L10EdgeLookup()
    key = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, 1, 3)
    l.edge_store[key] = {"n": 35, "hit_rate": 0.65, "ci_lower": 0.50, "ci_upper": 0.78}
    result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
    assert result["tier"] == 1
    assert result["n"] == 35


def test_tier2_fallback():
    l = L10EdgeLookup()
    key1 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, 1, 3)
    l.edge_store[key1] = {"n": 15, "hit_rate": 0.6, "ci_lower": 0.35, "ci_upper": 0.85}
    key2 = l._make_key(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, None, 3)
    l.edge_store[key2] = {"n": 45, "hit_rate": 0.62, "ci_lower": 0.48, "ci_upper": 0.74}
    result = l.lookup(SetupType.ORB_15MIN, Regime.TRENDING_UP, Direction.LONG, sector=1, time_bucket=3)
    assert result["tier"] == 2


def test_global_fallback():
    l = L10EdgeLookup()
    key6 = l._make_key(None, None, Direction.LONG, None, None)
    l.edge_store[key6] = {"n": 200, "hit_rate": 0.55, "ci_lower": 0.48, "ci_upper": 0.62}
    result = l.lookup(SetupType.VWAP_RECLAIM, Regime.RANGE_BOUND, Direction.LONG)
    assert result["tier"] == 6


def test_beta_binomial_posterior():
    post = beta_binomial_posterior(k=10, n=20, alpha_prior=6, beta_prior=6)
    assert 0.45 <= post["posterior_mean"] <= 0.55
    assert "ci_lower" in post


def test_bh_alpha_is_010():
    p_values = [0.01, 0.03, 0.05, 0.08, 0.15, 0.30]
    significant = benjamini_hochberg(p_values, alpha=0.10)
    assert sum(significant) == 3
