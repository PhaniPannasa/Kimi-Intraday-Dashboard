from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict

from models.enums import Direction


class L2UniverseFrame(BaseModel):
    fo_eligible: bool = True
    fo_ban: bool = False
    mwpl_status: str = "None"
    earnings_flag: str = "None"
    liquidity_quality: str = "Good"
    lqs_score: float = Field(0.0, ge=0.0, le=1.0)


class L3SignalFrame(BaseModel):
    ema_9: float = 0.0
    ema_20: float = 0.0
    ema_50: float = 0.0
    ema_aligned: bool = False
    supertrend_dir: int = 0
    adx: float = 0.0
    rsi: float = 0.0
    macd_hist: float = 0.0
    atr: float = 0.0
    atr_pct: float = 0.0
    bb_width: float = 0.0
    vwap: float = 0.0
    above_vwap: bool = False
    roc_20: float = 0.0


class L4SectorFrame(BaseModel):
    sector_id: int = 0
    sector_name: str = ""
    rs_ratio: float = 0.0
    rs_momentum: float = 0.0
    rotation_rank: int = 0


class L5ScoreBreakdown(BaseModel):
    total: float = Field(0.0, ge=0.0, le=100.0)
    f1_trend: float = 0.0
    f2_momentum: float = 0.0
    f3_volume: float = 0.0
    f4_volpos: float = 0.0
    f5_structure: float = 0.0
    f6_sector: float = 0.0
    f7_risk: float = 0.0
    regime: str = "Range-Bound"
    modifiers: Dict[str, int] = {}


class L6RankSnapshot(BaseModel):
    previous_score: float = 0.0
    score_change: float = 0.0
    rank_movement: str = "STABLE"
    liquidity_quality: str = "Good"


class L7ConfluenceCheck(BaseModel):
    score: int = Field(0, ge=0, le=6)
    max: int = 6
    checks: Dict[str, bool] = {}


class L8ThesisSnapshot(BaseModel):
    thesis_id: str = ""
    setup_type: int = 1
    trigger: float = 0.0
    invalidation: float = 0.0
    t1: float = 0.0
    t2: float = 0.0
    gross_rr: float = 0.0
    net_rr: float = 0.0
    grade: str = "UNATTRACTIVE"
    actionability_tier: str = "Research-Only"


class SymbolFactorBreakdown(BaseModel):
    symbol: str
    direction: Direction = Direction.LONG
    last_updated: datetime
    l2_universe: L2UniverseFrame = L2UniverseFrame()
    l3_signals: L3SignalFrame = L3SignalFrame()
    l4_sector: L4SectorFrame = L4SectorFrame()
    l5_scores: L5ScoreBreakdown = L5ScoreBreakdown()
    l6_ranking: L6RankSnapshot = L6RankSnapshot()
    l7_confluence: L7ConfluenceCheck = L7ConfluenceCheck()
    l8_thesis: L8ThesisSnapshot = L8ThesisSnapshot()


class PipelineLayerStatus(BaseModel):
    status: str = "ok"
    last_run: Optional[datetime] = None
    duration_ms: int = 0


class PipelineStatusResponse(BaseModel):
    last_cycle_at: Optional[datetime] = None
    cycle_duration_ms: int = 0
    market_session: str = "Closed"
    time_bucket: str = "Pre-Open"
    layers: Dict[str, PipelineLayerStatus] = {}
