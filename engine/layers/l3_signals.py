"""L3 Per-Stock Signal Layer — orchestrator delegating to indicator/volume/options modules."""
import pandas as pd
import numpy as np
from typing import Optional

from engine.layers.l3_indicators import (
    compute_indicators_single_tf,
    compute_all_indicators,
    detect_macd_divergence as _detect_macd_divergence_new,
)
from engine.layers.l3_volume_seasonality import (
    adjust_volume,
    compute_volume_confirm,
    compute_volume_zscore as _compute_volume_zscore_new,
)
from engine.layers.l3_options import classify_oi as _classify_oi_new


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy wrapper — delegates to l3_indicators, strips 5m suffix for backward compat."""
    result = compute_indicators_single_tf(df, suffix="5m")
    # Strip _5m suffix for backward compatibility with existing callers
    mapper = {col: col[:-3] for col in result.columns if col.endswith("_5m")}
    result = result.rename(columns=mapper)
    # Add roc_20 for backward compat (was in the original implementation)
    result["roc_20"] = df["close"].pct_change(20) * 100
    return result


def ema_aligned(df: pd.DataFrame) -> bool:
    """Check if EMAs are in bullish alignment (9 > 20 > 50).

    Works with both legacy (no suffix) and new (_5m suffix) column names.
    """
    if len(df) < 2:
        return False
    latest = df.iloc[-1]
    e9 = latest.get("ema_9_5m") if "ema_9_5m" in df.columns else latest.get("ema_9", 0)
    e20 = latest.get("ema_20_5m") if "ema_20_5m" in df.columns else latest.get("ema_20", 0)
    e50 = latest.get("ema_50_5m") if "ema_50_5m" in df.columns else latest.get("ema_50", 0)
    return bool(e9 > e20 > e50)


def detect_macd_divergence(df: pd.DataFrame, direction: str = "long") -> bool:
    """Backward-compatible MACD divergence detection.

    Works with both legacy (no suffix) and new (_5m suffix) column names.
    Uses 5-bar window comparison per system_design_final.md.
    """
    if len(df) < 10:
        return False
    prices = df["close"].values
    macd_hist = df["macd_hist_5m"].values if "macd_hist_5m" in df.columns else df["macd_hist"].values
    if direction == "long":
        return prices[-5:].min() < prices[-10:-5].min() and macd_hist[-5:].min() > macd_hist[-10:-5].min()
    else:
        return prices[-5:].max() > prices[-10:-5].max() and macd_hist[-5:].max() < macd_hist[-10:-5].max()


class L3Signals:
    """L3 orchestrator — delegates to specialized modules.

    Usage:
        signals = L3Signals()
        df_with_indicators = signals.compute(df)
    """
    def compute(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Compute L3 signals. Returns enhanced DataFrame with indicator columns.

        Args:
            df: OHLCV DataFrame with at least 50 rows for reliable indicators.
            **kwargs: Reserved for future params (df_15m, nifty_df, pcr, iv, etc.)

        Returns:
            DataFrame with indicators added (backward-compatible column names).
        """
        return compute_indicators(df)


def classify_oi(price_change_pct: float, oi_change_pct: float) -> str:
    """Classify OI change direction. Delegates to l3_options."""
    return _classify_oi_new(price_change_pct, oi_change_pct)


def compute_volume_zscore(current_vol: float, avg_vol: float, std_vol: float) -> float:
    """Backward-compatible volume z-score."""
    if std_vol == 0:
        return 0
    return (current_vol - avg_vol) / std_vol


def compute_vwap(df) -> pd.Series:
    """Compute VWAP from OHLCV DataFrame."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol


def compute_pcr_zscore(pcr: float, pcr_history: list) -> float:
    """Backward-compatible PCR z-score."""
    if not pcr_history:
        return 0
    mean = np.mean(pcr_history)
    std = np.std(pcr_history)
    if std == 0:
        return 0
    return (pcr - mean) / std
