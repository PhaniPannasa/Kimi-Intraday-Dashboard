"""Dual-timeframe indicator computation (5-min + 15-min).

Per system_design_final.md Section 5.3:
- EMA(9/20/50), Supertrend(10,3.0), ADX(14), RSI(14),
  MACD(12,26,9), ATR(14), Bollinger Bands(20,2sigma)
- All computed on BOTH 5-min and 15-min timeframes
- ROC is stock return - Nifty return (Nifty-relative)
- ATR percentile is distributional (rank within 20-day history)
"""
import pandas as pd
import numpy as np


def _ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=length, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = (high - high.shift()).clip(lower=0)
    minus_dm = (low.shift() - low).clip(lower=0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)

    plus_di = 100 * (plus_dm.ewm(alpha=1/length, adjust=False).mean() / tr.ewm(alpha=1/length, adjust=False).mean())
    minus_di = 100 * (minus_dm.ewm(alpha=1/length, adjust=False).mean() / tr.ewm(alpha=1/length, adjust=False).mean())
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/length, adjust=False).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD — returns (macd line, signal line, histogram)."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 10, multiplier: float = 3.0):
    """Supertrend indicator — returns (supertrend series, direction series)."""
    atr = _atr(high, low, close, length)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr
    direction = pd.Series(1, index=close.index)

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == 1:
                upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i-1])
            else:
                lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i-1])

    supertrend = pd.Series(np.where(direction == 1, lower_band, upper_band), index=close.index)
    return supertrend, direction


def _bbands(series: pd.Series, length: int = 20, std: float = 2.0):
    """Bollinger Bands — returns (upper, middle, lower, bandwidth)."""
    middle = series.ewm(span=length, adjust=False).mean()
    std_dev = series.rolling(length).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bandwidth = (upper - lower) / middle
    return upper, middle, lower, bandwidth


def compute_indicators_single_tf(df: pd.DataFrame, suffix: str = "5m") -> pd.DataFrame:
    df = df.copy()
    df[f"ema_9_{suffix}"] = _ema(df["close"], length=9)
    df[f"ema_20_{suffix}"] = _ema(df["close"], length=20)
    df[f"ema_50_{suffix}"] = _ema(df["close"], length=50)

    st, st_dir = _supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3.0)
    df[f"supertrend_{suffix}"] = st
    df[f"supertrend_dir_{suffix}"] = st_dir

    df[f"adx_{suffix}"] = _adx(df["high"], df["low"], df["close"], length=14)
    df[f"rsi_{suffix}"] = _rsi(df["close"], length=14)

    macd_line, macd_signal, macd_hist = _macd(df["close"], fast=12, slow=26, signal=9)
    df[f"macd_{suffix}"] = macd_line
    df[f"macd_signal_{suffix}"] = macd_signal
    df[f"macd_hist_{suffix}"] = macd_hist

    atr_series = _atr(df["high"], df["low"], df["close"], length=14)
    df[f"atr_{suffix}"] = atr_series

    atr_lookback = 20 * 75 if suffix == "5m" else 20 * 25
    df[f"atr_pctile_{suffix}"] = (
        atr_series.rolling(atr_lookback, min_periods=5)
        .apply(lambda x: (x < x.iloc[-1]).sum() / len(x) if len(x) > 0 else 0.5)
    )

    bb_upper, _, bb_lower, bb_width = _bbands(df["close"], length=20, std=2)
    df[f"bb_upper_{suffix}"] = bb_upper
    df[f"bb_lower_{suffix}"] = bb_lower
    df[f"bb_width_{suffix}"] = bb_width

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