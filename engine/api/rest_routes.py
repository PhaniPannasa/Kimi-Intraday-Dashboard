from datetime import datetime
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
        last_bar_processed=datetime.utcnow(),
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
