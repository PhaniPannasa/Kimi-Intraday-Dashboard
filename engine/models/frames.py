from pydantic import BaseModel, Field
from datetime import datetime, timezone
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
    vix_value: float = 0.0
    premarket_bias: str = "Neutral"
    bank_nifty_divergence: float = 0.0


class RankingEntry(BaseModel):
    symbol: str
    instrument_key: str
    direction: Direction = Direction.LONG
    score: float = Field(0.0, ge=0.0, le=100.0)
    setup_type: SetupType = SetupType.ORB_15MIN
    setup_label: str = ""
    confluence_score: int = Field(0, ge=0, le=6)
    net_rr: float = 0.0
    actionability_tier: ActionabilityTier = ActionabilityTier.RESEARCH_ONLY
    rank_movement: RankMovement = RankMovement.STABLE
    liquidity_quality: LiquidityQuality = LiquidityQuality.GOOD
    # Rich fields for enhanced UI
    price: float = 0.0
    change_pct: float = 0.0
    sector_name: str = ""
    sector_id: int = 0
    rs_ratio: float = 0.0
    rs_momentum: float = 0.0
    sparkline: List[float] = []
    state: str = "PENDING"
    edge_tier: int = 6


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
    confluence_score: int = Field(0, ge=0, le=6)
    time_decay_multiplier: float = 1.0
    actionability_tier: ActionabilityTier = ActionabilityTier.RESEARCH_ONLY
    valid_until: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    preferred_regime: Regime = Regime.TRENDING_UP
    # NEW: cost transparency fields
    cost_breakdown: Optional[dict] = None
    slippage_bps: float = 0.0
    liquidity_quality: LiquidityQuality = LiquidityQuality.GOOD
    net_reward: float = 0.0
    net_risk: float = 0.0


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


# ── New models for enhanced UI ──

class FunnelCountsFrame(BaseModel):
    """Per-layer survivor counts for the FunnelStrip component."""
    layer: str
    in_count: int = 0
    out_count: int = 0


class FunnelCountsResponse(BaseModel):
    """Aggregate funnel counts across all layers."""
    L1: FunnelCountsFrame = FunnelCountsFrame(layer="L1")
    L2: FunnelCountsFrame = FunnelCountsFrame(layer="L2")
    L3: FunnelCountsFrame = FunnelCountsFrame(layer="L3")
    L4: FunnelCountsFrame = FunnelCountsFrame(layer="L4")
    L5: FunnelCountsFrame = FunnelCountsFrame(layer="L5")
    L6: FunnelCountsFrame = FunnelCountsFrame(layer="L6")
    L7: FunnelCountsFrame = FunnelCountsFrame(layer="L7")
    L8: FunnelCountsFrame = FunnelCountsFrame(layer="L8")
    L9: FunnelCountsFrame = FunnelCountsFrame(layer="L9")
    L10: FunnelCountsFrame = FunnelCountsFrame(layer="L10")


class ActivityEvent(BaseModel):
    """A single cycle activity event for the feed."""
    id: str
    ts: str  # ISO timestamp
    type: str  # NEW, DROP, TRIGGER, T1, ACTIVE, INVALID, JUMP_UP, JUMP_DN, STATE
    symbol: str
    direction: Direction = Direction.LONG
    text: str = ""
    detail: str = ""
    cycle: int = 0


class ActivityEventsResponse(BaseModel):
    """Paginated activity events response."""
    events: List[ActivityEvent] = []
    total: int = 0


class ActiveThesisEntry(BaseModel):
    """Single active thesis for the L9 monitor."""
    thesis_id: str
    symbol: str
    direction: Direction = Direction.LONG
    setup_label: str = ""
    state: str = "PENDING"
    trigger: float = 0.0
    t1: float = 0.0
    t2: float = 0.0
    net_rr: float = 0.0
    mfe_R: float = 0.0
    mae_R: float = 0.0
    entry_price: Optional[float] = None
    current_price: Optional[float] = None


class ActiveThesesResponse(BaseModel):
    """All active/triggered theses for monitoring."""
    theses: List[ActiveThesisEntry] = []


class CandleEntry(BaseModel):
    """Single OHLC candle."""
    o: float  # open
    h: float  # high
    l: float  # low
    c: float  # close


class CandleOverlays(BaseModel):
    """Level overlays for the candle chart."""
    vwap: float = 0.0
    trigger: float = 0.0
    invalidation: float = 0.0
    t1: float = 0.0
    t2: float = 0.0


class CandleResponse(BaseModel):
    """OHLC candles for a symbol."""
    symbol: str
    interval: str = "1m"
    candles: List[CandleEntry] = []
    overlays: Optional[CandleOverlays] = None
