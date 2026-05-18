"""Time-decay function per system_design_final.md Section 5.8.

M(t) = exp(-lambda * max(0, t - t_window)^2)

| Time           | ORB Multiplier | Supertrend/VWAP |
|----------------|----------------|-----------------|
| 9:30-10:30     | 1.00           | 1.00            |
| 10:30-11:30    | 0.85           | 0.90            |
| 11:30-12:30    | 0.65           | 0.78            |
| 12:30-13:30    | 0.42           | 0.62            |
| 13:30-14:30    | 0.22           | 0.42            |
| After 14:30    | 0.08           | 0.22            |
"""
import math

# lambda values per setup type
LAMBDA_VALUES = {
    "ORB_15MIN": 0.0003,
    "ORB_2HOUR": 0.0003,
    "FIRST_HOUR_BREAKOUT": 0.0003,
    "VWAP_RECLAIM": 0.00015,
    "SUPERTREND_PULLBACK": 0.00015,
    "CPR_BREAKOUT": 0.00015,
    "MEAN_REVERSION": 0.00015,
}

# t_window values (minutes after creation before decay starts)
TIME_WINDOWS = {
    "ORB_15MIN": 30,
    "ORB_2HOUR": 60,
    "FIRST_HOUR_BREAKOUT": 45,
    "VWAP_RECLAIM": 15,
    "SUPERTREND_PULLBACK": 15,
    "CPR_BREAKOUT": 15,
    "MEAN_REVERSION": 30,
}

DEFAULT_LAMBDA = 0.0002
DEFAULT_WINDOW = 30


def compute_time_decay(setup_type: str, minutes_since_creation: int) -> float:
    """Compute M(t) for a setup at elapsed minutes since thesis creation.

    Args:
        setup_type: Setup type name (e.g. "ORB_15MIN", "VWAP_RECLAIM")
        minutes_since_creation: Minutes elapsed since thesis was created

    Returns:
        Multiplier in (0, 1] - 1.0 at creation, decaying toward 0
    """
    lam = LAMBDA_VALUES.get(setup_type, DEFAULT_LAMBDA)
    t_window = TIME_WINDOWS.get(setup_type, DEFAULT_WINDOW)

    effective_t = max(0, minutes_since_creation - t_window)
    return math.exp(-lam * effective_t ** 2)
