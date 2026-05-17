import random
from datetime import datetime, timezone

import polars as pl

from models.enums import Regime, Direction
from models.frames import MarketContextFrame, ThesisCard
from layers.l1_market_context import L1MarketContext
from layers.l5_scoring import L5Scoring
from layers.l6_ranking import L6Ranking
from layers.l7_confluence import L7Confluence
from layers.l8_thesis import L8Thesis, L8CostModel
from layers.l9_monitor import L9ShadowLedger
from layers.l10_edge import L10EdgeLookup
from api.websocket_manager import manager as ws_manager


NIFTY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "HINDUNILVR", "KOTAKBANK", "BAJFINANCE", "WIPRO", "AXISBANK",
    "TITAN", "MARUTI", "SUNPHARMA", "ULTRACEMCO", "NTPC", "POWERGRID",
    "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND", "JSWSTEEL", "TATASTEEL",
    "ADANIPORTS", "ADANIENT", "ONGC", "COALINDIA",
]


class PipelineOrchestrator:
    """Orchestrates the L1-L10 pipeline every minute during market hours."""

    def __init__(self):
        self.l1 = L1MarketContext()
        self.l5 = L5Scoring()
        self.l6 = L6Ranking(top_n=25)
        self.l7 = L7Confluence()
        self.l8 = L8Thesis()
        self.l8_cost = L8CostModel()
        self.l9 = L9ShadowLedger()
        self.l10 = L10EdgeLookup()
        self._cycle_count = 0

    async def run_cycle(self):
        """Execute one full L1-L10 pipeline cycle."""
        now = datetime.now(timezone.utc)
        self._cycle_count += 1

        # L1: Market Context
        nifty_df = self._synthetic_nifty_ohlc()
        vix_value = random.uniform(13, 28)
        stock_data = {sym: self._synthetic_stock_ohlc(sym) for sym in random.sample(NIFTY_SYMBOLS, 30)}
        context = self.l1.compute(nifty_df, vix_value, stock_data)

        # L2-L5: Score every symbol through L5 + L7 confluence
        regime = context.regime
        scored = []
        for sym in NIFTY_SYMBOLS:
            symbol_data = self._synthetic_symbol_signals(sym, regime)
            sector = {"rank": random.randint(1, 11), "tailwind": random.random() > 0.7}
            oi = {"classification": random.choice(
                ["Long Buildup", "Short Buildup", "Long Unwinding", "Short Covering", "Neutral"]
            )}
            result = self.l5.compute(symbol_data, regime, sector, oi)

            cdata = self._synthetic_confluence_data(sym, symbol_data["direction"])
            conf_score = self.l7.compute(cdata)

            result["confluence_score"] = conf_score
            result["setup_type"] = random.choice([1, 2, 3, 4, 5, 6])
            result["actionability_tier"] = "Research-Only"
            result["liquidity_quality"] = random.choice(["Excellent", "Good", "Marginal"])
            result["net_rr"] = random.uniform(0.5, 3.0)
            scored.append(result)

        # L6: Rank
        rankings = self.l6.rank(scored)
        longs = [r for r in rankings if r.net_rr > 0]
        shorts = [r for r in rankings if r.net_rr <= 0]

        # L8: Assemble theses for top 5
        theses = []
        for rank_entry in rankings[:5]:
            orb_high = rank_entry.score * 10 * random.uniform(0.99, 1.01)
            orb_low = rank_entry.score * 10 * random.uniform(0.94, 0.98)
            vwap = (orb_high + orb_low) / 2
            pdh = orb_high * 1.02
            direction = "LONG" if rank_entry.net_rr > 0 else "SHORT"

            thesis = self.l8.assemble(
                symbol=rank_entry.symbol,
                direction=direction,
                orb_high=orb_high,
                orb_low=orb_low,
                vwap=vwap,
                pdh=pdh,
                confluence_score=rank_entry.confluence_score,
            )

            cost_data = {
                "trigger": thesis.trigger,
                "t1": thesis.t1,
                "invalidation": thesis.invalidation,
                "lot_size": 50,
                "futures": True,
                "direction": direction,
                "time_remaining_min": 120,
            }
            costs = self.l8_cost.apply(cost_data)
            thesis.gross_rr = costs["gross_rr"]
            thesis.net_rr = costs["net_rr"]
            thesis.time_decay_multiplier = costs["time_decay_multiplier"]

            if thesis.net_rr >= 1.5:
                thesis.grade = "ATTRACTIVE"
            elif thesis.net_rr >= 1.0:
                thesis.grade = "MARGINAL"
            else:
                thesis.grade = "UNATTRACTIVE"

            theses.append(thesis)

        # L9: Trigger + tick check (same loop so each thesis is checked
        # against its own price, not aggregated across all theses)
            await self.l9.on_trigger({
                "thesis_id": thesis.thesis_id,
                "symbol": thesis.symbol,
                "direction": thesis.direction.value,
                "trigger": thesis.trigger,
                "invalidation": thesis.invalidation,
                "t1": thesis.t1,
                "t2": thesis.t2,
            })
            mock_price = thesis.trigger * random.uniform(0.999, 1.001)
            results = await self.l9.on_tick(mock_price)
            for r in results:
                if r["state"] == "STOPPED_OUT":
                    await ws_manager.broadcast({
                        "type": "L9_INVALIDATION",
                        "timestamp": now.isoformat(),
                        "payload": {"thesis_id": r["thesis_id"], "reason": f"Stop loss hit at {mock_price:.2f}"},
                    })

        # L9: Tick check — already done per-thesis above; placeholder kept
        # so the check() interface is exercised within the registration loop.

        # L10: Edge lookup
        edge_events = []
        for st in [1, 2, 3]:
            for d in [Direction.LONG, Direction.SHORT]:
                reg = Regime(regime)
                edge = self.l10.lookup(st, reg, d)
                if edge["is_significant"]:
                    tier = st * 10 + (1 if d == Direction.LONG else 2)
                    edge_events.append({"tier": tier, "promotion": "PROMOTED" if edge["n"] >= 30 else "WATCH"})

        # Broadcast all events
        await ws_manager.broadcast({
            "type": "L1_CONTEXT",
            "timestamp": now.isoformat(),
            "payload": context.model_dump(),
        })
        await ws_manager.broadcast({
            "type": "L6_RANKINGS",
            "timestamp": now.isoformat(),
            "payload": {
                "long": [r.model_dump() for r in longs],
                "short": [r.model_dump() for r in shorts],
            },
        })
        for thesis in theses:
            await ws_manager.broadcast({
                "type": "L8_THESIS",
                "timestamp": now.isoformat(),
                "payload": {"thesis_id": thesis.thesis_id, "card": thesis.model_dump()},
            })
        for evt in edge_events:
            await ws_manager.broadcast({
                "type": "L10_EDGE",
                "timestamp": now.isoformat(),
                "payload": evt,
            })

    # Synthetic data generators
    def _synthetic_nifty_ohlc(self) -> pl.DataFrame:
        closes = [22000 + sum((random.random() - 0.48) * 20 for _ in range(i)) for i in range(1, 101)]
        return pl.DataFrame({
            "close": closes,
            "high": [c + random.uniform(10, 50) for c in closes],
            "low": [c - random.uniform(10, 50) for c in closes],
        })

    def _synthetic_stock_ohlc(self, symbol: str) -> pl.DataFrame:
        base = hash(symbol) % 5000
        closes = [base + random.gauss(0, 10) for _ in range(20)]
        return pl.DataFrame({
            "close": closes,
            "high": [c + random.uniform(1, 10) for c in closes],
            "low": [c - random.uniform(1, 10) for c in closes],
            "vwap": [c + random.uniform(-2, 2) for c in closes],
        })

    def _synthetic_symbol_signals(self, symbol: str, regime: str) -> dict:
        base = hash(symbol + regime) % 100
        direction = "LONG" if random.random() > 0.35 else "SHORT"
        return {
            "symbol": symbol,
            "ema_aligned": random.random() > 0.4,
            "supertrend_bull": direction == "LONG",
            "adx": random.uniform(15, 40),
            "rsi": random.uniform(35, 70),
            "macd_divergence": random.random() > 0.7,
            "roc_z": random.gauss(0, 1),
            "above_vwap": random.random() > 0.5,
            "vol_z": random.gauss(0.5, 1),
            "vol_confirm": random.random() > 0.4,
            "direction": direction,
            "bb_position": random.random(),
            "atr_pctile": random.random(),
            "dist_to_support": random.uniform(0, 0.1),
            "pos_52w": random.random(),
            "cpr_dist": random.uniform(0, 0.05),
        }

    def _synthetic_confluence_data(self, symbol: str, direction: str) -> dict:
        return {
            "close": random.uniform(1000, 5000),
            "high": random.uniform(1010, 5050),
            "low": random.uniform(990, 4950),
            "volume": random.uniform(5000, 50000),
            "median_volume": random.uniform(4000, 30000),
            "bar_range": random.uniform(5, 50),
            "median_range": random.uniform(5, 40),
            "ema9": random.uniform(1000, 5000),
            "ema20": random.uniform(1000, 5000),
            "ema50": random.uniform(1000, 5000),
            "price": random.uniform(1000, 5000),
            "invalidation": random.uniform(950, 4950),
            "atr": random.uniform(10, 100),
            "t1": random.uniform(1050, 5050),
            "direction": direction,
        }


pipeline = PipelineOrchestrator()
