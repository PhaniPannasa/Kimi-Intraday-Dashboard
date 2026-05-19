import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Response

from core.auth.token_manager import token_manager
from core.data.redis_cache import cache
from core.pipeline import pipeline
from core.scheduler.market_scheduler import scheduler
from db.timescale import db as timescale_db
from models.enums import (
    ActionabilityTier,
    Breadth,
    Direction,
    LiquidityQuality,
    RankMovement,
    Regime,
    SetupType,
    ThesisState,
    VIXBand,
)
from models.factors import (
    L2UniverseFrame,
    L3SignalFrame,
    L4SectorFrame,
    L5ScoreBreakdown,
    L6RankSnapshot,
    L7ConfluenceCheck,
    L8ThesisSnapshot,
    L9MonitorSnapshot,
    L10EdgeSnapshot,
    PipelineLayerStatus,
    PipelineStatusResponse,
    SymbolFactorBreakdown,
)
from models.frames import (
    ActiveThesisEntry,
    ActiveThesesResponse,
    ActivityEvent,
    ActivityEventsResponse,
    CandleEntry,
    CandleOverlays,
    CandleResponse,
    EdgeTierStats,
    FunnelCountsFrame,
    FunnelCountsResponse,
    HealthResponse,
    MarketContextFrame,
    RankingEntry,
    ThesisCard,
    ThesisOutcome,
)

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))

# ── Module-level cycle counter ──
_cycle_counter: int = 10420


def _next_cycle() -> int:
    global _cycle_counter
    _cycle_counter += 1
    return _cycle_counter


# ── Deterministic PRNG (mulberry32, matching frontend engineSimulator.ts) ──
def _make_rng(seed: int):
    """Mulberry32: 32-bit PRNG matching the frontend TS implementation."""
    s = seed & 0xFFFFFFFF
    def rng() -> float:
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF
        t = s
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * 61))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rng


# ── Nifty 100 symbol database (50 symbols, matching frontend engineSimulator.ts) ──
# Each entry: (symbol, instrument_key, base_price, sector_id)
NIFTY_SYMBOLS: List[Tuple[str, str, float, int]] = [
    ("RELIANCE",   "NSE_EQ|INE002A01018", 1284.5,  7),
    ("HDFCBANK",   "NSE_EQ|INE040A01034", 1640.8,  1),
    ("TCS",        "NSE_EQ|INE467B01029", 3245.2,  2),
    ("BHARTIARTL", "NSE_EQ|INE397D01024", 1730.1,  8),
    ("ICICIBANK",  "NSE_EQ|INE090A01021", 1318.6,  1),
    ("INFY",       "NSE_EQ|INE009A01021", 1582.4,  2),
    ("SBIN",       "NSE_EQ|INE062A01020",  812.3,  1),
    ("LT",         "NSE_EQ|INE018A01030", 3478.0,  9),
    ("ITC",        "NSE_EQ|INE154A01025",  421.7,  4),
    ("HINDUNILVR", "NSE_EQ|INE030A01027", 2389.4,  4),
    ("KOTAKBANK",  "NSE_EQ|INE237A01028", 1742.0,  1),
    ("AXISBANK",   "NSE_EQ|INE238A01034", 1138.2,  1),
    ("BAJFINANCE", "NSE_EQ|INE296A01024", 6720.5,  1),
    ("MARUTI",     "NSE_EQ|INE585B01010", 11240.0,  3),
    ("M&M",        "NSE_EQ|INE101A01026", 2840.0,  3),
    ("SUNPHARMA",  "NSE_EQ|INE044A01036", 1782.0,  5),
    ("ASIANPAINT", "NSE_EQ|INE021A01026", 2412.0,  9),
    ("TITAN",      "NSE_EQ|INE280A01028", 3398.0,  4),
    ("NTPC",       "NSE_EQ|INE733E01010",  342.8, 11),
    ("ULTRACEMCO", "NSE_EQ|INE481G01011", 11380.0, 10),
    ("NESTLEIND",  "NSE_EQ|INE239A01016", 2287.0,  4),
    ("ONGC",       "NSE_EQ|INE213A01029",  272.1,  7),
    ("JSWSTEEL",   "NSE_EQ|INE019A01030",  978.4,  6),
    ("POWERGRID",  "NSE_EQ|INE752E01010",  308.6, 11),
    ("ADANIENT",   "NSE_EQ|INE423A01024", 2398.0,  7),
    ("HCLTECH",    "NSE_EQ|INE860A01027", 1632.5,  2),
    ("WIPRO",      "NSE_EQ|INE075A01022",  512.7,  2),
    ("BAJAJFINSV", "NSE_EQ|INE918I01026", 1742.0,  1),
    ("COALINDIA",  "NSE_EQ|INE522F01014",  392.2,  6),
    ("TATASTEEL",  "NSE_EQ|INE081A01020",  142.8,  6),
    ("INDUSINDBK", "NSE_EQ|INE095A01012",  782.4,  1),
    ("TECHM",      "NSE_EQ|INE669E01018", 1542.0,  2),
    ("HINDALCO",   "NSE_EQ|INE038A01020",  642.3,  6),
    ("BAJAJ-AUTO", "NSE_EQ|INE917I01010", 9420.0,  3),
    ("EICHERMOT",  "NSE_EQ|INE066A01021", 4820.0,  3),
    ("DRREDDY",    "NSE_EQ|INE089A01023", 1232.0,  5),
    ("BPCL",       "NSE_EQ|INE029A01011",  298.4,  7),
    ("CIPLA",      "NSE_EQ|INE059A01026", 1492.0,  5),
    ("DIVISLAB",   "NSE_EQ|INE361B01024", 6182.0,  5),
    ("BRITANNIA",  "NSE_EQ|INE216A01030", 5142.0,  4),
    ("TATAMOTORS", "NSE_EQ|INE155A01022",  728.5,  3),
    ("APOLLOHOSP", "NSE_EQ|INE437A01024", 6840.0,  5),
    ("HEROMOTOCO", "NSE_EQ|INE158A01026", 4382.0,  3),
    ("ADANIPORTS", "NSE_EQ|INE742F01042", 1378.0,  7),
    ("UPL",        "NSE_EQ|INE628A01036",  542.7,  5),
    ("TATACONSUM", "NSE_EQ|INE192A01025", 1042.0,  4),
    ("SHRIRAMFIN", "NSE_EQ|INE721A01028", 2982.0,  1),
    ("LTIM",       "NSE_EQ|INE214T01019", 6120.0,  2),
    ("SBILIFE",    "NSE_EQ|INE265A01028", 1840.0,  1),
    ("HDFCLIFE",   "NSE_EQ|INE795G01014",  712.8,  1),
]

