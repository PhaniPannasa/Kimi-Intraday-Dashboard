import numpy as np
import polars as pl
from models.enums import Regime, VIXBand, Breadth
from models.frames import MarketContextFrame


def compute_ema(series: pl.Series, length: int) -> pl.Series:
    return series.ewm_mean(span=length)


def compute_realized_vol(returns: pl.Series, window: int = 20) -> pl.Series:
    return returns.rolling_std(window) * np.sqrt(252)


def classify_regime(nifty_df: pl.DataFrame) -> tuple:
    if len(nifty_df) < 50:
        return Regime.RANGE_BOUND.value, 0.5

    returns = nifty_df["close"].pct_change()
    vol = compute_realized_vol(returns, 20)
    vol_baseline = vol.rolling_mean(60 * 75)
    vol_zscore = (vol - vol_baseline) / vol_baseline.rolling_std(60 * 75)

    ema50 = compute_ema(nifty_df["close"], 50)
    slope = ema50.diff(5)

    latest_vol_z = vol_zscore.tail(1).to_list()[0] or 0
    latest_slope = slope.tail(1).to_list()[0] or 0

    if latest_slope > 0 and latest_vol_z > 0.5:
        return Regime.TRENDING_UP.value, 0.85
    elif latest_slope < 0 and latest_vol_z > 0.5:
        return Regime.TRENDING_DOWN.value, 0.85
    elif latest_slope > 0:
        return Regime.TRENDING_UP.value, 0.65
    elif latest_slope < 0:
        return Regime.TRENDING_DOWN.value, 0.65
    else:
        return Regime.RANGE_BOUND.value, 0.7


def classify_vix_band(vix_value: float, vix_history: list) -> VIXBand:
    if len(vix_history) < 10:
        return VIXBand.NORMAL
    p20 = np.percentile(vix_history, 20)
    p80 = np.percentile(vix_history, 80)
    if vix_value < p20:
        return VIXBand.COMPRESSED
    elif vix_value > p80:
        return VIXBand.ELEVATED
    return VIXBand.NORMAL


def compute_breadth(stock_data: dict) -> Breadth:
    above_vwap = 0
    advancers = 0
    decliners = 0
    total = len(stock_data)
    if total == 0:
        return Breadth.MIXED

    for df in stock_data.values():
        if len(df) == 0:
            continue
        latest = df.tail(1)
        if latest["close"].to_list()[0] > latest["vwap"].to_list()[0]:
            above_vwap += 1
        if len(df) > 1:
            if df["close"].tail(1).to_list()[0] > df["close"].head(1).to_list()[0]:
                advancers += 1
            else:
                decliners += 1

    vwap_pct = above_vwap / total
    ad_ratio = advancers / max(decliners, 1)
    hl_ratio = advancers / total if total > 0 else 0.5
    b = 0.5 * vwap_pct + 0.25 * ad_ratio + 0.25 * hl_ratio

    if b > 0.60:
        return Breadth.STRONG
    elif b < 0.40:
        return Breadth.WEAK
    return Breadth.MIXED


class L1MarketContext:
    def __init__(self):
        self.vix_history = []

    def compute(self, nifty_df: pl.DataFrame, vix_value: float, stock_data: dict) -> MarketContextFrame:
        self.vix_history.append(vix_value)
        regime, confidence = classify_regime(nifty_df)
        vix_band = classify_vix_band(vix_value, self.vix_history)
        breadth = compute_breadth(stock_data)

        return MarketContextFrame(
            regime=regime,
            regime_confidence=confidence,
            volatility_qualifier="Normal",
            vix_band=vix_band.value,
            vix_trajectory="Stable",
            time_bucket="Trend Establishment",
            breadth=breadth.value,
            premarket_bias="Neutral",
        )
