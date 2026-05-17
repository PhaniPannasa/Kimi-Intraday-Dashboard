from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter

from models.enums import (
    ActionabilityTier,
    Breadth,
    Direction,
    LiquidityQuality,
    RankMovement,
    Regime,
    SetupType,
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
    PipelineLayerStatus,
    PipelineStatusResponse,
    SymbolFactorBreakdown,
)
from models.frames import (
    EdgeTierStats,
    HealthResponse,
    MarketContextFrame,
    RankingEntry,
    ThesisCard,
    ThesisOutcome,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        websocket="connected",
        last_bar_processed=datetime.now(timezone.utc),
        top25_long_count=25,
        top25_short_count=25,
        active_theses=4,
        token_expires_in_days=365,
        db_connected=True,
        redis_connected=True,
        scheduler_jobs=12,
    )


@router.get("/market/context", response_model=MarketContextFrame)
async def market_context():
    return MarketContextFrame(
        regime=Regime.TRENDING_UP,
        regime_confidence=0.85,
        volatility_qualifier="Volatile",
        vix_band=VIXBand.ELEVATED,
        vix_trajectory="Rising",
        time_bucket="Trend Establishment",
        breadth=Breadth.STRONG,
        premarket_bias="Positive",
    )


@router.get("/rankings/top25/{direction}", response_model=List[RankingEntry])
async def rankings(direction: str):
    direction = Direction(direction.upper())
    mock_entries = [
        RankingEntry(
            symbol="RELIANCE",
            instrument_key="NSE_EQ|INE002A01018",
            score=84.5,
            setup_type=SetupType.ORB_15MIN,
            confluence_score=5,
            net_rr=1.4,
            actionability_tier=ActionabilityTier.TRADEABLE,
            rank_movement=RankMovement.UP,
            liquidity_quality=LiquidityQuality.EXCELLENT,
        ),
        RankingEntry(
            symbol="TCS",
            instrument_key="NSE_EQ|INE467B01029",
            score=79.2,
            setup_type=SetupType.VWAP_RECLAIM,
            confluence_score=4,
            net_rr=1.1,
            actionability_tier=ActionabilityTier.CONSTRAINED,
            rank_movement=RankMovement.NEW,
            liquidity_quality=LiquidityQuality.GOOD,
        ),
    ]
    return mock_entries


@router.get("/thesis/{thesis_id}", response_model=ThesisCard)
async def get_thesis(thesis_id: str):
    return ThesisCard(
        thesis_id=thesis_id,
        symbol="RELIANCE",
        direction=Direction.LONG,
        setup_type=SetupType.ORB_15MIN,
        trigger=2450.5,
        invalidation=2420.0,
        t1=2495.0,
        t2=2530.0,
        gross_rr=1.5,
        net_rr=1.35,
        grade="ATTRACTIVE",
        time_decay_multiplier=1.0,
        actionability_tier=ActionabilityTier.TRADEABLE,
    )


@router.get("/thesis/{thesis_id}/outcome", response_model=Optional[ThesisOutcome])
async def get_thesis_outcome(thesis_id: str):
    return None


@router.get("/edge/tiers")
async def edge_tiers():
    return {"tiers": [], "promotions": []}


@router.get("/edge/tier/{tier_id}/stats", response_model=EdgeTierStats)
async def edge_tier_stats(tier_id: int):
    return EdgeTierStats(
        tier_id=tier_id,
        setup_type=SetupType.ORB_15MIN,
        regime=Regime.TRENDING_UP,
        direction=Direction.LONG,
        n=42,
        hit_rate=0.62,
        ci_lower=0.48,
        ci_upper=0.74,
        is_significant=True,
        avg_net_return=0.85,
        std_net_return=1.2,
    )


@router.get("/rankings/{symbol}/factors", response_model=SymbolFactorBreakdown)
async def symbol_factors(symbol: str):
    return SymbolFactorBreakdown(
        symbol=symbol,
        direction=Direction.LONG,
        last_updated=datetime.now(timezone.utc),
        l2_universe=L2UniverseFrame(
            fo_eligible=True, fo_ban=False, mwpl_status="None",
            earnings_flag="None", liquidity_quality="Excellent", lqs_score=0.87,
        ),
        l3_signals=L3SignalFrame(
            ema_9=2455.2, ema_20=2430.1, ema_50=2400.5, ema_aligned=True,
            supertrend_dir=1, adx=28.4, rsi=56.2, macd_hist=1.35,
            atr=12.5, atr_pct=0.51, bb_width=2.1, vwap=2448.0,
            above_vwap=True, roc_20=3.2,
        ),
        l4_sector=L4SectorFrame(
            sector_id=8, sector_name="Energy", rs_ratio=1.08,
            rs_momentum=1.02, rotation_rank=3,
        ),
        l5_scores=L5ScoreBreakdown(
            total=84.5, f1_trend=85, f2_momentum=72, f3_volume=90,
            f4_volpos=68, f5_structure=88, f6_sector=75, f7_risk=82,
            regime="Trending-Up", modifiers={"strong_sector": 3},
        ),
        l6_ranking=L6RankSnapshot(
            previous_score=78.2, score_change=6.3,
            rank_movement="UP", liquidity_quality="Excellent",
        ),
        l7_confluence=L7ConfluenceCheck(
            score=5, max=6,
            checks={
                "strong_close": True,
                "volume_confirm": True,
                "non_exhaustion": True,
                "htf_alignment": True,
                "risk_distance": True,
                "reward_distance": False,
            },
        ),
        l8_thesis=L8ThesisSnapshot(
            thesis_id=f"{symbol}-ORB-20260517-0931",
            setup_type=1, trigger=2450.5, invalidation=2420.0,
            t1=2495.0, t2=2530.0, gross_rr=1.5, net_rr=1.35,
            grade="ATTRACTIVE", actionability_tier="Tradeable",
        ),
    )


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def pipeline_status():
    now = datetime.now(timezone.utc)
    return PipelineStatusResponse(
        last_cycle_at=now,
        cycle_duration_ms=4200,
        market_session="Open",
        time_bucket="Trend Establishment",
        layers={
            "l1_market_context": PipelineLayerStatus(status="ok", last_run=now, duration_ms=45),
            "l2_universe": PipelineLayerStatus(status="ok", last_run=now, duration_ms=120),
            "l3_signals": PipelineLayerStatus(status="ok", last_run=now, duration_ms=890),
            "l4_sector": PipelineLayerStatus(status="ok", last_run=now, duration_ms=30),
            "l5_scoring": PipelineLayerStatus(status="ok", last_run=now, duration_ms=560),
            "l6_ranking": PipelineLayerStatus(status="ok", last_run=now, duration_ms=80),
            "l7_confluence": PipelineLayerStatus(status="ok", last_run=now, duration_ms=340),
            "l8_thesis": PipelineLayerStatus(status="ok", last_run=now, duration_ms=210),
            "l9_monitor": PipelineLayerStatus(status="ok", last_run=now, duration_ms=150),
            "l10_edge": PipelineLayerStatus(status="ok", last_run=now, duration_ms=95),
        },
    )