SECTOR_NAMES: Dict[int, str] = {
    1: "Financials", 2: "IT", 3: "Auto", 4: "FMCG", 5: "Pharma",
    6: "Metals", 7: "Energy", 8: "Telecom", 9: "Realty", 10: "Cement",
    11: "Power",
}

SETUP_LABELS: Dict[int, str] = {
    1: "ORB-15m", 2: "VWAP Reclaim", 3: "ST Pullback",
    4: "Mean Reversion", 5: "1H Breakout", 6: "CPR Breakout",
}

SYMBOL_DATA = {s[0]: {"instrument_key": s[1], "base_price": s[2], "sector_id": s[3]} for s in NIFTY_SYMBOLS}
ALL_SYMBOLS = [s[0] for s in NIFTY_SYMBOLS]

FUNNEL_LAYERS = [
    ("L1", 1), ("L2", 50), ("L3", 48), ("L4", 42), ("L5", 38),
    ("L6", 30), ("L7", 25), ("L8", 18), ("L9", 12), ("L10", 8),
]

EVENT_TYPES = ["NEW", "DROP", "TRIGGER", "T1", "ACTIVE", "INVALID", "JUMP_UP", "JUMP_DN", "STATE"]

REGIMES = [Regime.TRENDING_UP, Regime.TRENDING_DOWN, Regime.RANGE_BOUND]
VIX_BANDS = [VIXBand.COMPRESSED, VIXBand.NORMAL, VIXBand.ELEVATED]
BREADTHS = [Breadth.STRONG, Breadth.MIXED, Breadth.WEAK]
LIQUIDITY_OPTS = [LiquidityQuality.EXCELLENT, LiquidityQuality.GOOD, LiquidityQuality.MARGINAL]
ACTION_OPTS = [ActionabilityTier.TRADEABLE, ActionabilityTier.CONSTRAINED, ActionabilityTier.RESEARCH_ONLY]
MOVEMENTS = [RankMovement.NEW, RankMovement.UP, RankMovement.DOWN, RankMovement.STABLE]
STATES_POOL = ["PENDING", "TRIGGERED", "ACTIVE", "T1_HIT"]
GRADES = ["ATTRACTIVE", "NEUTRAL", "UNATTRACTIVE"]


# ── Utility helpers ──

def _pick(rng, items):
    return items[int(rng() * len(items))]


def _rand_uniform(rng, a: float, b: float) -> float:
    return a + rng() * (b - a)


def _rand_norm(rng) -> float:
    """Box-Muller transform for standard normal."""
    u1 = rng()
    u2 = rng()
    if u1 < 1e-10:
        u1 = 0.5
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _ist_now():
    return datetime.now(IST)


def _valid_until_ist():
    """Return 15:30 IST today (or tomorrow if past market close)."""
    now = datetime.now(IST)
    eod = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now > eod:
        eod += timedelta(days=1)
    return eod


# ── Market data generators ──

def _gen_price(rng, base_price: float) -> float:
    return round(base_price * (1.0 + _rand_norm(rng) * 0.015), 2)


def _gen_change_pct(rng) -> float:
    return round(_rand_norm(rng) * 1.5, 2)


def _gen_sparkline(rng, base_price: float, length: int = 30) -> List[float]:
    price = base_price
    prices = [round(price, 2)]
    vol = base_price * 0.003
    for _ in range(length - 1):
        price += _rand_norm(rng) * vol
        prices.append(round(price, 2))
    return prices


def _gen_candles(rng, base_price: float, count: int = 60) -> List[CandleEntry]:
    price = base_price * (1.0 + _rand_uniform(rng, -0.01, 0.01))
    vol = base_price * 0.002
    raw = [price]
    for _ in range(count):
        raw.append(raw[-1] + _rand_norm(rng) * vol)

    candles = []
    for i in range(count):
        o = round(raw[i], 2)
        c = round(raw[i + 1], 2)
        spread = abs(c - o) * 0.3 + vol * rng() * 0.5
        h = round(max(o, c) + spread * rng(), 2)
        lo = round(min(o, c) - spread * rng(), 2)
        candles.append(CandleEntry(o=o, h=h, l=lo, c=c))
    return candles


