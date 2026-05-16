from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

from models.enums import (
    Regime,
    SetupType,
    Direction,
    ActionabilityTier,
    RankMovement,
    ThesisState,
    VIXBand,
    Breadth,
    LiquidityQuality,
)


class MarketContextFrame(BaseModel):
    regime: Regime = Regime.RANGE_BOUND
    regime_confidence: float = Field(0.0, ge=0.0, le=1.0)
    volatility_qualifier: str = "Normal"
    vix_band: VIXBand = VIXBand.NORMAL
    vix_trajectory: str = "Stable"
    time_bucket: str = "Pre-Open"
    event_flag: Optional[str] = None
    breadth: Breadth = Breadth.MIXED
    premarket_bias: str = "Neutral"
    bank_nifty_divergence: float = 0.0


class RankingEntry(BaseModel):
    symbol: str
    instrument_key: str
    score: float = Field(0.0, ge=0.0, le=100.0)
    setup_type: SetupType = SetupType.ORB_15MIN
    confluence_score: int = Field(0, ge=0, le=6)
    net_rr: float = 0.0
    actionability_tier: ActionabilityTier = ActionabilityTier.RESEARCH_ONLY
    rank_movement: RankMovement = RankMovement.STABLE
    liquidity_quality: LiquidityQuality = LiquidityQuality.GOOD


class ThesisCard(BaseModel):
    thesis_id: str
    symbol: str
    direction: Direction = Direction.LONG
    setup_type: SetupType = SetupType.ORB_15MIN
    trigger: float = 0.0
    invalidation: float = 0.0
    t1: float = 0.0
    t2: float = 0.0
    gross_rr: float = 0.0
    net_rr: float = 0.0
    grade: str = "UNATTRACTIVE"
    time_decay_multiplier: float = 1.0
    actionability_tier: ActionabilityTier = ActionabilityTier.RESEARCH_ONLY
    valid_until: datetime = datetime.utcnow()
    preferred_regime: Regime = Regime.TRENDING_UP


class ThesisOutcome(BaseModel):
    thesis_id: str
    state: ThesisState = ThesisState.CREATED
    entry_ts: Optional[datetime] = None
    exit_ts: Optional[datetime] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    mfe_pct: float = 0.0
    mae_pct: float = 0.0
    gross_return_pct: float = 0.0
    net_return_pct: float = 0.0
    r_multiple: float = 0.0
    time_to_trigger_min: Optional[int] = None
    time_to_exit_min: Optional[int] = None


class EdgeTierStats(BaseModel):
    tier_id: int
    setup_type: SetupType
    regime: Regime
    sector: Optional[int] = None
    time_bucket: Optional[int] = None
    direction: Direction
    n: int = 0
    hit_rate: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    is_significant: bool = False
    avg_net_return: float = 0.0
    std_net_return: float = 0.0


class HealthResponse(BaseModel):
    status: str = "healthy"
    websocket: str = "disconnected"
    last_bar_processed: Optional[datetime] = None
    top25_long_count: int = 0
    top25_short_count: int = 0
    active_theses: int = 0
    token_expires_in_days: int = 365
    db_connected: bool = False
    redis_connected: bool = False
    scheduler_jobs: int = 0
