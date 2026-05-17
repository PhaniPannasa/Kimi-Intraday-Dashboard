from typing import List
from models.frames import RankingEntry
from models.enums import RankMovement


class L6Ranking:
    def __init__(self, top_n: int = 25):
        self.top_n = top_n
        self.previous_ranks: dict[str, int] = {}
        self.theta = 2.0

    def compute_rank_movement(self, symbol: str, new_rank: int) -> RankMovement:
        old_rank = self.previous_ranks.get(symbol)
        if old_rank is None:
            return RankMovement.NEW
        if new_rank <= old_rank - 2:
            return RankMovement.UP
        if new_rank >= old_rank + 2:
            return RankMovement.DOWN
        return RankMovement.STABLE

    def rank(self, scored_stocks: list) -> List[RankingEntry]:
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)
        ranked = []
        for i, stock in enumerate(scored_stocks[:self.top_n]):
            rank = i + 1
            movement = self.compute_rank_movement(stock["symbol"], rank)
            ranked.append(RankingEntry(
                symbol=stock["symbol"],
                instrument_key=stock.get("instrument_key", ""),
                score=stock["score"],
                setup_type=stock.get("setup_type", 1),
                confluence_score=stock.get("confluence_score", 0),
                net_rr=stock.get("net_rr", 0.0),
                actionability_tier=stock.get("actionability_tier", "Research-Only"),
                rank_movement=movement,
                liquidity_quality=stock.get("liquidity_quality", "Good"),
            ))
            self.previous_ranks[stock["symbol"]] = rank
        return ranked