def _gen_overlays(rng, candles: List[CandleEntry], direction: Direction = Direction.LONG) -> CandleOverlays:
    last = candles[-1].c if candles else 0.0
    vwap = sum(c.c for c in candles[-20:]) / 20.0 if len(candles) >= 20 else last
    atr_pct = 0.5 + rng() * 1.0
    offset = atr_pct / 100.0

    if direction == Direction.LONG:
        trigger = round(last * (1.0 + offset * (0.5 + rng())), 2)
        invalidation = round(trigger * (1.0 - offset * (1.0 + rng())), 2)
        t1 = round(trigger * (1.0 + offset * (1.5 + rng())), 2)
        t2 = round(t1 * (1.0 + offset * (1.0 + rng())), 2)
    else:
        trigger = round(last * (1.0 - offset * (0.5 + rng())), 2)
        invalidation = round(trigger * (1.0 + offset * (1.0 + rng())), 2)
        t1 = round(trigger * (1.0 - offset * (1.5 + rng())), 2)
        t2 = round(t1 * (1.0 - offset * (1.0 + rng())), 2)

    return CandleOverlays(vwap=round(vwap, 2), trigger=trigger, invalidation=invalidation, t1=t1, t2=t2)


def _gen_setup_levels(rng, price: float, atr_pct: float, direction: Direction):
    dist = price * atr_pct / 100.0
    if direction == Direction.LONG:
        trigger = price + dist * (0.5 + rng())
        invalidation = trigger - dist * (1.0 + rng() * 0.5)
        t1 = trigger + dist * (1.5 + rng() * 1.0)
        t2 = t1 + dist * (1.0 + rng() * 1.5)
    else:
        trigger = price - dist * (0.5 + rng())
        invalidation = trigger + dist * (1.0 + rng() * 0.5)
        t1 = trigger - dist * (1.5 + rng() * 1.0)
        t2 = t1 - dist * (1.0 + rng() * 1.5)
    gross_rr = abs(t1 - trigger) / max(abs(invalidation - trigger), 0.01)
    net_rr = round(gross_rr * 0.95, 2)
    return (round(trigger, 2), round(invalidation, 2), round(t1, 2), round(t2, 2),
            round(gross_rr, 2), net_rr)


def _gen_grade(score: float, confluence: int) -> str:
    avg = (score / 100.0 + confluence / 6.0) / 2.0
    if avg > 0.7:
        return "ATTRACTIVE"
    if avg > 0.45:
        return "NEUTRAL"
    return "UNATTRACTIVE"


def _pick_setup(rng, score: float) -> Tuple[int, int]:
    st = int(rng() * 6) + 1
    cs = min(6, max(2, int(score / 20 + rng() * 2)))
    return st, cs


def _build_ranking_entry(rng, symbol: str, ik: str, bp: float, sid: int,
                         score: float, direction: Direction) -> RankingEntry:
    price = _gen_price(rng, bp)
    change_pct = _gen_change_pct(rng)
    atr_pct = 0.5 + rng() * 1.0
    st, cs = _pick_setup(rng, score)
    _, _, _, _, _, nrr = _gen_setup_levels(rng, price, atr_pct, direction)
    grade = _gen_grade(score, cs)
    tier = max(1, 6 - int(score / 17))
    state = _pick(rng, STATES_POOL)

    return RankingEntry(
        symbol=symbol,
        instrument_key=ik,
        direction=direction,
        score=round(score, 1),
        setup_type=SetupType(st),
        setup_label=SETUP_LABELS.get(st, ""),
        confluence_score=cs,
        net_rr=nrr,
        actionability_tier=_pick(rng, ACTION_OPTS),
        rank_movement=_pick(rng, MOVEMENTS),
        liquidity_quality=_pick(rng, LIQUIDITY_OPTS),
        price=price,
        change_pct=change_pct,
        sector_name=SECTOR_NAMES.get(sid, ""),
        sector_id=sid,
        rs_ratio=round(0.7 + rng() * 0.8, 3),
        rs_momentum=round(0.8 + rng() * 0.5, 3),
        sparkline=_gen_sparkline(rng, price, 30),
        state=state,
        edge_tier=tier,
    )


