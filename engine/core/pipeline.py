"""Intraday pipeline — TickBuffer, BarAggregator, and PipelineOrchestrator.

TickBuffer      Accumulates WebSocket ticks into 1-min OHLCV bars per instrument.
BarAggregator   Manages one TickBuffer per symbol.
PipelineOrchestrator  Drives L1-L10 layers with real bar data, market-session
                      awareness, cold-start backfill, and closing snapshots.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)

from api.websocket_manager import manager as ws_manager
from core.data.redis_cache import cache
from core.data.upstox_rest import upstox_rest
from core.data.nse_scraper import nse_scraper
from core.session.market_session import session as market_session, IST
from db.timescale import db as timescale_db
from layers.l1_market_context import L1MarketContext
from layers.l3_signals import L3Signals, ema_aligned, detect_macd_divergence
from layers.l4_sector import rank_sectors
from layers.l5_scoring import L5Scoring
from layers.l6_ranking import L6Ranking
from layers.l7_confluence import L7Confluence
from layers.l8_thesis import L8Thesis
from layers.l9_monitor import L9ShadowLedger
from layers.l10_edge import L10EdgeLookup
from models.enums import Direction, Regime, SetupType
from models.factors import (
    L2UniverseFrame, L3SignalFrame, L4SectorFrame,
    L5ScoreBreakdown, L6RankSnapshot, L7ConfluenceCheck,
    L8ThesisSnapshot, SymbolFactorBreakdown,
    PipelineLayerStatus, PipelineStatusResponse,
)
from models.frames import MarketContextFrame, ThesisCard

IST = timezone(timedelta(hours=5, minutes=30))

# 105 Nifty constituents with their Upstox instrument keys (ISIN-based).
SYMBOL_TO_INSTRUMENT_KEY: dict[str, str] = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "INFY": "NSE_EQ|INE009A01021",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "ITC": "NSE_EQ|INE154A01025",
    "LT": "NSE_EQ|INE018A01030",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "WIPRO": "NSE_EQ|INE075A01022",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "TITAN": "NSE_EQ|INE280A01028",
    "MARUTI": "NSE_EQ|INE585B01010",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "NTPC": "NSE_EQ|INE733E01010",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "TECHM": "NSE_EQ|INE669C01036",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "NESTLEIND": "NSE_EQ|INE239A01024",
    "JSWSTEEL": "NSE_EQ|INE019A01020",
    "TATASTEEL": "NSE_EQ|INE081A01020",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "ADANIENT": "NSE_EQ|INE423A01024",
    "ONGC": "NSE_EQ|INE213A01029",
    "COALINDIA": "NSE_EQ|INE522F01014",
    "BAJAJFINSV": "NSE_EQ|INE918I01026",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "HINDZINC": "NSE_EQ|INE267A01025",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "M&M": "NSE_EQ|INE101A01026",
    "TATACONSUM": "NSE_EQ|INE192A01025",
    "TRENT": "NSE_EQ|INE849A01020",
    "BEL": "NSE_EQ|INE263A01024",
    "HAL": "NSE_EQ|INE066F01020",
    "ADANIGREEN": "NSE_EQ|INE364U01010",
    "ADANIENSOL": "NSE_EQ|INE0RHD01013",
    "ADANIPOWER": "NSE_EQ|INE814H01011",
    "AMBUJACEM": "NSE_EQ|INE079A01024",
    "APOLLOHOSP": "NSE_EQ|INE437A01024",
    "AUROPHARMA": "NSE_EQ|INE406A01037",
    "BAJAJHLDNG": "NSE_EQ|INE118A01012",
    "BANKBARODA": "NSE_EQ|INE028A01039",
    "BHARATFORG": "NSE_EQ|INE465A01025",
    "BPCL": "NSE_EQ|INE029A01011",
    "BRITANNIA": "NSE_EQ|INE216A01030",
    "CANBK": "NSE_EQ|INE476A01022",
    "CHOLAFIN": "NSE_EQ|INE121A01024",
    "CIPLA": "NSE_EQ|INE059A01026",
    "COLPAL": "NSE_EQ|INE259A01022",
    "DABUR": "NSE_EQ|INE016A01026",
    "DIVISLAB": "NSE_EQ|INE361B01024",
    "DLF": "NSE_EQ|INE271C01023",
    "DRREDDY": "NSE_EQ|INE089A01023",
    "EICHERMOT": "NSE_EQ|INE066A01021",
    "GAIL": "NSE_EQ|INE129A01019",
    "GODREJCP": "NSE_EQ|INE102D01028",
    "GRASIM": "NSE_EQ|INE047A01021",
    "HAVELLS": "NSE_EQ|INE176B01034",
    "HDFCLIFE": "NSE_EQ|INE795G01014",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "HINDALCO": "NSE_EQ|INE038A01020",
    "HINDPETRO": "NSE_EQ|INE094A01026",
    "ICICIPRULI": "NSE_EQ|INE726G01019",
    "ICICIGI": "NSE_EQ|INE874N01028",
    "INDIGO": "NSE_EQ|INE646L01027",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "IOC": "NSE_EQ|INE242A01010",
    "IRFC": "NSE_EQ|INE053F01010",
    "JINDALSTEL": "NSE_EQ|INE749A01030",
    "JIOFIN": "NSE_EQ|INE758E01017",
    "LICHSGFIN": "NSE_EQ|INE115A01026",
    "LTIM": "NSE_EQ|INE214T01019",
    "LUPIN": "NSE_EQ|INE326A01037",
    "MARICO": "NSE_EQ|INE196A01026",
    "MAXHEALTH": "NSE_EQ|INE027H01010",
    "MOTHERSON": "NSE_EQ|INE775A01035",
    "MPHASIS": "NSE_EQ|INE356A01018",
    "MRF": "NSE_EQ|INE883A01011",
    "NAUKRI": "NSE_EQ|INE663F01024",
    "NAVINFLUOR": "NSE_EQ|INE048G01026",
    "NYKAA": "NSE_EQ|INE145A01016",
    "OIL": "NSE_EQ|INE274J01014",
    "PAYTM": "NSE_EQ|INE982J01020",
    "PEL": "NSE_EQ|INE140A01024",
    "PIDILITIND": "NSE_EQ|INE318A01026",
    "PNB": "NSE_EQ|INE160A01022",
    "POLYCAB": "NSE_EQ|INE455K01017",
    "RECLTD": "NSE_EQ|INE020B01018",
    "SBICARD": "NSE_EQ|INE018E01016",
    "SBILIFE": "NSE_EQ|INE123W01016",
    "SHRIRAMFIN": "NSE_EQ|INE721A01013",
    "SIEMENS": "NSE_EQ|INE003A01024",
    "SRF": "NSE_EQ|INE647A01010",
    "TATAPOWER": "NSE_EQ|INE245A01021",
    "TORNTPHARM": "NSE_EQ|INE685A01028",
    "TVSMOTOR": "NSE_EQ|INE494B01023",
    "UPL": "NSE_EQ|INE628A01036",
    "VEDL": "NSE_EQ|INE205A01025",
    "ZOMATO": "NSE_EQ|INE758T01015",
    "ZYDUSLIFE": "NSE_EQ|INE010B01027",
}

# Per-symbol sector assignment for L4 sector-RS lookup.
#
# Maps each of the 105 symbols in SYMBOL_TO_INSTRUMENT_KEY to ONE of the 11
# sector keys in SECTOR_INDEX_MAP (Auto / Bank / FMCG / IT / Media / Metal /
# Pharma / PSU Bank / Realty / Energy / Telecom).
#
# Grouping rules for stocks without an exact NSE sector index match
# (no "Power", "Insurance", "Cement", "Aviation", "ConsumerDurables", or
# "Financials" index exists in SECTOR_INDEX_MAP):
#
#   * Power utilities      -> "Energy"   (NTPC, POWERGRID, TATAPOWER,
#                                        ADANIPOWER, ADANIGREEN, ADANIENSOL)
#   * Cement / Building    -> "Metal"    (ULTRACEMCO, AMBUJACEM, GRASIM)
#   * Insurance / NBFC     -> "Bank"     (HDFCLIFE, ICICIPRULI, ICICIGI,
#                                        SBILIFE, BAJAJFINSV, BAJAJHLDNG,
#                                        BAJFINANCE, CHOLAFIN, SHRIRAMFIN,
#                                        SBICARD, LICHSGFIN, IRFC, RECLTD,
#                                        JIOFIN)
#   * Aviation             -> "Energy"   (INDIGO; fuel-cost-sensitive proxy)
#   * Consumer Durables /  -> "FMCG"     (ASIANPAINT, HAVELLS, POLYCAB,
#     Paints                              TITAN, PIDILITIND)
#   * Retail / Platforms   -> "FMCG"     (TRENT, NYKAA - consumer)
#   * Internet / Platforms -> "IT"       (NAUKRI, ZOMATO, PAYTM)
#   * Agri / Specialty     -> "FMCG" or "Metal" depending on closest fit
#     chemicals
#   * Capital goods /      -> "Auto" or "Metal" depending on closest fit
#     industrials                       (BEL, HAL, SIEMENS, BHARATFORG)
#
# Default fallback for any symbol not present here is "Bank" (preserves the
# pre-Fix-4 behaviour).
SYMBOL_TO_SECTOR: dict[str, str] = {
    # --- Energy / Oil & Gas / Power utilities ---
    "RELIANCE": "Energy",       # Oil & gas major
    "ONGC": "Energy",           # Oil exploration
    "COALINDIA": "Energy",      # Coal / energy
    "BPCL": "Energy",           # Oil refining
    "HINDPETRO": "Energy",      # Oil refining
    "IOC": "Energy",            # Oil refining
    "GAIL": "Energy",           # Gas transmission
    "OIL": "Energy",            # Oil India
    "NTPC": "Energy",           # Power utility (proxy: Energy)
    "POWERGRID": "Energy",      # Power transmission (proxy: Energy)
    "TATAPOWER": "Energy",      # Power utility (proxy: Energy)
    "ADANIPOWER": "Energy",     # Power utility (proxy: Energy)
    "ADANIGREEN": "Energy",     # Renewable power (proxy: Energy)
    "ADANIENSOL": "Energy",     # Power transmission (proxy: Energy)
    "INDIGO": "Energy",         # Aviation (fuel-cost-sensitive proxy: Energy)

    # --- Banks (private + general) ---
    "HDFCBANK": "Bank",
    "ICICIBANK": "Bank",
    "KOTAKBANK": "Bank",
    "AXISBANK": "Bank",
    "INDUSINDBK": "Bank",

    # --- PSU Banks ---
    "SBIN": "PSU Bank",
    "BANKBARODA": "PSU Bank",
    "CANBK": "PSU Bank",
    "PNB": "PSU Bank",

    # --- NBFCs / Insurance / financial services (proxy: Bank) ---
    "BAJFINANCE": "Bank",       # NBFC (proxy: Bank)
    "BAJAJFINSV": "Bank",       # Financial services holding (proxy: Bank)
    "BAJAJHLDNG": "Bank",       # Bajaj holdings (proxy: Bank)
    "CHOLAFIN": "Bank",         # NBFC (proxy: Bank)
    "SHRIRAMFIN": "Bank",       # NBFC (proxy: Bank)
    "SBICARD": "Bank",          # Credit cards (proxy: Bank)
    "LICHSGFIN": "Bank",        # Housing finance (proxy: Bank)
    "IRFC": "Bank",             # Railway finance (proxy: Bank)
    "RECLTD": "Bank",           # Power finance (proxy: Bank)
    "JIOFIN": "Bank",           # Digital financial services (proxy: Bank)
    "HDFCLIFE": "Bank",         # Life insurance (proxy: Bank)
    "ICICIPRULI": "Bank",       # Life insurance (proxy: Bank)
    "ICICIGI": "Bank",          # General insurance (proxy: Bank)
    "SBILIFE": "Bank",          # Life insurance (proxy: Bank)

    # --- IT / Tech / Internet platforms ---
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "MPHASIS": "IT",
    "NAUKRI": "IT",             # Internet platform (proxy: IT)
    "ZOMATO": "IT",             # Internet platform (proxy: IT)
    "PAYTM": "IT",              # Digital payments / fintech platform (proxy: IT)

    # --- Auto / Auto ancillaries ---
    "MARUTI": "Auto",
    "M&M": "Auto",
    "TATAMOTORS": "Auto",
    "BAJAJ-AUTO": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",
    "TVSMOTOR": "Auto",
    "MOTHERSON": "Auto",        # Auto ancillary
    "BHARATFORG": "Auto",       # Auto / industrial forgings (proxy: Auto)
    "MRF": "Auto",              # Tyres (proxy: Auto)

    # --- FMCG / Consumer staples / Consumer durables / Paints ---
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",
    "DABUR": "FMCG",
    "MARICO": "FMCG",
    "COLPAL": "FMCG",
    "GODREJCP": "FMCG",
    "TATACONSUM": "FMCG",
    "TITAN": "FMCG",            # Jewellery / lifestyle (proxy: FMCG)
    "ASIANPAINT": "FMCG",       # Paints (proxy: FMCG - consumer)
    "PIDILITIND": "FMCG",       # Adhesives / consumer chemicals (proxy: FMCG)
    "HAVELLS": "FMCG",          # Consumer durables (proxy: FMCG)
    "POLYCAB": "FMCG",          # Cables / consumer durables (proxy: FMCG)
    "TRENT": "FMCG",            # Retail (proxy: FMCG)
    "NYKAA": "FMCG",            # Beauty retail (proxy: FMCG)

    # --- Pharma / Healthcare ---
    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "DIVISLAB": "Pharma",
    "LUPIN": "Pharma",
    "AUROPHARMA": "Pharma",
    "TORNTPHARM": "Pharma",
    "ZYDUSLIFE": "Pharma",
    "APOLLOHOSP": "Pharma",     # Healthcare (proxy: Pharma)
    "MAXHEALTH": "Pharma",      # Healthcare (proxy: Pharma)

    # --- Metal / Mining / Cement (building materials) ---
    "TATASTEEL": "Metal",
    "JSWSTEEL": "Metal",
    "JINDALSTEL": "Metal",
    "HINDALCO": "Metal",
    "HINDZINC": "Metal",
    "VEDL": "Metal",
    "ULTRACEMCO": "Metal",      # Cement (proxy: Metal - building material)
    "AMBUJACEM": "Metal",       # Cement (proxy: Metal - building material)
    "GRASIM": "Metal",          # Cement + chemicals (proxy: Metal)

    # --- Telecom ---
    "BHARTIARTL": "Telecom",

    # --- Realty / Real estate ---
    "DLF": "Realty",

    # --- Industrials / Capital goods / Defence (proxy: Auto / Metal) ---
    "LT": "Auto",               # Engineering / construction (proxy: Auto -
                                # the closest "industrial" index available)
    "BEL": "Auto",              # Defence electronics (proxy: Auto -
                                # industrial / capital goods)
    "HAL": "Auto",              # Defence aerospace (proxy: Auto - industrial)
    "SIEMENS": "Auto",          # Industrial automation (proxy: Auto -
                                # industrial / capital goods)

    # --- Diversified / Specialty (best-fit by primary revenue source) ---
    "ADANIPORTS": "Energy",     # Ports / logistics; Adani conglomerate
                                # (proxy: Energy - infrastructure)
    "ADANIENT": "Energy",       # Diversified Adani group flagship
                                # (proxy: Energy - infrastructure)
    "SRF": "Metal",             # Specialty chemicals / fluorochemicals
                                # (proxy: Metal - industrial materials)
    "NAVINFLUOR": "Metal",      # Specialty chemicals / fluorochemicals
                                # (proxy: Metal - industrial materials)
    "UPL": "FMCG",              # Agro chemicals (proxy: FMCG - consumer ag)
    "PEL": "Pharma",            # Piramal Enterprises - pharma + financials
                                # (proxy: Pharma - historic primary biz)
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
        # Normalize ts precision: mix of REST (ms) and WS (μs) timestamps
        # can cause Polars ComputeError when building the DataFrame.
        for b in bars:
            if isinstance(b.get("ts"), datetime):
                b["ts"] = b["ts"].replace(microsecond=0)
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
            inst_key = self.symbol_map.get(symbol, symbol)
            buf.pre_load(inst_key, bars_df)

    def get_bars(self, symbol: str, n: int = 100) -> pl.DataFrame:
        """Return the last *n* completed bars for *symbol*."""
        buf = self._buffers.get(symbol)
        if buf is None:
            return pl.DataFrame(
                {"open": [], "high": [], "low": [], "close": [], "volume": []},
            )
        inst_key = self.symbol_map.get(symbol, symbol)
        return buf.get_latest_bars(inst_key, n=n)


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------

NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"

SECTOR_INDEX_MAP: dict[str, str] = {
    "Auto": "NSE_INDEX|Nifty Auto",
    "Bank": "NSE_INDEX|Nifty Bank",
    "FMCG": "NSE_INDEX|Nifty FMCG",
    "IT": "NSE_INDEX|Nifty IT",
    "Media": "NSE_INDEX|Nifty Media",
    "Metal": "NSE_INDEX|Nifty Metal",
    "Pharma": "NSE_INDEX|Nifty Pharma",
    "PSU Bank": "NSE_INDEX|Nifty PSU Bank",
    "Realty": "NSE_INDEX|Nifty Realty",
    "Energy": "NSE_INDEX|Nifty Energy",
    "Telecom": "NSE_INDEX|Nifty Telecom",
}


def _check_earnings_today(symbol: str, earnings_data: list) -> str:
    """Check if symbol has earnings announcement today."""
    from datetime import date
    today_str = date.today().isoformat()
    for item in earnings_data or []:
        if item.get("symbol") == symbol and item.get("date") == today_str:
            return "Earnings"
    return "None"


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
        self.l9 = L9ShadowLedger()
        self.l10 = L10EdgeLookup()

        # Idempotency guard: pre-market backfill runs once
        self._pre_market_done: bool = False

        # Cached state (read by health / API routes)
        self.latest_context: Optional[MarketContextFrame] = None
        self.latest_long_rankings: list = []
        self.latest_short_rankings: list = []
        self.latest_theses: list[ThesisCard] = []

        # Cycle number for funnel / activity / status
        self._cycle_number: int = 0

        # Telemetry realness tracking (updated each cycle)
        self._l2_flags_populated: bool = False
        self._sector_rs_real: bool = False
        self._bars_persisted: bool = False

        # In-memory factors cache: scored entries from last cycle so the
        # /rankings/{symbol}/factors endpoint can serve real data without Redis.
        self._latest_scored: list[dict] = []

        # In-memory activity feed: events from pipeline cycles so
        # /activity/events can serve real data without Redis.
        self._activity_events: list[dict] = []

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run_cycle(self):
        """Dispatch to the appropriate phase handler.

        Phase "closed" runs a one-shot bootstrap when the engine starts after
        15:30 IST so the dashboard has real (stale) data to render until the
        next market open — instead of sitting on cycle_number=0 and forcing
        every endpoint into the mock-fallback branch.
        """
        phase = self.session.current_phase()
        if phase == "pre-market" and not self._pre_market_done:
            await self._run_pre_market_cycle()
        elif phase == "live":
            await self._run_live_cycle()
        elif phase == "closing":
            await self._run_closing_cycle()
        elif phase == "closed" and self._cycle_number == 0:
            # Bootstrap: backfill yesterday's bars, then run one scoring pass.
            logger.info("[Pipeline] Closed-phase bootstrap — backfilling + 1 scoring cycle")
            if not self._pre_market_done:
                await self._run_pre_market_cycle()
            await self._run_live_cycle()

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
            nonlocal success, fail
            async with sem:
                try:
                    resp = await self.upstox_rest.get_historical_candle(
                        inst_key, "1minute",
                    )
                    df = self._candle_json_to_df(resp)
                    if len(df) > 0:
                        self.aggregator.pre_load(sym, df)
                        success += 1
                except Exception as e:
                    fail += 1
                    logger.warning("[PreMarket] %s: fetch failed — %s", sym, str(e)[:120])

        success = 0
        fail = 0
        await asyncio.gather(
            *[_fetch_one(sym, key) for sym, key in self.symbol_map.items()],
            return_exceptions=True,
        )
        logger.info(
            "[PreMarket] backfill complete — success=%d fail=%d total=%d",
            success, fail, len(self.symbol_map),
        )
        self._pre_market_done = True

    def _try_assemble_thesis(self, symbol: str, direction: str, bars_df,
                              pd_df, l3_df, signals: dict,
                              l2_flags: dict, sector_data: dict) -> ThesisCard | None:
        """Try all 6 setup assemblers; return first passing thesis or None."""
        if len(bars_df) < 5:
            return None

        recent = bars_df.tail(5)
        close = float(recent["close"][-1])
        orb_high = float(recent["high"].max())
        orb_low = float(recent["low"].min())
        pdh = orb_high * 1.01
        pdl = orb_low * 0.99
        atr_val = signals.get("atr", max((orb_high - orb_low) * 0.5, 1.0))
        signals["direction"] = direction

        thesis_errs = 0
        first_thesis_err = None
        for setup_type in range(1, 7):
            try:
                thesis = self.l8.assemble(
                    symbol=symbol,
                    direction=direction,
                    setup_type=setup_type,
                    setup_params={
                        "orb_high": orb_high, "orb_low": orb_low,
                        "vwap": signals.get("vwap", close),
                        "pdh": pdh, "pdl": pdl,
                        "close": close, "atr": atr_val,
                    },
                    confluence_data=self._extract_confluence_data(pd_df, l3_df, signals),
                    cost_params={
                        "qty": 100, "lot_size": 50,
                        "futures": l2_flags.get("fo_eligible", True),
                        "liquidity_quality": l2_flags.get("liquidity_quality", "Good"),
                        "fo_ban": l2_flags.get("fo_ban", False),
                        "shortability": l2_flags.get("shortability", "FUTURES_OPTIONS"),
                    },
                )
                if thesis.trigger > 0 and thesis.invalidation > 0:
                    return thesis
            except Exception as e:
                thesis_errs += 1
                if first_thesis_err is None:
                    first_thesis_err = str(e)[:120]
                continue
        if thesis_errs and first_thesis_err:
            logger.warning(
                "[Pipeline] Thesis assembly errors for %s: %d/6 setups failed, first=%s",
                symbol, thesis_errs, first_thesis_err,
            )
        return None

    # ------------------------------------------------------------------
    # Phase: live  (full compute pipeline)
    # ------------------------------------------------------------------

    async def _run_live_cycle(self):
        now = datetime.now(timezone.utc)
        self._cycle_number += 1
        self.last_cycle_at = now

        # L2: Fetch NSE flags once per cycle (cached for all symbols)
        l2_flags: dict[str, dict] = {}
        try:
            fo_ban_list = await nse_scraper.get_fo_ban_list()
            earnings_data = await nse_scraper.get_corporate_actions()
            mwpl_list = await nse_scraper.get_mwpl()
            for sym in self.symbol_map:
                l2_flags[sym] = {
                    "fo_ban": sym in fo_ban_list,
                    "mwpl": "MWPL" if sym in mwpl_list else "None",
                    "earnings": _check_earnings_today(sym, earnings_data),
                }
        except Exception:
            l2_flags = {}
        self._l2_flags_populated = len(l2_flags) > 0

        # One-time backfill: fetch historical candles for symbols with < 20 bars
        if not getattr(self, '_live_backfill_done', False):
            self._live_backfill_done = True
            backfill_count = 0
            bf_errs = 0
            first_err = None
            for sym, inst_key in self.symbol_map.items():
                try:
                    existing = self.aggregator.get_bars(sym, n=200)
                    if len(existing) < 20:
                        resp = await self.upstox_rest.get_historical_candle(inst_key, "1minute")
                        df = self._candle_json_to_df(resp)
                        if len(df) > 0:
                            self.aggregator.pre_load(sym, df)
                            backfill_count += 1
                except Exception as e:
                    bf_errs += 1
                    if first_err is None:
                        first_err = str(e)[:120]
            logger.info(
                "[Pipeline] Live backfill: loaded=%d errors=%d",
                backfill_count, bf_errs,
            )
            if first_err:
                logger.warning("[Pipeline] Live backfill first error: %s", first_err)

        # 1. Fetch Nifty context data
        nifty_df = None
        try:
            nifty_resp = await self.upstox_rest.get_historical_candle(
                NIFTY_INDEX_KEY, "1minute",
            )
            nifty_df = self._candle_json_to_df(nifty_resp)
        except Exception:
            pass

        # L4: Compute real sector RS from sector index feeds
        real_sector_data: dict[str, dict] = {}
        try:
            sector_returns: dict[str, float] = {}
            sector_histories: dict[str, list] = {}
            for sector_name, index_key in SECTOR_INDEX_MAP.items():
                try:
                    resp = await self.upstox_rest.get_historical_candle(index_key, "1minute")
                    df = self._candle_json_to_df(resp)
                    if len(df) >= 5:
                        close = df["close"].to_numpy()
                        sector_returns[sector_name] = float((close[-1] - close[0]) / close[0])
                        sector_histories[sector_name] = (
                            [float((close[i] - close[i-5]) / close[i-5])
                             for i in range(5, len(close), 5)]
                            if len(close) >= 25 else
                            [float((close[-1] - close[0]) / close[0])]
                        )
                except Exception:
                    continue
            if sector_returns:
                nifty_5min_return = float(
                    (nifty_df["close"].to_numpy()[-1] - nifty_df["close"].to_numpy()[0])
                    / nifty_df["close"].to_numpy()[0]
                ) if nifty_df is not None and len(nifty_df) >= 5 else 0.0
                ranked_sectors = rank_sectors(sector_returns, nifty_5min_return, sector_histories)
                for entry in ranked_sectors:
                    real_sector_data[entry["sector"]] = entry
        except Exception:
            pass
        self._sector_rs_real = len(real_sector_data) > 0

        # 2. Per-symbol: L3 -> signals -> L5 score
        scored: list[dict] = []
        stock_data: dict[str, pl.DataFrame] = {}
        bars_ok = 0
        bars_skip = 0
        l3_err = 0

        for sym in self.symbol_map:
            try:
                bars = self.aggregator.get_bars(sym, n=100)
                if len(bars) < 20:
                    bars_skip += 1
                    continue

                bars_ok += 1
                # Convert to pandas for TA-lib / pandas_ta
                pd_df = bars.to_pandas()
                l3_df = self.l3.compute(pd_df)

                signals = self._extract_l3_signals(sym, l3_df)
                flags = l2_flags.get(sym, {})
                signals["fo_ban"] = flags.get("fo_ban", False)
                signals["earnings"] = flags.get("earnings") == "Earnings"
                regime = self._current_regime()

                sector_name = SYMBOL_TO_SECTOR.get(sym, "Bank")
                sector_data = real_sector_data.get(sector_name, {"rank": 6, "tailwind": False})
                oi_data = {"classification": "Neutral"}

                result = self.l5.compute(signals, regime, sector_data, oi_data)
                result["instrument_key"] = self.symbol_map[sym]

                # L7: Confluence check (uses available bar + L3 data)
                conf_data = self._extract_confluence_data(pd_df, l3_df, signals)
                conf_score = self.l7.compute(conf_data)
                result["confluence_score"] = conf_score
                result["setup_type"] = 1  # Default placeholder; overwritten by L8 thesis assembly
                result["direction"] = signals.get("direction", "LONG")
                result["net_rr"] = max(0.2, conf_score * 0.35)
                result["sector_name"] = sector_name
                result["sector_id"] = sector_data.get("rank", 6)
                result["actionability_tier"] = "Research-Only"
                # Compute liquidity quality from bar volume data
                vol_series = bars["volume"].to_numpy()
                avg_vol = float(np.mean(vol_series)) if len(vol_series) > 0 else 0
                result["liquidity_quality"] = "Good"  # Default; enriched when depth feed wired

                scored.append(result)
                # L1.compute_breadth expects a "vwap" column
                stock_data[sym] = self._add_vwap_column(bars)

            except Exception:
                l3_err += 1
                continue

        logger.info(
            "[Pipeline] cycle=%d scored=%d bars_ok=%d bars_skip=%d l3_err=%d",
            self._cycle_number, len(scored), bars_ok, bars_skip, l3_err,
        )

        # 3. L1: market context
        # Real VIX from Upstox historical candles (LTPC endpoint not available)
        vix_value = 15.0
        try:
            vix_candle_resp = await self.upstox_rest.get_historical_candle(
                "NSE_INDEX|India VIX", "1minute",
            )
            vix_candles = vix_candle_resp.get("data", {}).get("candles", [])
            if vix_candles:
                vix_value = float(vix_candles[-1][4])  # close of last candle
        except Exception:
            pass  # Keep fallback value on fetch failure

        # Bank Nifty divergence
        bank_nifty_divergence = 0.0
        try:
            bn_df = None
            bn_resp = None
            try:
                bn_resp = await self.upstox_rest.get_historical_candle(
                    "NSE_INDEX|Nifty Bank", "1minute",
                )
                bn_df = self._candle_json_to_df(bn_resp)
            except Exception:
                pass
            if nifty_df is not None and bn_df is not None and len(nifty_df) >= 5 and len(bn_df) >= 5:
                nifty_close = nifty_df["close"].to_numpy()
                bn_close = bn_df["close"].to_numpy()
                nifty_ret = float((nifty_close[-1] - nifty_close[-5]) / nifty_close[-5])
                bn_ret = float((bn_close[-1] - bn_close[-5]) / bn_close[-5])
                bank_nifty_divergence = round(bn_ret - nifty_ret, 4)
        except Exception:
            pass

        # event_flag from earnings
        event_flag = None
        try:
            earnings_today = [sym for sym, flags in l2_flags.items()
                            if flags.get("earnings") == "Earnings"]
            if earnings_today:
                event_flag = f"Earnings: {', '.join(earnings_today[:5])}"
        except Exception:
            pass

        if nifty_df is not None and len(nifty_df) > 0 and stock_data:
            context = self.l1.compute(
                nifty_df, vix_value, stock_data,
                event_flag=event_flag,
                bank_nifty_divergence=bank_nifty_divergence,
                phase=self.session.current_phase(),
                data_as_of=now.astimezone(IST),
            )
        else:
            context = MarketContextFrame(vix_value=vix_value, data_as_of=now.astimezone(IST))
        self.latest_context = context
        logger.info(
            "[Pipeline] L1 context: regime=%s vix=%.2f breadth=%s bucket=%s",
            context.regime, context.vix_value, context.breadth, context.time_bucket,
        )

        # 4. L6: rank (returns tuple[list, dict] with metrics)
        if scored:
            rankings, ranking_metrics = self.l6.rank(scored)
            longs = [r for r in rankings if r.direction == Direction.LONG]
            shorts = [r for r in rankings if r.direction == Direction.SHORT]
            self.latest_long_rankings = longs
            self.latest_short_rankings = shorts
            self._latest_scored = scored
            logger.info(
                "[Pipeline] L6 rankings: long=%d short=%d",
                len(longs), len(shorts),
            )
        else:
            rankings = []
            ranking_metrics = {}
            longs = []
            shorts = []
            logger.warning("[Pipeline] L6 rankings: scored empty, no rankings produced")

        # Push activity events to Redis
        try:
            cycle_num = self._cycle_number
            for r in rankings:
                movement_str = r.rank_movement.value if hasattr(r.rank_movement, 'value') else str(r.rank_movement)
                if movement_str in ("NEW", "UP", "DOWN"):
                    event = {
                        "id": f"{now.timestamp()}-{r.symbol}",
                        "ts": now.isoformat(),
                        "type": movement_str,
                        "symbol": r.symbol,
                        "direction": r.direction.value if hasattr(r.direction, 'value') else str(r.direction),
                        "text": f"{r.symbol} {movement_str} (score {r.score:.1f})",
                        "detail": f"Rank movement, score {r.score:.1f}",
                        "cycle": cycle_num,
                    }
                    self._activity_events.append(event)
                    await self.cache.client.lpush("pipeline:activity", json.dumps(event))
            # Trim in-memory events to last 200
            if len(self._activity_events) > 200:
                self._activity_events = self._activity_events[-200:]
            await self.cache.client.ltrim("pipeline:activity", 0, 199)
        except Exception:
            pass

        # 5. L8: assemble theses for stocks with score >= 40
        theses: list[ThesisCard] = []
        for rank_entry in rankings[:10]:  # Top 10, limit active theses
            sym = rank_entry.symbol
            bars = self.aggregator.get_bars(sym, 20)
            if len(bars) < 5:
                continue

            pd_df = bars.to_pandas()
            l3_df = self.l3.compute(pd_df)
            sigs = self._extract_l3_signals(sym, l3_df)
            direction = rank_entry.direction.value if hasattr(rank_entry.direction, 'value') else str(rank_entry.direction)
            sigs["direction"] = direction

            thesis = self._try_assemble_thesis(
                sym, direction, bars, pd_df, l3_df, sigs,
                l2_flags.get(sym, {}),
                real_sector_data.get(
                    SYMBOL_TO_SECTOR.get(sym, "Bank"),
                    {"rank": 6, "tailwind": False},
                ),
            )
            if thesis is None:
                continue

            theses.append(thesis)

            # L9: register in shadow ledger
            await self.l9.on_create({
                "thesis_id": thesis.thesis_id,
                "symbol": thesis.symbol,
                "direction": thesis.direction.value,
                "setup_type": thesis.setup_type.value,
                "trigger": thesis.trigger,
                "invalidation": thesis.invalidation,
                "t1": thesis.t1,
                "t2": thesis.t2,
                "sector": SYMBOL_TO_SECTOR.get(sym, "Bank"),
                "time_bucket": context.time_bucket if hasattr(context, "time_bucket") else "Trend Establishment",
                "regime": context.regime if hasattr(context, "regime") else "Range-Bound",
                "cost_breakdown": thesis.cost_breakdown,
            })

        self.latest_theses = theses

        # 6. L10: populate from DB then edge lookup
        await self.l10.populate_from_db()
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

        # Cache funnel counts to Redis
        try:
            funnel = {
                "L1": {"in": 1, "out": 1},
                "L2": {"in": len(self.symbol_map), "out": len(scored)},
                "L3": {"in": len(scored), "out": len(scored)},
                "L4": {"in": len(scored), "out": len(scored)},
                "L5": {"in": len(scored), "out": len(scored)},
                "L6": {"in": len(scored), "out": len(rankings)},
                "L7": {"in": len(rankings), "out": len(rankings)},
                "L8": {"in": len(rankings), "out": len(theses)},
                "L9": {"in": len(theses), "out": len(self.l9.active)},
                "L10": {"in": len(theses), "out": len(theses)},
            }
            await self.cache.set("pipeline:funnel_counts", funnel)
        except Exception:
            pass

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

        # Broadcast funnel counts via WS
        try:
            await ws_manager.broadcast_funnel_counts(funnel)
        except Exception:
            pass

        # Broadcast alert for each thesis
        for thesis in theses:
            try:
                await ws_manager.broadcast_alert(
                    "triggered", thesis.symbol,
                    f"{thesis.symbol} {thesis.direction.value} thesis triggered @ {thesis.trigger:.2f}"
                )
            except Exception:
                pass

        # 8. Write factor breakdowns and pipeline status to Redis
        try:
            long_symbols = {r.symbol for r in longs}
            for scored_entry in scored:
                sym = scored_entry["symbol"]
                direction = Direction.LONG if sym in long_symbols else Direction.SHORT
                factors = scored_entry.get("factors", {})
                await self._write_factors_to_redis(
                    symbol=sym,
                    direction=direction,
                    l5=L5ScoreBreakdown(
                        total=scored_entry.get("score", 0),
                        f1_trend=factors.get("f1", 0),
                        f2_momentum=factors.get("f2", 0),
                        f3_volume=factors.get("f3", 0),
                        f4_volpos=factors.get("f4", 0),
                        f5_structure=factors.get("f5", 0),
                        f6_sector=factors.get("f6", 0),
                        f7_risk=factors.get("f7", 0),
                        regime=self._current_regime(),
                        modifiers=scored_entry.get("modifiers", {}),
                    ),
                    l6=L6RankSnapshot(
                        liquidity_quality=scored_entry.get("liquidity_quality", "Good"),
                    ),
                    l7=L7ConfluenceCheck(
                        score=scored_entry.get("confluence_score", 0),
                        max=6,
                    ),
                )
                break  # Only write first symbol for now to keep cycle fast

            await self._write_pipeline_status({
                # TODO: measure actual per-layer durations
                "l1_market_context": 0,
                "l2_universe": 0,
                "l3_signals": 0,
                "l4_sector": 0,
                "l5_scoring": 0,
                "l6_ranking": 0,
                "l7_confluence": 0,
                "l8_thesis": 0,
                "l9_monitor": 0,
                "l10_edge": 0,
            })
        except Exception:
            pass  # Redis writes are non-critical cache augmentations

        # Persist closed bars to TimescaleDB so /market/candles has real data
        try:
            await self._persist_bars()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_bars(self):
        """Write closed bars from the aggregator into TimescaleDB ``market_bars``.

        Uses ON CONFLICT DO NOTHING so re-persisting the same bars across
        cycles is harmless.  Sets ``_bars_persisted`` on first success so
        the telemetry predicate flips to ``pipeline``.
        """
        if timescale_db.pool is None:
            return
        inserted = 0
        errors = 0
        for sym, inst_key in self.symbol_map.items():
            bars = self.aggregator.get_bars(sym, n=5)
            if len(bars) == 0:
                continue
            for bar in bars.iter_rows(named=True):
                try:
                    await timescale_db.execute(
                        "INSERT INTO market_bars "
                        "(time, instrument_key, open, high, low, close, volume, oi) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                        "ON CONFLICT DO NOTHING",
                        bar["ts"], inst_key,
                        float(bar["open"]), float(bar["high"]),
                        float(bar["low"]), float(bar["close"]),
                        int(bar["volume"]), int(bar.get("oi", 0)),
                    )
                    inserted += 1
                except Exception:
                    errors += 1
        if inserted > 0:
            self._bars_persisted = True

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

        # Upstox returns candles newest-first; reverse to chronological so
        # that ``get_latest_bars(n)`` (which does ``[-n:]``) returns the
        # most recent bars rather than the oldest.  Keep the most recent
        # ~2 trading days (750 bars/day at 1-min).
        rows = []
        for c in reversed(candles[:750]):
            rows.append({
                "ts": datetime.fromisoformat(c[0]),
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

    # ------------------------------------------------------------------
    # Redis persistence helpers
    # ------------------------------------------------------------------

    async def _write_factors_to_redis(self, symbol: str, direction: Direction, **kwargs):
        """Persist per-symbol factor breakdown to Redis (key = ``factors:{symbol}``)."""
        breakdown = SymbolFactorBreakdown(
            symbol=symbol,
            direction=direction,
            last_updated=datetime.now(timezone.utc),
            l2_universe=kwargs.get("l2", L2UniverseFrame()),
            l3_signals=kwargs.get("l3", L3SignalFrame()),
            l4_sector=kwargs.get("l4", L4SectorFrame()),
            l5_scores=kwargs.get("l5", L5ScoreBreakdown()),
            l6_ranking=kwargs.get("l6", L6RankSnapshot()),
            l7_confluence=kwargs.get("l7", L7ConfluenceCheck()),
            l8_thesis=kwargs.get("l8", L8ThesisSnapshot()),
        )
        await self.cache.set(f"factors:{symbol}", breakdown.model_dump(mode='json'), ex=300)

    async def _write_pipeline_status(self, layer_timings: dict):
        """Persist pipeline-cycle status to Redis (key = ``pipeline:status``)."""
        now = datetime.now(timezone.utc)
        layers = {}
        for name, duration_ms in layer_timings.items():
            layers[name] = PipelineLayerStatus(
                status="ok", last_run=now, duration_ms=duration_ms,
            )

        time_bucket = self.latest_context.time_bucket if self.latest_context else "Unknown"
        phase = self.session.current_phase().capitalize() if self.session else "Closed"

        status = PipelineStatusResponse(
            last_cycle_at=now,
            cycle_number=self._cycle_number,
            cycle_duration_ms=sum(layer_timings.values()),
            market_session=phase,
            time_bucket=time_bucket,
            layers=layers,
        )
        await self.cache.set("pipeline:status", status.model_dump(mode='json'), ex=120)

    async def handle_upstox_tick(self, raw_message: bytes | str):
        """Parse an Upstox V3 WebSocket tick (protobuf) and route to TickBuffer.

        V3 feed sends protobuf-encoded FeedResponse containing a feeds map
        keyed by instrument_key. Each feed has LTPC (ltp, cp), volume (vtt),
        and OI (oi) fields for full mode.
        """
        from core.data.MarketDataFeedV3_pb2 import FeedResponse

        try:
            if isinstance(raw_message, str):
                raw_message = raw_message.encode("utf-8")
            feed_resp = FeedResponse.FromString(raw_message)
        except Exception:
            return

        # FeedResponse.feeds is a map<string, Feed>
        is_initial = feed_resp.type == 0  # initial_feed
        for instrument_key, feed in feed_resp.feeds.items():
            try:
                ltp = None
                volume = 0
                oi = 0
                ts = datetime.fromtimestamp(feed_resp.currentTs / 1000.0, tz=timezone.utc)

                if feed.HasField("fullFeed"):
                    ff = feed.fullFeed
                    if ff.HasField("marketFF"):
                        mf = ff.marketFF
                        ltp = mf.ltpc.ltp if mf.ltpc.ltp else None
                        volume = int(mf.vtt)
                        oi = int(mf.oi)
                        # Pre-load OHLC bars from initial feed
                        if is_initial and mf.marketOHLC.ohlc:
                            ohlc_rows = []
                            for ohlc in mf.marketOHLC.ohlc:
                                if ohlc.ts:
                                    ohlc_rows.append({
                                        "open": ohlc.open,
                                        "high": ohlc.high,
                                        "low": ohlc.low,
                                        "close": ohlc.close,
                                        "volume": ohlc.vol,
                                        "ts": datetime.fromtimestamp(ohlc.ts, tz=timezone.utc),
                                    })
                            if ohlc_rows:
                                try:
                                    self.aggregator.pre_load(
                                        self.aggregator._inst_to_sym.get(instrument_key, instrument_key),
                                        pl.DataFrame(ohlc_rows),
                                    )
                                except Exception:
                                    pass
                    elif ff.HasField("indexFF"):
                        idx = ff.indexFF
                        ltp = idx.ltpc.ltp if idx.ltpc.ltp else None
                elif feed.HasField("ltpc"):
                    ltp = feed.ltpc.ltp if feed.ltpc.ltp else None

                if ltp is None:
                    continue

                self.aggregator.ingest_tick(instrument_key, float(ltp), volume, oi, ts)
            except Exception:
                continue


# Module-level singleton
pipeline = PipelineOrchestrator()
