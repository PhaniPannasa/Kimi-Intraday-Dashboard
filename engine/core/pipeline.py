"""Intraday pipeline — TickBuffer, BarAggregator, and PipelineOrchestrator.

TickBuffer      Accumulates WebSocket ticks into 1-min OHLCV bars per instrument.
BarAggregator   Manages one TickBuffer per symbol.
PipelineOrchestrator  Drives L1-L10 layers with real bar data, market-session
                      awareness, cold-start backfill, and closing snapshots.
"""

import asyncio
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import polars as pl

from api.websocket_manager import manager as ws_manager
from core.data.redis_cache import cache
from core.data.upstox_rest import upstox_rest
from core.session.market_session import session as market_session
from layers.l1_market_context import L1MarketContext
from layers.l3_signals import L3Signals, ema_aligned, detect_macd_divergence
from layers.l5_scoring import L5Scoring
from layers.l6_ranking import L6Ranking
from layers.l7_confluence import L7Confluence
from layers.l8_thesis import L8Thesis, L8CostModel
from layers.l9_monitor import L9ShadowLedger
from layers.l10_edge import L10EdgeLookup
from models.enums import Direction, Regime, SetupType
from models.frames import MarketContextFrame, ThesisCard

IST = timezone(timedelta(hours=5, minutes=30))

# 30 Nifty symbols with their Upstox instrument keys (NSE_EQ|<symbol>).
SYMBOL_TO_INSTRUMENT_KEY: dict[str, str] = {
    "RELIANCE": "NSE_EQ|RELIANCE",
    "TCS": "NSE_EQ|TCS",
    "HDFCBANK": "NSE_EQ|HDFCBANK",
    "INFY": "NSE_EQ|INFY",
    "ICICIBANK": "NSE_EQ|ICICIBANK",
    "SBIN": "NSE_EQ|SBIN",
    "BHARTIARTL": "NSE_EQ|BHARTIARTL",
    "ITC": "NSE_EQ|ITC",
    "LT": "NSE_EQ|LT",
    "HINDUNILVR": "NSE_EQ|HINDUNILVR",
    "KOTAKBANK": "NSE_EQ|KOTAKBANK",
    "BAJFINANCE": "NSE_EQ|BAJFINANCE",
    "WIPRO": "NSE_EQ|WIPRO",
    "AXISBANK": "NSE_EQ|AXISBANK",
    "TITAN": "NSE_EQ|TITAN",
    "MARUTI": "NSE_EQ|MARUTI",
    "SUNPHARMA": "NSE_EQ|SUNPHARMA",
    "ULTRACEMCO": "NSE_EQ|ULTRACEMCO",
    "NTPC": "NSE_EQ|NTPC",
    "POWERGRID": "NSE_EQ|POWERGRID",
    "HCLTECH": "NSE_EQ|HCLTECH",
    "TECHM": "NSE_EQ|TECHM",
    "ASIANPAINT": "NSE_EQ|ASIANPAINT",
    "NESTLEIND": "NSE_EQ|NESTLEIND",
    "JSWSTEEL": "NSE_EQ|JSWSTEEL",
    "TATASTEEL": "NSE_EQ|TATASTEEL",
    "ADANIPORTS": "NSE_EQ|ADANIPORTS",
    "ADANIENT": "NSE_EQ|ADANIENT",
    "ONGC": "NSE_EQ|ONGC",
    "COALINDIA": "NSE_EQ|COALINDIA",
}

# ---------------------------------------------------------------------------
# TickBuffer
# ---------------------------------------------------------------------------