def _build_symbol_factors(rng, symbol: str, direction: Direction) -> SymbolFactorBreakdown:
    sd = SYMBOL_DATA.get(symbol)
    if not sd:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    bp = sd["base_price"]
    sid = sd["sector_id"]
    price = _gen_price(rng, bp)
    change_pct = _gen_change_pct(rng)
    atr_pct = 0.5 + rng() * 1.0
    st = int(rng() * 6) + 1
    score = round(20 + rng() * 60 + (_rand_norm(rng) * 10), 1)
    cs = min(6, max(2, int(score / 20 + rng() * 2)))

    trigger, inval, t1v, t2v, grr, nrr = _gen_setup_levels(rng, price, atr_pct, direction)

    ema_9 = price * (1.0 + _rand_uniform(rng, -0.01, 0.01))
    ema_20 = price * (1.0 + _rand_uniform(rng, -0.015, 0.005))
    ema_50 = price * (1.0 + _rand_uniform(rng, -0.025, 0.005))

    return SymbolFactorBreakdown(
        symbol=symbol,
        direction=direction,
        last_updated=datetime.now(timezone.utc),
        price=price,
        change_pct=change_pct,
        sparkline=_gen_sparkline(rng, price, 30),
        l2_universe=L2UniverseFrame(
            fo_eligible=rng() > 0.1,
            fo_ban=rng() < 0.05,
            mwpl_status=_pick(rng, ["None", "Near Limit", "At Limit"]),
            earnings_flag=_pick(rng, ["None", "This Week", "Next Week", "Today"]),
            liquidity_quality=_pick(rng, ["Excellent", "Good", "Marginal"]),
            lqs_score=round(0.5 + rng() * 0.5, 2),
        ),
        l3_signals=L3SignalFrame(
            ema_9=round(ema_9, 2),
            ema_20=round(ema_20, 2),
            ema_50=round(ema_50, 2),
            ema_aligned=rng() > 0.4,
            supertrend_dir=1 if rng() > 0.4 else -1,
            adx=round(15 + rng() * 35, 1),
            rsi=round(25 + rng() * 50, 1),
            macd_hist=round(_rand_norm(rng) * 3, 2),
            atr=round(bp * 0.01 * (0.5 + rng()), 2),
            atr_pct=round(0.3 + rng() * 1.5, 2),
            bb_width=round(1.5 + rng() * 3.0, 2),
            vwap=round(price * (1.0 + _rand_norm(rng) * 0.005), 2),
            above_vwap=rng() > 0.4,
            roc_20=round(_rand_norm(rng) * 5, 2),
        ),
        l4_sector=L4SectorFrame(
            sector_id=sid,
            sector_name=SECTOR_NAMES.get(sid, ""),
            rs_ratio=round(0.7 + rng() * 0.8, 3),
            rs_momentum=round(0.8 + rng() * 0.5, 3),
            rotation_rank=int(rng() * 11) + 1,
        ),
        l5_scores=L5ScoreBreakdown(
            total=score,
            f1_trend=round(30 + rng() * 60, 1),
            f2_momentum=round(30 + rng() * 60, 1),
            f3_volume=round(30 + rng() * 60, 1),
            f4_volpos=round(30 + rng() * 60, 1),
            f5_structure=round(30 + rng() * 60, 1),
            f6_sector=round(30 + rng() * 60, 1),
            f7_risk=round(30 + rng() * 60, 1),
            regime=("Trending-Up" if direction == Direction.LONG else "Trending-Down"),
            modifiers={"trend_strength": int(rng() * 5) + 1, "sector_tailwind": int(rng() * 3)},
        ),
        l6_ranking=L6RankSnapshot(
            previous_score=round(score - 5 + rng() * 10, 1),
            score_change=round(_rand_norm(rng) * 8, 1),
            rank_movement=_pick(rng, ["NEW", "UP", "DOWN", "STABLE"]),
            liquidity_quality=_pick(rng, ["Excellent", "Good", "Marginal"]),
        ),
        l7_confluence=L7ConfluenceCheck(
            score=cs,
            max=6,
            checks={
                "strong_close": rng() > 0.3,
                "volume_confirm": rng() > 0.4,
                "non_exhaustion": rng() > 0.3,
                "htf_alignment": rng() > 0.4,
                "risk_distance": rng() > 0.3,
                "reward_distance": rng() > 0.5,
            },
        ),
        l8_thesis=L8ThesisSnapshot(
            thesis_id=f"{symbol}-{SETUP_LABELS.get(st, '').replace('-', '')}-{_ist_now().strftime('%Y%m%d-%H%M')}",
            setup_type=st,
            setup_label=SETUP_LABELS.get(st, ""),
            trigger=trigger,
            invalidation=inval,
            t1=t1v,
            t2=t2v,
            gross_rr=grr,
            net_rr=nrr,
            grade=_gen_grade(score, cs),
            actionability_tier=_pick(rng, ["Tradeable", "Constrained", "Research-Only"]),
            valid_until_min=_valid_until_ist().hour * 60 + _valid_until_ist().minute,
            time_decay=round(0.7 + rng() * 0.3, 2),
        ),
        l9_monitor=L9MonitorSnapshot(
            state=_pick(rng, ["PENDING", "TRIGGERED", "ACTIVE", "T1_HIT", "INVALIDATED"]),
            mfe_R=round(rng() * 2.0, 2),
            mae_R=round(rng() * 0.8, 2),
            entry_price=round(trigger * (1.0 + _rand_norm(rng) * 0.002), 2) if rng() > 0.3 else None,
            current_price=price,
        ),
        l10_edge=L10EdgeSnapshot(
            edge_tier=max(1, int(rng() * 6)),
            hit_rate=round(0.3 + rng() * 0.5, 3),
            ci_lower=round(0.2 + rng() * 0.3, 3),
            ci_upper=round(0.5 + rng() * 0.4, 3),
            n_samples=int(20 + rng() * 180),
            is_significant=rng() > 0.3,
        ),
    )


def _gen_events(rng, cycle: int, limit: int = 20) -> List[ActivityEvent]:
    events: List[ActivityEvent] = []
    now = _ist_now()

    for i in range(min(limit * 2, 60)):
        if rng() > 0.55:
            continue
        ev_type = _pick(rng, EVENT_TYPES)
        sym = _pick(rng, ALL_SYMBOLS)
        dir_ = Direction.LONG if rng() > 0.5 else Direction.SHORT
        ev_cycle = max(1, cycle - limit + i)
        sym_data = SYMBOL_DATA[sym]
        ev_rng = _make_rng(ev_cycle * 65537 + hash(sym) % 100000)
        px = _gen_price(ev_rng, sym_data["base_price"])

        texts = {
            "NEW": f"{sym} entered Top 25 {dir_.value}",
            "DROP": f"{sym} dropped from Top 25",
            "TRIGGER": f"{sym} thesis triggered at {px}",
            "T1": f"{sym} hit T1 target on {dir_.value} thesis",
            "ACTIVE": f"{sym} thesis is now ACTIVE",
            "INVALID": f"{sym} thesis invalidated",
            "JUMP_UP": f"{sym} surged {int(rng()*5)+1} positions in ranking",
            "JUMP_DN": f"{sym} slipped {int(rng()*5)+1} positions in ranking",
            "STATE": f"{sym} state changed to {_pick(rng, STATES_POOL)}",
        }
        details = {
            "NEW": f"Score: {round(60+rng()*35, 1)}  |  RR: {round(0.8+rng()*2.0, 2)}",
            "DROP": f"Score fell below cutoff: {round(20+rng()*25, 1)}",
            "TRIGGER": f"Entry at {px}  |  Stop at {round(px*0.98, 2)}",
            "T1": f"Target 1 locked  |  R-multiple: {round(1.0+rng()*1.2, 2)}",
            "ACTIVE": f"Entry: {round(px*0.995, 2)}  |  Running P&L: {round((rng()-0.5)*2.0, 2)}R",
            "INVALID": f"Price moved adverse: {round((rng()-0.5)*3.0, 2)}% away",
            "JUMP_UP": f"Rank delta: +{int(rng()*8)+2}  |  New rank: #{int(rng()*15)+1}",
            "JUMP_DN": f"Rank delta: -{int(rng()*8)+2}  |  New rank: #{int(rng()*25)+15}",
            "STATE": f"From {_pick(rng, ['PENDING','TRIGGERED'])} to {_pick(rng, ['ACTIVE','T1_HIT'])}",
        }

        ts = now - timedelta(seconds=(limit - i) * rng() * 60)
        events.append(ActivityEvent(
            id=f"evt-{ev_cycle}-{sym}-{i}",
            ts=ts.isoformat(),
            type=ev_type,
            symbol=sym,
            direction=dir_,
            text=texts.get(ev_type, ""),
            detail=details.get(ev_type, ""),
            cycle=ev_cycle,
        ))

    events.sort(key=lambda e: e.cycle, reverse=True)
    return events[:limit]


