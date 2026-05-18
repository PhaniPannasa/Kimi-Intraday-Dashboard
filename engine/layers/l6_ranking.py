import math
from typing import List
from models.frames import RankingEntry
from models.enums import RankMovement


def compute_adaptive_theta(scores_20_30: list[float]) -> float:
    """Adaptive hysteresis threshold from score gaps at ranks 20-30."""
    if len(scores_20_30) < 2:
        return 2.0
    gaps = [abs(scores_20_30[i] - scores_20_30[i+1])
            for i in range(len(scores_20_30) - 1)]
    mean_gap = sum(gaps) / len(gaps)
    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
    sigma_gap = math.sqrt(variance)
    return max(2.0, 0.25 * sigma_gap)


def compute_concentration(scores: list[float], sectors: list[str]) -> dict:
    """Compute informational concentration metrics."""
    from collections import Counter
    sector_counts = Counter(sectors)
    max_sector_count = max(sector_counts.values()) if sector_counts else 0
    score_spread = max(scores) - min(scores) if scores else 0
    return {
        "sector_concentration": max_sector_count,
        "is_theme_day": max_sector_count > 8,
        "score_spread": score_spread,
        "is_high_conviction": score_spread > 20,
    }


class L6Ranking:
    def __init__(self, top_n: int = 25):
        self.top_n = top_n
        self.previous_ranks: dict[str, int] = {}
        self._rank_history: dict[str, list[tuple[int, int]]] = {}
        self._tick_counter: int = 0
        self.theta: float = 2.0

    def compute_rank_movement(self, symbol: str, new_rank: int) -> RankMovement:
        old_rank = self.previous_ranks.get(symbol)
        if old_rank is None:
            return RankMovement.NEW

        history = self._rank_history.get(symbol, [])
        rank_5_ticks_ago = old_rank
        current_tick = self._tick_counter
        for r, tick in reversed(history):
            if current_tick - tick >= 5:
                rank_5_ticks_ago = r
                break

        if new_rank <= rank_5_ticks_ago - 2:
            return RankMovement.UP
        if new_rank >= rank_5_ticks_ago + 2:
            return RankMovement.DOWN
        return RankMovement.STABLE

    def rank(self, scored_stocks: list) -> tuple[List[RankingEntry], dict]:
        self._tick_counter += 1
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # Adaptive theta from boundary scores
        boundary_scores = [s["score"] for s in scored_stocks[19:30]] if len(scored_stocks) >= 30 \
            else [s["score"] for s in scored_stocks[-11:]]
        self.theta = compute_adaptive_theta(boundary_scores)

        top_n_candidates = scored_stocks[:self.top_n]

        # Hysteresis gate
        if len(scored_stocks) > self.top_n:
            rank_25_score = top_n_candidates[-1]["score"]
            rank_26_score = scored_stocks[self.top_n]["score"]
            if rank_26_score > rank_25_score + self.theta:
                top_n_candidates[-1] = scored_stocks[self.top_n]

        ranked = []
        for i, stock in enumerate(top_n_candidates):
            rank = i + 1
            symbol = stock["symbol"]
            movement = self.compute_rank_movement(symbol, rank)

            ranked.append(RankingEntry(
                symbol=symbol,
                instrument_key=stock.get("instrument_key", ""),
                score=stock["score"],
                setup_type=stock.get("setup_type", 1),
                confluence_score=stock.get("confluence_score", 0),
                net_rr=stock.get("net_rr", 0.0),
                actionability_tier=stock.get("actionability_tier", "Research-Only"),
                rank_movement=movement,
                liquidity_quality=stock.get("liquidity_quality", "Good"),
            ))

            if symbol not in self._rank_history:
                self._rank_history[symbol] = []
            self._rank_history[symbol].append((rank, self._tick_counter))
            if len(self._rank_history[symbol]) > 10:
                self._rank_history[symbol] = self._rank_history[symbol][-10:]

            self.previous_ranks[symbol] = rank

        sectors = [s.get("sector", "Unknown") for s in top_n_candidates]
        scores = [s["score"] for s in top_n_candidates]
        metrics = compute_concentration(scores, sectors)
        return ranked, metrics
