import pytest
from layers.l6_ranking import L6Ranking
from models.enums import RankMovement


def test_rank_movement_new():
    l6 = L6Ranking()
    assert l6.compute_rank_movement("RELIANCE", 1) == RankMovement.NEW


def test_rank_movement_up():
    l6 = L6Ranking()
    l6.previous_ranks = {"RELIANCE": 5}
    assert l6.compute_rank_movement("RELIANCE", 1) == RankMovement.UP


def test_rank_movement_stable():
    l6 = L6Ranking()
    l6.previous_ranks = {"RELIANCE": 2}
    assert l6.compute_rank_movement("RELIANCE", 1) == RankMovement.STABLE


def test_ranking_top_n():
    l6 = L6Ranking(top_n=3)
    stocks = [{"symbol": f"S{i}", "score": 100 - i, "instrument_key": f"K{i}"} for i in range(10)]
    rankings, metrics = l6.rank(stocks)
    assert len(rankings) == 3
    assert rankings[0].symbol == "S0"
    assert "sector_concentration" in metrics