def _gen_active_theses(rng, cycle: int) -> List[ActiveThesisEntry]:
    theses: List[ActiveThesisEntry] = []
    count = int(rng() * 4) + 3  # 3-6 theses
    now_ist = _ist_now()

    for i in range(count):
        sym = _pick(rng, ALL_SYMBOLS)
        sd = SYMBOL_DATA[sym]
        dir_ = Direction.LONG if rng() > 0.5 else Direction.SHORT
        st = int(rng() * 6) + 1
        state = _pick(rng, STATES_POOL)
        bp = sd["base_price"]
        price = _gen_price(rng, bp)
        atr_pct = 0.5 + rng() * 1.0
        trigger, _, t1v, t2v, _, nrr = _gen_setup_levels(rng, price, atr_pct, dir_)
        entry = trigger if state in ("TRIGGERED", "ACTIVE", "T1_HIT") else None
        mfe = round(abs(price - trigger) / max(abs(trigger * 0.01), 0.01) * rng() * 0.02, 2) if entry else 0.0
        mae = round(abs(price - trigger) / max(abs(trigger * 0.01), 0.01) * rng() * 0.01, 2) if entry else 0.0

        theses.append(ActiveThesisEntry(
            thesis_id=f"{sym}-{SETUP_LABELS.get(st, '').replace('-', '')}-{now_ist.strftime('%Y%m%d-%H%M')}",
            symbol=sym,
            direction=dir_,
            setup_label=SETUP_LABELS.get(st, ""),
            state=state,
            trigger=trigger,
            t1=t1v,
            t2=t2v,
            net_rr=nrr,
            mfe_R=mfe,
            mae_R=mae,
            entry_price=entry,
            current_price=price if entry else None,
        ))
    return theses


def _gen_funnel_dict(rng) -> Dict[str, Dict[str, int]]:
    return {
        "L1":  {"in": 1,  "out": 1},
        "L2":  {"in": 50, "out": 48},
        "L3":  {"in": 48, "out": 42},
        "L4":  {"in": 42, "out": 38},
        "L5":  {"in": 38, "out": 30},
        "L6":  {"in": 30, "out": 25},
        "L7":  {"in": 25, "out": 18},
        "L8":  {"in": 18, "out": 12},
        "L9":  {"in": 12, "out": 8},
        "L10": {"in": 8,  "out": 6},
    }


def _funnel_counts_response() -> FunnelCountsResponse:
    return FunnelCountsResponse(
        L1=FunnelCountsFrame(layer="L1", in_count=1, out_count=1),
        L2=FunnelCountsFrame(layer="L2", in_count=50, out_count=48),
        L3=FunnelCountsFrame(layer="L3", in_count=48, out_count=42),
        L4=FunnelCountsFrame(layer="L4", in_count=42, out_count=38),
        L5=FunnelCountsFrame(layer="L5", in_count=38, out_count=30),
        L6=FunnelCountsFrame(layer="L6", in_count=30, out_count=25),
        L7=FunnelCountsFrame(layer="L7", in_count=25, out_count=18),
        L8=FunnelCountsFrame(layer="L8", in_count=18, out_count=12),
        L9=FunnelCountsFrame(layer="L9", in_count=12, out_count=8),
        L10=FunnelCountsFrame(layer="L10", in_count=8, out_count=6),
    )


# ═══════════════════════════════════════════════════════════════════
#  EXISTING ENDPOINTS — enriched with realistic mock data
# ═══════════════════════════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse)
async def health(response: Response):
    long_count = len(pipeline.latest_long_rankings)
    short_count = len(pipeline.latest_short_rankings)
    thesis_count = len(pipeline.latest_theses)
    has_real_data = (long_count + short_count + thesis_count) > 0
    response.headers["X-Data-Source"] = "pipeline" if has_real_data else "mock"

    last_bar = None
    try:
        for buf in pipeline.aggregator._buffers.values():
            for bars in getattr(buf, "_completed", {}).values():
                for bar in bars:
                    ts = bar.get("ts")
                    if ts is not None and (last_bar is None or ts > last_bar):
                        last_bar = ts
    except Exception:
        last_bar = None

    return HealthResponse(
        status="healthy",
        websocket="connected" if has_real_data else "idle",
        last_bar_processed=last_bar if last_bar else datetime.now(timezone.utc),
        top25_long_count=long_count,
        top25_short_count=short_count,
        active_theses=thesis_count,
        token_expires_in_days=token_manager.days_until_expiry(),
        db_connected=await timescale_db.ping(),
        redis_connected=await cache.ping(),
        scheduler_jobs=scheduler.get_job_count(),
    )


