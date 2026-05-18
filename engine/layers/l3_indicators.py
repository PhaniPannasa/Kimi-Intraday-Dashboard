"""Dual-timeframe indicator computation (5-min + 15-min).

Per system_design_final.md Section 5.3:
- EMA(9/20/50), Supertrend(10,3.0), ADX(14), RSI(14),
  MACD(12,26,9), ATR(14), Bollinger Bands(20,2sigma)
- All computed on BOTH 5-min and 15-min timeframes
- ROC is stock return - Nifty return (Nifty-relative)
- ATR percentile is distributional (rank within 20-day history)
"""
import pandas as pd
import pandas_ta as ta
import numpy as np


def compute_indicators_single_tf(df: pd.DataFrame, suffix: str = "5m") -> pd.DataFrame:
    df = df.copy()
    df[f"ema_9_{suffix}"] = ta.ema(df["close"], length=9)
    df[f"ema_20_{suffix}"] = ta.ema(df["close"], length=20)
    df[f"ema_50_{suffix}"] = ta.ema(df["close"], length=50)

    st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0)
    df[f"supertrend_{suffix}"] = st[f"SUPERT_10_3.0"]
    df[f"supertrend_dir_{suffix}"] = st[f"SUPERTd_10_3.0"]

    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    df[f"adx_{suffix}"] = adx["ADX_14"]

    df[f"rsi_{suffix}"] = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df[f"macd_hist_{suffix}"] = macd["MACDh_12_26_9"]
    df[f"macd_{suffix}"] = macd["MACD_12_26_9"]
    df[f"macd_signal_{suffix}"] = macd["MACDs_12_26_9"]

    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    df[f"atr_{suffix}"] = atr_series

    atr_lookback = 20 * 75 if suffix == "5m" else 20 * 25
    df[f"atr_pctile_{suffix}"] = (
        atr_series.rolling(atr_lookback, min_periods=5)
        .apply(lambda x: (x < x.iloc[-1]).sum() / len(x) if len(x) > 0 else 0.5)
    )

    bb = ta.bbands(df["close"], length=20, std=2)
    df[f"bb_upper_{suffix}"] = bb[f"BBU_20_2.0_2.0"]
    df[f"bb_lower_{suffix}"] = bb[f"BBL_20_2.0_2.0"]
    df[f"bb_width_{suffix}"] = bb[f"BBB_20_2.0_2.0"]

    df[f"ema_aligned_{suffix}"] = (df[f"ema_9_{suffix}"] > df[f"ema_20_{suffix}"]) & (df[f"ema_20_{suffix}"] > df[f"ema_50_{suffix}"])
    return df


def compute_all_indicators(df_5m: pd.DataFrame, df_15m: pd.DataFrame | None = None,
                           nifty_df: pd.DataFrame | None = None) -> pd.DataFrame:
    result = compute_indicators_single_tf(df_5m, suffix="5m")
    if df_15m is not None and len(df_15m) >= 2:
        ind_15m = compute_indicators_single_tf(df_15m, suffix="15m")
        result = result.join(ind_15m.filter(like="_15m"), how="left").ffill()

    result["roc_20_stock"] = df_5m["close"].pct_change(20) * 100
    if nifty_df is not None and len(nifty_df) >= 21:
        result["roc_20_nifty"] = nifty_df["close"].pct_change(20) * 100
        result["roc_vs_nifty"] = result["roc_20_stock"] - result["roc_20_nifty"]
    else:
        result["roc_vs_nifty"] = result["roc_20_stock"]
    return result


def detect_macd_divergence(df: pd.DataFrame, direction: str = "long",
                           timeframe: str = "5m") -> bool:
    """Detect MACD divergence using 5-bar window low detection per spec."""
    col = f"macd_hist_{timeframe}"
    if col not in df.columns or len(df) < 10:
        return False
    prices = df["close"].values
    macd_hist = df[col].values
    if direction == "long":
        price_made_lower_low = prices[-5:].min() < prices[-10:-5].min()
        macd_made_higher_low = macd_hist[-5:].min() > macd_hist[-10:-5].min()
        return price_made_lower_low and macd_made_higher_low
    else:
        price_made_higher_high = prices[-5:].max() > prices[-10:-5].max()
        macd_made_lower_high = macd_hist[-5:].max() < macd_hist[-10:-5].max()
        return price_made_higher_high and macd_made_lower_high