class TickBuffer:
    """Accumulates ticks for a single instrument into 1-min OHLCV bars.

    When a tick arrives in a new minute the previous bar is closed (its
    ``close`` is set to the incoming tick's LTP) and returned.  Completed
    bars are stored in ``self._completed`` and can be retrieved as a Polars
    DataFrame via ``get_latest_bars``.
    """

    def __init__(self):
        # _current[instrument_key] -> current open-bar dict
        self._current: dict[str, dict] = {}
        # _completed[instrument_key] -> list of closed-bar dicts
        self._completed: dict[str, list[dict]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Tick ingestion
    # ------------------------------------------------------------------

    def ingest(
        self,
        instrument_key: str,
        ltp: float,
        volume: int,
        oi: int,
        ts: datetime,
    ) -> Optional[dict]:
        """Process one tick.

        Returns the just-closed bar dict when a minute boundary has been
        crossed, otherwise ``None``.
        """
        current = self._current.get(instrument_key)

        if current is not None:
            prev_mk = self._minute_key(current["ts"])
            curr_mk = self._minute_key(ts)

            if prev_mk != curr_mk:
                # Minute boundary crossed — update current bar's close/high/low
                # with the incoming tick, then close it.
                current["close"] = ltp
                current["high"] = max(current["high"], ltp)
                current["low"] = min(current["low"], ltp)
                closed = dict(current)
                self._completed[instrument_key].append(closed)

                # Start new bar
                self._current[instrument_key] = self._make_bar(
                    instrument_key, ltp, volume, oi, ts,
                )
                return closed

            # Same minute — update OHLCV in-place
            current["high"] = max(current["high"], ltp)
            current["low"] = min(current["low"], ltp)
            current["close"] = ltp
            current["volume"] += volume
            current["oi"] = oi
            return None

        # First tick ever for this instrument
        self._current[instrument_key] = self._make_bar(
            instrument_key, ltp, volume, oi, ts,
        )
        return None

    # ------------------------------------------------------------------
    # Pre-load historical bars
    # ------------------------------------------------------------------

    def pre_load(self, instrument_key: str, bars_df: pl.DataFrame) -> None:
        """Load historical bars from a Polars DataFrame into the completed buffer.

        Expects columns: ``open``, ``high``, ``low``, ``close``, ``volume``
        (``ts`` and ``oi`` are optional).
        """
        for row in bars_df.iter_rows(named=True):
            self._completed[instrument_key].append({
                "instrument_key": instrument_key,
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row.get("volume", 0),
                "oi": row.get("oi", 0),
                "ts": row.get("ts", datetime.now(timezone.utc)),
            })

    # ------------------------------------------------------------------
    # Retrieve completed bars
    # ------------------------------------------------------------------

    def get_latest_bars(self, instrument_key: str, n: int = 100) -> pl.DataFrame:
        """Return the last *n* completed bars as a Polars DataFrame."""
        bars = self._completed.get(instrument_key, [])[-n:]
        if not bars:
            return pl.DataFrame(
                {"open": [], "high": [], "low": [], "close": [], "volume": []},
            )
        return pl.DataFrame(bars)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _minute_key(ts: datetime) -> str:
        return ts.strftime("%Y-%m-%dT%H:%M")

    @staticmethod
    def _make_bar(
        instrument_key: str, ltp: float, volume: int, oi: int, ts: datetime,
    ) -> dict:
        return {
            "instrument_key": instrument_key,
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp,
            "volume": volume,
            "oi": oi,
            "ts": ts,
        }


# ---------------------------------------------------------------------------
# BarAggregator
# ---------------------------------------------------------------------------

class BarAggregator:
    """Manages one :class:`TickBuffer` per symbol.

    Symbol-to-instrument-key mapping is provided at construction time.
    ``ingest_tick`` routes by instrument key; ``get_bars`` / ``pre_load``
    look up the buffer by symbol name.
    """

    def __init__(self, symbol_map: dict[str, str]):
        # {short_symbol: instrument_key}
        self.symbol_map = symbol_map
        # Reverse map for tick routing
        self._inst_to_sym: dict[str, str] = {ik: s for s, ik in symbol_map.items()}
        self._buffers: dict[str, TickBuffer] = {
            sym: TickBuffer() for sym in symbol_map
        }

    def ingest_tick(
        self,
        instrument_key: str,
        ltp: float,
        volume: int,
        oi: int,
        ts: datetime,
    ) -> Optional[dict]:
        """Route a tick to the correct buffer and return any closed bar."""
        sym = self._inst_to_sym.get(instrument_key)
        if sym is None:
            return None
        return self._buffers[sym].ingest(instrument_key, ltp, volume, oi, ts)

    def pre_load(self, symbol: str, bars_df: pl.DataFrame) -> None:
        """Pre-load historical bars for *symbol*."""
        buf = self._buffers.get(symbol)
        if buf is not None:
            buf.pre_load(symbol, bars_df)

    def get_bars(self, symbol: str, n: int = 100) -> pl.DataFrame:
        """Return the last *n* completed bars for *symbol*."""
        buf = self._buffers.get(symbol)
        if buf is None:
            return pl.DataFrame(
                {"open": [], "high": [], "low": [], "close": [], "volume": []},
            )
        return buf.get_latest_bars(symbol, n=n)


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------

NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"


class PipelineOrchestrator:
    """Drives the L1-L10 pipeline with real bar data.

    Three phase handlers (delegated by ``run_cycle``):

    * **pre-market** — cold-start: fetch yesterday's 1-min bars from Upstox
      REST for each symbol.
    * **live** — compute L3 indicators from real bars, score, rank, assemble
      theses, register in L9, edge lookup, and broadcast.
    * **closing** — force-expire L9, capture snapshot to Redis.
    """

    def __init__(self):
        self.symbol_map: dict[str, str] = SYMBOL_TO_INSTRUMENT_KEY.copy()
        self.session = market_session
        self.upstox_rest = upstox_rest
        self.cache = cache
        self.ws_manager = ws_manager

        self.aggregator = BarAggregator(self.symbol_map)

        # Layers
        self.l1 = L1MarketContext()
        self.l3 = L3Signals()
        self.l5 = L5Scoring()
        self.l6 = L6Ranking(top_n=25)
        self.l7 = L7Confluence()
        self.l8 = L8Thesis()
        self.l8_cost = L8CostModel()
        self.l9 = L9ShadowLedger()
        self.l10 = L10EdgeLookup()

        # Idempotency guard: pre-market backfill runs once
        self._pre_market_done: bool = False

        # Cached state (read by health / API routes)
        self.latest_context: Optional[MarketContextFrame] = None
        self.latest_long_rankings: list = []
        self.latest_short_rankings: list = []
        self.latest_theses: list[ThesisCard] = []

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run_cycle(self):
        """Dispatch to the appropriate phase handler."""
        phase = self.session.current_phase()
        if phase == "pre-market" and not self._pre_market_done:
            await self._run_pre_market_cycle()
        elif phase == "live":
            await self._run_live_cycle()
        elif phase == "closing":
            await self._run_closing_cycle()

    # ------------------------------------------------------------------
    # Phase: pre-market  (cold-start backfill)
    # ------------------------------------------------------------------

    async def _run_pre_market_cycle(self):
        """Fetch yesterday's 1-min bars for every symbol and pre-load.

        Uses asyncio.gather with a semaphore to limit concurrent REST calls.
        Sets ``_pre_market_done`` so subsequent cycles skip the backfill.
        """
        sem = asyncio.Semaphore(5)

        async def _fetch_one(sym: str, inst_key: str):
            async with sem:
                try:
                    resp = await self.upstox_rest.get_historical_candle(
                        inst_key, "1minute",
                    )
                    df = self._candle_json_to_df(resp)
                    if len(df) > 0:
                        self.aggregator.pre_load(sym, df)
                except Exception:
                    pass  # Gracefully skip unreachable symbols

        await asyncio.gather(
            *[_fetch_one(sym, key) for sym, key in self.symbol_map.items()],
            return_exceptions=True,
        )
        self._pre_market_done = True

    # ------------------------------------------------------------------
    # Phase: live  (full compute pipeline)
    # ------------------------------------------------------------------

    async def _run_live_cycle(self):
        now = datetime.now(timezone.utc)

        # 1. Fetch Nifty context data
        nifty_df = None
        try:
            nifty_resp = await self.upstox_rest.get_historical_candle(
                NIFTY_INDEX_KEY, "5minute",
            )
            nifty_df = self._candle_json_to_df(nifty_resp)
        except Exception:
            pass

        # 2. Per-symbol: L3 -> signals -> L5 score
        scored: list[dict] = []
        stock_data: dict[str, pl.DataFrame] = {}

        for sym in self.symbol_map:
            try:
                bars = self.aggregator.get_bars(sym, n=100)
                if len(bars) < 20:
                    continue  # Not enough bars for indicators

                # Convert to pandas for TA-lib / pandas_ta
                pd_df = bars.to_pandas()
                l3_df = self.l3.compute(pd_df)

                signals = self._extract_l3_signals(sym, l3_df)
                regime = self._current_regime()

                sector_data = self._synthetic_sector_data(sym)
                oi_data = {"classification": "Neutral"}

                result = self.l5.compute(signals, regime, sector_data, oi_data)
                result["instrument_key"] = self.symbol_map[sym]

                # L7: Confluence check (uses available bar + L3 data)
                conf_data = self._extract_confluence_data(pd_df, l3_df, signals)
                conf_score = self.l7.compute(conf_data)
                result["confluence_score"] = conf_score
                result["setup_type"] = random.randint(1, 6)
                result["actionability_tier"] = "Research-Only"
                result["liquidity_quality"] = random.choice(["Excellent", "Good", "Marginal"])

                scored.append(result)
                # L1.compute_breadth expects a "vwap" column
                stock_data[sym] = self._add_vwap_column(bars)

            except Exception:
                continue

        # 3. L1: market context
        vix_value = 15.0  # Placeholder — integrate real VIX feed later
        if nifty_df is not None and len(nifty_df) > 0 and stock_data:
            context = self.l1.compute(nifty_df, vix_value, stock_data)
        else:
            context = MarketContextFrame()
        self.latest_context = context

        # 4. L6: rank
        if scored:
            rankings = self.l6.rank(scored)
            longs = [r for r in rankings if r.net_rr > 0]
            shorts = [r for r in rankings if r.net_rr <= 0]
            self.latest_long_rankings = longs
            self.latest_short_rankings = shorts
        else:
            rankings = []
            longs = []
            shorts = []

        # 5. L8: assemble theses for top 5
        theses: list[ThesisCard] = []
        for rank_entry in rankings[:5]:
            bars_for_thesis = self.aggregator.get_bars(rank_entry.symbol, 20)
            if len(bars_for_thesis) < 2:
                continue
            recent = bars_for_thesis.tail(5)
            orb_high = float(recent["high"].max())
            orb_low = float(recent["low"].min())
            vwap_val = float(bars_for_thesis.tail(1)["close"][0])
            pdh = orb_high * 1.01
            direction = "LONG" if rank_entry.net_rr > 0 else "SHORT"

            thesis = self.l8.assemble(
                symbol=rank_entry.symbol,
                direction=direction,
                orb_high=orb_high,
                orb_low=orb_low,
                vwap=vwap_val,
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

            # L9: register & tick check
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
            l9_results = await self.l9.on_tick(mock_price)
            for r in l9_results:
                if r["state"] == "STOPPED_OUT":
                    await ws_manager.broadcast({
                        "type": "L9_INVALIDATION",
                        "timestamp": now.isoformat(),
                        "payload": {
                            "thesis_id": r["thesis_id"],
                            "reason": f"Stop loss hit at {mock_price:.2f}",
                        },
                    })

        self.latest_theses = theses

        # 6. L10: edge lookup
        regime_str = context.regime if hasattr(context, "regime") else "Range-Bound"
        edge_events = []
        for st in [SetupType.ORB_15MIN, SetupType.VWAP_RECLAIM, SetupType.SUPERTREND_PULLBACK]:
            for d in [Direction.LONG, Direction.SHORT]:
                reg = Regime(regime_str) if isinstance(regime_str, str) else regime_str
                edge = self.l10.lookup(st, reg, d)
                if edge["is_significant"]:
                    tier = st.value * 10 + (1 if d == Direction.LONG else 2)
                    edge_events.append({
                        "tier": tier,
                        "promotion": "PROMOTED" if edge["n"] >= 30 else "WATCH",
                    })

        # 7. Broadcast all
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

    # ------------------------------------------------------------------
    # Phase: closing  (force-expire + snapshot)
    # ------------------------------------------------------------------

    async def _run_closing_cycle(self):
        """Force-expire L9 active theses and snapshot state to Redis."""
        expired = await self.l9.on_force_expire()

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": (
                self.latest_context.model_dump()
                if self.latest_context
                else None
            ),
            "long_rankings": [
                r.model_dump() for r in self.latest_long_rankings
            ],
            "short_rankings": [
                r.model_dump() for r in self.latest_short_rankings
            ],
            "theses": [t.model_dump() for t in self.latest_theses],
            "expired_theses": expired,
            "l9_history_count": len(self.l9.history),
        }

        await self.cache.set("pipeline:closing_snapshot", snapshot)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _candle_json_to_df(data: dict) -> pl.DataFrame:
        """Convert Upstox historical-candle JSON to a Polars DataFrame.

        Expected format::

            {"data": {"candles": [
                ["2026-05-18T09:15:00+05:30", o, h, l, c, v],
                ...
            ]}}
        """
        candles = data.get("data", {}).get("candles", [])
        if not candles:
            return pl.DataFrame(
                {"open": [], "high": [], "low": [], "close": [], "volume": []},
            )

        rows = []
        for c in candles:
            rows.append({
                "ts": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            })
        return pl.DataFrame(rows)

    @staticmethod
    def _safe_float(val, default: float = 0.0) -> float:
        """Return *val* or *default* if NaN/None/inf."""
        if val is None:
            return default
        try:
            if np.isnan(val) or np.isinf(val):
                return default
        except (TypeError, ValueError):
            return default
        return float(val)

    @staticmethod
    def _safe_bool(val, default: bool = False) -> bool:
        """Return *val* as bool, or *default* if not convertible."""
        if val is None:
            return default
        try:
            return bool(val)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(val, default: int = 0) -> int:
        if val is None:
            return default
        try:
            v = int(val)
            return v
        except (TypeError, ValueError):
            return default

    def _extract_l3_signals(self, symbol: str, l3_df: pd.DataFrame) -> dict:
        """Extract L5-ready signal dict from an L3-computed DataFrame."""
        if len(l3_df) == 0:
            return self._default_signals(symbol)

        latest = l3_df.iloc[-1]

        # Direction from supertrend (1=bullish, -1=bearish)
        sd = self._safe_float(latest.get("supertrend_dir", 0))
        direction = "LONG" if sd == 1 else "SHORT"

        # Volume z-score
        vol = l3_df["volume"] if "volume" in l3_df.columns else pd.Series([0])
        vol_mean = vol.mean()
        vol_std = vol.std()
        vol_z = (vol.iloc[-1] - vol_mean) / vol_std if vol_std > 0 else 0

        return {
            "symbol": symbol,
            "ema_aligned": ema_aligned(l3_df),
            "supertrend_bull": direction == "LONG",
            "adx": self._safe_float(latest.get("adx")),
            "rsi": self._safe_float(latest.get("rsi"), 50.0),
            "macd_divergence": detect_macd_divergence(l3_df, direction.lower()),
            "roc_z": self._safe_float(latest.get("roc_20", 0)) / 100.0,
            "above_vwap": self._safe_bool(False),
            "vol_z": vol_z,
            "vol_confirm": self._safe_bool(False),
            "direction": direction,
            "bb_position": self._calc_bb_position(latest),
            "atr_pctile": 0.5,
            "dist_to_support": 0.0,
            "pos_52w": 0.5,
            "cpr_dist": 0.0,
        }

    @staticmethod
    def _default_signals(symbol: str) -> dict:
        return {
            "symbol": symbol,
            "ema_aligned": False,
            "supertrend_bull": False,
            "adx": 0,
            "rsi": 50,
            "macd_divergence": False,
            "roc_z": 0,
            "above_vwap": False,
            "vol_z": 0,
            "vol_confirm": False,
            "direction": "LONG",
            "bb_position": 0.5,
            "atr_pctile": 0.5,
            "dist_to_support": 0,
            "pos_52w": 0.5,
            "cpr_dist": 0,
        }

    @staticmethod
    def _calc_bb_position(latest: pd.Series) -> float:
        """Return BB position (0-1) indicating where close sits in the band."""
        upper = latest.get("bb_upper")
        lower = latest.get("bb_lower")
        close_val = latest.get("close")
        if any(v is None for v in (upper, lower, close_val)):
            return 0.5
        try:
            upper, lower, close_val = float(upper), float(lower), float(close_val)
            if upper == lower:
                return 0.5
            return (close_val - lower) / (upper - lower)
        except (TypeError, ValueError):
            return 0.5

    def _current_regime(self) -> str:
        """Return the regime string from the latest context, or a default."""
        if self.latest_context is not None:
            r = self.latest_context.regime
            return r.value if hasattr(r, "value") else str(r)
        return "Range-Bound"

    @staticmethod
    def _synthetic_sector_data(symbol: str) -> dict:
        """Placeholder sector data — replace with real L4 feed later."""
        return {"rank": random.randint(1, 11), "tailwind": random.random() > 0.7}

    @staticmethod
    def _extract_confluence_data(
        pd_df: pd.DataFrame,
        l3_df: pd.DataFrame,
        signals: dict,
    ) -> dict:
        """Build the data dict required by L7Confluence.compute().

        Uses the latest bar from *pd_df* (raw OHLCV), indicator values from
        *l3_df*, and the **direction** from *signals*.

        ``invalidation`` and ``t1`` are estimated from ATR since the true
        levels are not known until L8 assembles the thesis card.
        """
        if len(pd_df) == 0 or len(l3_df) == 0:
            return {}

        latest_bar = pd_df.iloc[-1]
        latest_idx = l3_df.iloc[-1]

        close_val = float(latest_bar["close"])
        atr_val = float(latest_idx.get("atr", 0))

        direction = signals.get("direction", "LONG")

        # Estimate invalidation and T1 from ATR (refined in L8)
        if direction == "LONG":
            invalidation = close_val - atr_val if atr_val > 0 else close_val * 0.99
            t1 = close_val + 1.5 * atr_val if atr_val > 0 else close_val * 1.01
        else:
            invalidation = close_val + atr_val if atr_val > 0 else close_val * 1.01
            t1 = close_val - 1.5 * atr_val if atr_val > 0 else close_val * 0.99

        return {
            "close": close_val,
            "high": float(latest_bar["high"]),
            "low": float(latest_bar["low"]),
            "volume": float(latest_bar["volume"]),
            "median_volume": float(pd_df["volume"].median()),
            "bar_range": float(latest_bar["high"] - latest_bar["low"]),
            "median_range": float((pd_df["high"] - pd_df["low"]).median()),
            "ema9": float(latest_idx.get("ema_9", close_val)),
            "ema20": float(latest_idx.get("ema_20", close_val)),
            "ema50": float(latest_idx.get("ema_50", close_val)),
            "price": close_val,
            "invalidation": round(invalidation, 2),
            "atr": atr_val,
            "t1": round(t1, 2),
            "direction": direction,
        }

    @staticmethod
    def _add_vwap_column(bars: pl.DataFrame) -> pl.DataFrame:
        """Add a ``vwap`` column to a Polars DataFrame if missing.

        VWAP is computed as the cumulative typical-price-volume /
        cumulative volume.
        """
        if "vwap" in bars.columns:
            return bars
        typical = (bars["high"] + bars["low"] + bars["close"]) / 3.0
        cum_tp_vol = (typical * bars["volume"]).cum_sum()
        cum_vol = bars["volume"].cum_sum()
        vwap = cum_tp_vol / cum_vol
        return bars.with_columns(vwap.alias("vwap"))

    async def handle_upstox_tick(self, raw_message: str):
        """Parse an Upstox V3 WebSocket tick and route to TickBuffer.ingest().

        Expected message format (Full mode):
          {"type": "full", "data": {"instrument_key": "...", "ltp": ...,
           "volume": ..., "oi": ..., "timestamp": "..."}}
        """
        try:
            msg = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            return

        data = msg.get("data", msg)
        if not isinstance(data, dict):
            return

        instrument_key = data.get("instrument_key")
        ltp = data.get("ltp") or data.get("last_price")
        if instrument_key is None or ltp is None:
            return

        volume = int(data.get("volume", 0) or 0)
        oi = int(data.get("oi", 0) or 0)
        ts_str = data.get("timestamp") or data.get("exchange_timestamp")
        if ts_str:
            ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        else:
            ts = datetime.now(timezone.utc)

        self.aggregator.ingest_tick(instrument_key, float(ltp), volume, oi, ts)


# Module-level singleton
pipeline = PipelineOrchestrator()