@router.get("/market/context", response_model=MarketContextFrame)
async def market_context(response: Response):
    # Only use pipeline context if it has meaningful data (vix_value > 0)
    if pipeline.latest_context is not None and pipeline.latest_context.vix_value > 0:
        response.headers["X-Data-Source"] = "pipeline"
        return pipeline.latest_context
    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 7919)
    event_flag = _pick(rng, [None, None, None, "RBI Policy 14:00", "F&O Expiry 14:30",
                             "US CPI Data 18:00", "Weekly Expiry"])
    return MarketContextFrame(
        regime=_pick(rng, REGIMES),
        regime_confidence=round(0.55 + rng() * 0.4, 2),
        volatility_qualifier=_pick(rng, ["Low", "Normal", "Elevated", "High"]),
        vix_band=_pick(rng, VIX_BANDS),
        vix_value=round(12 + rng() * 18, 2),
        vix_trajectory=_pick(rng, ["Falling", "Stable", "Rising"]),
        time_bucket=_pick(rng, [
            "Opening Shock", "Trend Establishment", "Mid-Morning",
            "Lunch", "Afternoon Recovery", "Closing Hour",
        ]),
        event_flag=event_flag,
        breadth=_pick(rng, BREADTHS),
        premarket_bias=_pick(rng, ["Positive", "Neutral", "Negative", "Mixed"]),
        bank_nifty_divergence=round(_rand_uniform(rng, -0.8, 0.8), 2),
    )


@router.get("/rankings/top25/{direction}", response_model=List[RankingEntry])
async def rankings(direction: str, response: Response):
    try:
        dir_enum = Direction(direction.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid direction: {direction}. Must be 'long' or 'short'")

    live = (
        pipeline.latest_long_rankings
        if dir_enum == Direction.LONG
        else pipeline.latest_short_rankings
    )
    if live:
        response.headers["X-Data-Source"] = "pipeline"
        return live[:25]

    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 104729)

    scored: List[Tuple[str, str, float, int, float]] = []
    for sym, ik, bp, sid in NIFTY_SYMBOLS:
        base = max(0, min(100, _rand_norm(rng) * 22 + 50))
        adj = max(0, min(100, base + _rand_norm(rng) * 10))
        scored.append((sym, ik, bp, sid, adj))

    scored.sort(key=lambda x: x[4], reverse=True)

    entries = []
    for sym, ik, bp, sid, score in scored[:25]:
        erng = _make_rng(cycle * 10007 + hash(sym) % 100000)
        entries.append(_build_ranking_entry(erng, sym, ik, bp, sid, score, dir_enum))
    return entries


@router.get("/thesis/{thesis_id}", response_model=ThesisCard)
async def get_thesis(thesis_id: str, response: Response):
    for thesis in pipeline.latest_theses:
        if thesis.thesis_id == thesis_id:
            response.headers["X-Data-Source"] = "pipeline"
            return thesis
    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65539 + hash(thesis_id) % 100000)
    sym = _pick(rng, ALL_SYMBOLS)
    sd = SYMBOL_DATA[sym]
    dir_ = Direction.LONG if rng() > 0.5 else Direction.SHORT
    st = int(rng() * 6) + 1
    price = _gen_price(rng, sd["base_price"])
    atr_pct = 0.5 + rng() * 1.0
    trigger, inval, t1v, t2v, grr, nrr = _gen_setup_levels(rng, price, atr_pct, dir_)
    cs = min(6, max(2, int(rng() * 4 + 2)))

    cost = {
        "stt": round(price * 0.001, 2),
        "brokerage": round(price * 0.0003, 2),
        "gst": round(price * 0.00005, 2),
        "sebi": round(price * 0.00002, 2),
        "stamp": round(price * 0.0001, 2),
        "slippage_bps": round(2 + rng() * 8, 1),
    }

    return ThesisCard(
        thesis_id=thesis_id,
        symbol=sym,
        direction=dir_,
        setup_type=SetupType(st),
        trigger=trigger,
        invalidation=inval,
        t1=t1v,
        t2=t2v,
        gross_rr=grr,
        net_rr=nrr,
        grade=_gen_grade(50 + rng() * 40, cs),
        confluence_score=cs,
        time_decay_multiplier=round(0.7 + rng() * 0.3, 2),
        actionability_tier=_pick(rng, ACTION_OPTS),
        valid_until=_valid_until_ist(),
        preferred_regime=_pick(rng, REGIMES),
        cost_breakdown=cost,
        slippage_bps=round(2 + rng() * 8, 1),
        liquidity_quality=_pick(rng, LIQUIDITY_OPTS),
        net_reward=round(abs(t1v - trigger), 2),
        net_risk=round(abs(trigger - inval), 2),
    )


