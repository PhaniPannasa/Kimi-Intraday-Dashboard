from enum import Enum


class Regime(str, Enum):
    TRENDING_UP = "Trending-Up"
    TRENDING_DOWN = "Trending-Down"
    RANGE_BOUND = "Range-Bound"


class SetupType(int, Enum):
    ORB_15MIN = 1
    VWAP_RECLAIM = 2
    SUPERTREND_PULLBACK = 3
    MEAN_REVERSION = 4
    FIRST_HOUR_BREAKOUT = 5
    CPR_BREAKOUT = 6


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ActionabilityTier(str, Enum):
    TRADEABLE = "Tradeable"
    CONSTRAINED = "Constrained"
    RESEARCH_ONLY = "Research-Only"


class RankMovement(str, Enum):
    NEW = "NEW"
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class ThesisState(str, Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    ACTIVE = "ACTIVE"
    T1_HIT = "T1_HIT"
    T2_HIT = "T2_HIT"
    STOPPED_OUT = "STOPPED_OUT"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    FORCE_EXPIRED = "FORCE_EXPIRED"


class VIXBand(str, Enum):
    COMPRESSED = "Compressed"
    NORMAL = "Normal"
    ELEVATED = "Elevated"


class Breadth(str, Enum):
    STRONG = "Strong"
    MIXED = "Mixed"
    WEAK = "Weak"


class LiquidityQuality(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MARGINAL = "Marginal"
    POOR = "Poor"
