from engine.layers.l6_ranking import L6Ranking, compute_adaptive_theta
from models.enums import RankMovement


def test_entry_blocked_when_gap_below_theta():
    """NEWCO with score below the 25th stock's score stays out of top 25."""
    ranker = L6Ranking(top_n=25)
    ranker.previous_ranks = {f"S{i}": i+1 for i in range(25)}
    stocks = [{"symbol": f"S{i}", "score": 90 - i} for i in range(25)]
    stocks.append({"symbol": "NEWCO", "score": 65.0})
    result, _ = ranker.rank(stocks)
    symbols = [r.symbol for r in result]
    assert "NEWCO" not in symbols
    assert len(result) == 25


def test_entry_allowed_when_gap_exceeds_theta():
    """NEWCO with high score naturally enters top 25."""
    ranker = L6Ranking(top_n=25)
    ranker.previous_ranks = {f"S{i}": i+1 for i in range(25)}
    stocks = [{"symbol": f"S{i}", "score": 90 - i} for i in range(25)]
    stocks.append({"symbol": "NEWCO", "score": 85.0})
    result, _ = ranker.rank(stocks)
    symbols = [r.symbol for r in result]
    assert "NEWCO" in symbols
    assert len(result) == 25


def test_concentration_metrics():
    from engine.layers.l6_ranking import compute_concentration
    metrics = compute_concentration(
        scores=list(range(90, 65, -1)),
        sectors=["Bank"] * 10 + ["IT"] * 5 + ["Auto"] * 3 + ["FMCG"] * 3 + ["Metal"] * 4,
    )
    assert metrics["sector_concentration"] == 10
    assert metrics["is_theme_day"] is True
    assert metrics["score_spread"] > 0