@router.get("/thesis/{thesis_id}/outcome", response_model=Optional[ThesisOutcome])
async def get_thesis_outcome(thesis_id: str):
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65539 + hash(thesis_id) % 100000)
    sym = _pick(rng, ALL_SYMBOLS)
    sd = SYMBOL_DATA[sym]
    dir_ = Direction.LONG if rng() > 0.5 else Direction.SHORT
    st = int(rng() * 6) + 1
    price = _gen_price(rng, sd["base_price"])
    _, _, t1v, _, _, _ = _gen_setup_levels(rng, price, 0.5 + rng(), dir_)
    state = _pick(rng, list(ThesisState))
    entry_px = price * (1.0 + _rand_norm(rng) * 0.01)
    exit_px = t1v * (1.0 + _rand_norm(rng) * 0.02)
    mfe = abs(max(price, t1v) - entry_px) / entry_px * 100
    mae = abs(min(price, entry_px) - entry_px) / entry_px * 100
    ret = (exit_px - entry_px) / entry_px * 100

    return ThesisOutcome(
        thesis_id=thesis_id,
        state=state,
        entry_ts=datetime.now(IST) - timedelta(minutes=int(rng() * 60)),
        exit_ts=datetime.now(IST) - timedelta(minutes=int(rng() * 30)) if state in (
            ThesisState.T1_HIT, ThesisState.T2_HIT, ThesisState.STOPPED_OUT,
            ThesisState.INVALIDATED, ThesisState.EXPIRED) else None,
        entry_price=round(entry_px, 2),
        exit_price=round(exit_px, 2) if state in (
            ThesisState.T1_HIT, ThesisState.T2_HIT, ThesisState.STOPPED_OUT,
            ThesisState.INVALIDATED) else None,
        mfe_pct=round(mfe, 2),
        mae_pct=round(mae, 2),
        gross_return_pct=round(ret, 2),
        net_return_pct=round(ret * 0.95, 2),
        r_multiple=round(abs(exit_px - entry_px) / max(abs(entry_px * 0.01), 0.01) * 0.02, 2),
        time_to_trigger_min=int(rng() * 45) + 5,
        time_to_exit_min=int(rng() * 120) + 10 if state in (
            ThesisState.T1_HIT, ThesisState.T2_HIT, ThesisState.STOPPED_OUT,
            ThesisState.INVALIDATED) else None,
    )


@router.get("/edge/tiers")
async def edge_tiers(response: Response):
    response.headers["X-Data-Source"] = "mock"  # always mock pre-Phase-B
    cycle = _next_cycle()
    tiers = []
    for tid in range(1, 7):
        rng = _make_rng(cycle * 99991 + tid * 313)
        n = int(30 + rng() * 220)
        hr = round(0.25 + rng() * 0.55, 3)
        ci = 1.96 * math.sqrt(hr * (1.0 - hr) / n) if n > 0 else 0.99
        tiers.append({
            "tier_id": tid,
            "label": f"T{tid}",
            "setup_type": _pick(rng, list(SetupType)).value,
            "regime": _pick(rng, REGIMES).value,
            "direction": _pick(rng, ["LONG", "SHORT"]),
            "n": n,
            "hit_rate": hr,
            "ci_lower": round(max(0.0, hr - ci), 3),
            "ci_upper": round(min(1.0, hr + ci), 3),
            "is_significant": n > 40 and ci < 0.18,
            "avg_net_return": round(0.2 + rng() * 1.8, 2),
            "std_net_return": round(0.5 + rng() * 1.5, 2),
            "live_count": int(rng() * 6),
        })

    return {"tiers": tiers, "promotions": [t["tier_id"] for t in tiers if t["hit_rate"] > 0.6 and t["n"] > 50]}


@router.get("/edge/tier/{tier_id}/stats", response_model=EdgeTierStats)
async def edge_tier_stats(tier_id: int):
    if tier_id < 1 or tier_id > 6:
        raise HTTPException(status_code=404, detail="Tier must be 1-6")
    cycle = _next_cycle()
    rng = _make_rng(cycle * 99991 + tier_id * 313)
    n = int(50 + rng() * 200)
    hr = round(0.25 + rng() * 0.55, 3)
    ci = 1.96 * math.sqrt(hr * (1.0 - hr) / n) if n > 0 else 0.99
    return EdgeTierStats(
        tier_id=tier_id,
        setup_type=_pick(rng, list(SetupType)),
        regime=_pick(rng, REGIMES),
        sector=int(rng() * 11) + 1 if rng() > 0.3 else None,
        time_bucket=int(rng() * 6) + 1 if rng() > 0.3 else None,
        direction=_pick(rng, [Direction.LONG, Direction.SHORT]),
        n=n,
        hit_rate=hr,
        ci_lower=round(max(0.0, hr - ci), 3),
        ci_upper=round(min(1.0, hr + ci), 3),
        is_significant=n > 40 and ci < 0.18,
        avg_net_return=round(0.2 + rng() * 1.8, 2),
        std_net_return=round(0.5 + rng() * 1.5, 2),
    )


@router.get("/rankings/{symbol}/factors", response_model=SymbolFactorBreakdown)
async def symbol_factors(symbol: str, response: Response):
    if symbol not in SYMBOL_DATA:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    cached_factors = None
    try:
        cached_factors = await cache.get(f"factors:{symbol}")
    except Exception:
        cached_factors = None
    if cached_factors:
        response.headers["X-Data-Source"] = "pipeline"
        return SymbolFactorBreakdown(**cached_factors)
    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65537 + hash(symbol) % 100000)
    direction = Direction.LONG if rng() > 0.5 else Direction.SHORT
    return _build_symbol_factors(rng, symbol, direction)


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def pipeline_status(response: Response):
    try:
        cached = await cache.get("pipeline:status")
    except Exception:
        cached = None
    if cached:
        response.headers["X-Data-Source"] = "pipeline"
        return PipelineStatusResponse(**cached)

    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 4253)
    now = datetime.now(timezone.utc)
    layers = [
        ("l1_market_context", "ok", 45),
        ("l2_universe", "ok", 120),
        ("l3_signals", "ok", 890),
        ("l4_sector", "ok", 30),
        ("l5_scoring", "ok", 560),
        ("l6_ranking", "ok", 80),
        ("l7_confluence", "ok", 340),
        ("l8_thesis", "ok", 210),
        ("l9_monitor", "ok", 150),
        ("l10_edge", "ok", 95),
    ]
    return PipelineStatusResponse(
        last_cycle_at=now,
        cycle_number=cycle,
        cycle_duration_ms=4200 + int(rng() * 500),
        market_session=_pick(rng, ["Pre-Open", "Open", "Closed", "Settlement"]),
        time_bucket=_pick(rng, [
            "Opening Shock", "Trend Establishment", "Mid-Morning",
            "Lunch", "Afternoon Recovery", "Closing Hour",
        ]),
        layers={k: PipelineLayerStatus(status=s, last_run=now, duration_ms=d)
                for k, s, d in layers},
        funnel_counts=_gen_funnel_dict(rng),
    )


