import pandas as pd
import pandas_ta as ta
import numpy as np

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_9"] = ta.ema(df["close"], length=9)
    df["ema_20"] = ta.ema(df["close"], length=20)
    df["ema_50"] = ta.ema(df["close"], length=50)

    st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0)
    df["supertrend"] = st["SUPERT_10_3.0"]
    df["supertrend_dir"] = st["SUPERTd_10_3.0"]

    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    df["adx"] = adx["ADX_14"]

    df["rsi"] = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd_hist"] = macd["MACDh_12_26_9"]

    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["atr"] = atr_series
    df["atr_pct"] = df["atr"] / df["close"] * 100

    bb = ta.bbands(df["close"], length=20, std=2)
    df["bb_upper"] = bb["BBU_20_2.0_2.0"]
    df["bb_lower"] = bb["BBL_20_2.0_2.0"]
    df["bb_width"] = bb["BBB_20_2.0_2.0"]

    df["roc_20"] = df["close"].pct_change(20) * 100
    return df

def ema_aligned(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False
    latest = df.iloc[-1]
    return bool(latest["ema_9"] > latest["ema_20"] > latest["ema_50"])

def detect_macd_divergence(df: pd.DataFrame, direction: str = "long") -> bool:
    if len(df) < 10:
        return False
    prices = df["close"].values
    macd_hist = df["macd_hist"].values
    if direction == "long":
        return prices[-5] > prices[-1] and macd_hist[-5] < macd_hist[-1]
    else:
        return prices[-5] < prices[-1] and macd_hist[-5] > macd_hist[-1]

class L3Signals:
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        return compute_indicators(df)


def classify_oi(price_change_pct: float, oi_change_pct: float) -> str:
    if price_change_pct > 0.5 and oi_change_pct > 2:
        return "Long Buildup"
    elif price_change_pct < -0.5 and oi_change_pct > 2:
        return "Short Buildup"
    elif price_change_pct < -0.5 and oi_change_pct < -2:
        return "Long Unwinding"
    elif price_change_pct > 0.5 and oi_change_pct < -2:
        return "Short Covering"
    return "Neutral"


def compute_volume_zscore(current_vol: float, avg_vol: float, std_vol: float) -> float:
    if std_vol == 0:
        return 0
    return (current_vol - avg_vol) / std_vol


def compute_vwap(df) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol


def compute_pcr_zscore(pcr: float, pcr_history: list) -> float:
    if not pcr_history:
        return 0
    mean = np.mean(pcr_history)
    std = np.std(pcr_history)
    if std == 0:
        return 0
    return (pcr - mean) / std