# ═══════════════════════════════════════════════════════════════════
#  NEW ENDPOINTS — added for enhanced UI
# ═══════════════════════════════════════════════════════════════════

@router.get("/funnel/counts", response_model=FunnelCountsResponse)
async def funnel_counts(response: Response):
    has_rankings = bool(pipeline.latest_long_rankings or pipeline.latest_short_rankings)
    if has_rankings:
        response.headers["X-Data-Source"] = "pipeline"
        total = len(pipeline.symbol_map)
        ranked = len(pipeline.latest_long_rankings) + len(pipeline.latest_short_rankings)
        theses = len(pipeline.latest_theses)
        return FunnelCountsResponse(
            L1=FunnelCountsFrame(layer="L1", in_count=1, out_count=1),
            L2=FunnelCountsFrame(layer="L2", in_count=total, out_count=total),
            L3=FunnelCountsFrame(layer="L3", in_count=total, out_count=total),
            L4=FunnelCountsFrame(layer="L4", in_count=total, out_count=total),
            L5=FunnelCountsFrame(layer="L5", in_count=total, out_count=total),
            L6=FunnelCountsFrame(layer="L6", in_count=total, out_count=ranked),
            L7=FunnelCountsFrame(layer="L7", in_count=ranked, out_count=ranked),
            L8=FunnelCountsFrame(layer="L8", in_count=ranked, out_count=theses),
            L9=FunnelCountsFrame(layer="L9", in_count=theses, out_count=theses),
            L10=FunnelCountsFrame(layer="L10", in_count=theses, out_count=theses),
        )
    response.headers["X-Data-Source"] = "mock"
    _next_cycle()
    return _funnel_counts_response()


@router.get("/activity/events", response_model=ActivityEventsResponse)
async def activity_events(response: Response, since: int = Query(0), limit: int = Query(20, ge=1, le=50)):
    response.headers["X-Data-Source"] = "mock"  # always mock pre-Phase-B
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65539)
    events = _gen_events(rng, cycle, limit=limit)
    if since > 0:
        events = [e for e in events if e.cycle > since]
    return ActivityEventsResponse(events=events, total=len(events))


@router.get("/monitor/active-theses", response_model=ActiveThesesResponse)
async def active_theses(response: Response):
    if pipeline.latest_theses:
        response.headers["X-Data-Source"] = "pipeline"
        entries = [
            ActiveThesisEntry(
                thesis_id=t.thesis_id,
                symbol=t.symbol,
                direction=t.direction,
                setup_label=SETUP_LABELS.get(int(t.setup_type), ""),
                state="PENDING",
                trigger=t.trigger,
                t1=t.t1,
                t2=t.t2,
                net_rr=t.net_rr,
                mfe_R=0.0,
                mae_R=0.0,
                entry_price=None,
                current_price=None,
            )
            for t in pipeline.latest_theses
        ]
        return ActiveThesesResponse(theses=entries)
    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    rng = _make_rng(cycle * 65539)
    theses = _gen_active_theses(rng, cycle)
    return ActiveThesesResponse(theses=theses)


@router.get("/market/candles/{symbol}", response_model=CandleResponse)
async def market_candles(symbol: str, response: Response, interval: str = Query("1m"), count: int = Query(60, ge=10, le=200)):
    if symbol not in SYMBOL_DATA:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")

    try:
        bars = pipeline.aggregator.get_bars(symbol, n=count)
        if len(bars) > 0:
            response.headers["X-Data-Source"] = "pipeline"
            candles = [
                CandleEntry(o=float(row["open"]), h=float(row["high"]),
                            l=float(row["low"]), c=float(row["close"]))
                for row in bars.to_dicts()
            ]
            return CandleResponse(symbol=symbol, interval=interval, candles=candles, overlays=None)
    except Exception:
        pass

    response.headers["X-Data-Source"] = "mock"
    cycle = _next_cycle()
    base_price = SYMBOL_DATA[symbol]["base_price"]
    rng = _make_rng(cycle * 65537 + hash(symbol) % 100000)
    if interval != "1m":
        rng()
    candles = _gen_candles(rng, base_price, count)
    overlays = _gen_overlays(rng, candles, direction=Direction.LONG if rng() > 0.5 else Direction.SHORT)
    return CandleResponse(symbol=symbol, interval=interval, candles=candles, overlays=overlays)


@router.get("/telemetry/data-sources")
async def telemetry_data_sources():
    """One-shot snapshot of pipeline truth — which endpoints serve real data,
    current market-session phase, last bar timestamp, symbols feeding, and
    per-layer realness flags. Polled by the frontend DataSourceDebugPanel."""
    from api.websocket_manager import manager as ws_mgr
    from core.session.market_session import session as market_session
    from core.telemetry import snapshot

    return snapshot(
        pipeline=pipeline,
        session=market_session,
        ws_connections=len(ws_mgr._connections),
        scheduler_running=scheduler.scheduler.running,
    )
