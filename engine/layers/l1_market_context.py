import numpy as np
import polars as pl
from datetime import datetime, time
from models.enums import Regime, VIXBand, Breadth
from models.frames import MarketContextFrame


def compute_ema(series: pl.Series, length: int) -> pl.Series:
    return series.ewm_mean(span=length)


def compute_realized_vol(returns: pl.Series, window: int = 20) -> pl.Series:
    return returns.rolling_std(window) * np.sqrt(252)


def compute_vol_z_diurnal(
    nifty_df: pl.DataFrame,
    current_bucket: int | None = None,
    n_buckets: int = 75,
) -> float:
    """Compute vol z-score using same-time-of-day baseline.

    Compares current realized vol against the historical distribution
    for the same 5-min bucket, correcting for the intraday U-shape pattern
    where vol is high at open/close and low mid-day.
    """
    if len(nifty_df) < n_buckets:
        return 0.0

    returns = nifty_df["close"].pct_change()
    if len(returns) < 22:
        return 0.0

    vol = returns.rolling_std(20).to_list()

    if current_bucket is None:
        current_bucket = (len(nifty_df) - 1) % n_buckets

    bucket_vols = []
    for i in range(current_bucket, len(vol), n_buckets):
        v = vol[i]
        if v is not None and not (isinstance(v, float) and (v != v)):
            bucket_vols.append(v)

    bucket_vols = [v for v in bucket_vols if v is not None]
    if len(bucket_vols) < 3:
        return 0.0

    mean = np.mean(bucket_vols)
    std = np.std(bucket_vols)
    if std == 0:
        return 0.0

    current_vol = vol[-1]
    if current_vol is None:
        return 0.0

    return (current_vol - mean) / std


COLD_START_END = time(10, 45)


def should_use_cold_start(current_time: time) -> bool:
    return current_time < COLD_START_END


def get_cold_start_ema(df_15m: pl.DataFrame) -> pl.Series:
    span = min(9, len(df_15m))
    if span < 2:
        return df_15m["close"]
    return compute_ema(df_15m["close"], span)


def get_primary_ema(df_5m: pl.DataFrame) -> pl.Series:
    return compute_ema(df_5m["close"], 50)


def classify_regime(nifty_df: pl.DataFrame, df_15m: pl.DataFrame | None = None,
                    use_cold_start: bool = False,
                    current_time_bucket: int | None = None) -> tuple:
    SLOPE_THRESHOLD = 0.0003
    VOL_Z_THRESHOLD = 0.5

    if use_cold_start and df_15m is not None and len(df_15m) >= 2:
        ema_series = get_cold_start_ema(df_15m)
        slope = ema_series.diff(1)
    else:
        if len(nifty_df) < 50:
            return Regime.RANGE_BOUND.value, 0.5
        ema_series = get_primary_ema(nifty_df)
        slope = ema_series.diff(5)

    latest_slope = slope.tail(1).to_list()[0] or 0

    # Use diurnal (time-of-day adjusted) vol_z instead of flat 60-day baseline
    latest_vol_z = compute_vol_z_diurnal(nifty_df, current_bucket=current_time_bucket)

    if abs(latest_slope) < SLOPE_THRESHOLD:
        return Regime.RANGE_BOUND.value, 0.6
    if latest_slope > 0:
        return Regime.TRENDING_UP.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65
    return Regime.TRENDING_DOWN.value, 0.85 if latest_vol_z > VOL_Z_THRESHOLD else 0.65


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


def classify_volatility_qualifier(vol_z: float) -> str:
    return "Volatile" if abs(vol_z) > 0.8 else "Normal"


def classify_vix_trajectory(vix_history: list[float], window: int = 5) -> str:
    if len(vix_history) < window:
        return "Stable"
    recent = vix_history[-window:]
    if recent[-1] > recent[0] * 1.05:
        return "Rising"
    elif recent[-1] < recent[0] * 0.95:
        return "Falling"
    return "Stable"


def get_time_bucket(current_time: time) -> str:
    if current_time < time(9, 15):
        return "Pre-Open"
    elif current_time < time(9, 30):
        return "Opening Shock"
    elif current_time < time(10, 45):
        return "Trend Establishment"
    elif current_time < time(12, 0):
        return "Mid-Morning"
    elif current_time < time(13, 0):
        return "Lunch"
    elif current_time < time(14, 30):
        return "Afternoon Recovery"
    else:
        return "Closing Hour"


def compute_breadth(stock_data: dict) -> Breadth:
    above_vwap = 0
    advancers = 0
    decliners = 0
    new_highs = 0
    new_lows = 0
    total = len(stock_data)

    if total == 0:
        return Breadth.MIXED

    for df in stock_data.values():
        if len(df) == 0:
            continue
        latest = df.tail(1)
        close_val = latest["close"].to_list()[0]
        vwap_val = latest["vwap"].to_list()[0]

        if close_val > vwap_val:
            above_vwap += 1

        prev_close = latest["prev_close"].to_list()[0] if "prev_close" in latest.columns else df["close"].head(1).to_list()[0]
        if close_val > prev_close:
            advancers += 1
        elif close_val < prev_close:
            decliners += 1

        session_high = df["close"].max()
        session_low = df["close"].min()
        if close_val >= session_high and len(df) > 1:
            new_highs += 1
        if close_val <= session_low and len(df) > 1:
            new_lows += 1

    vwap_pct = above_vwap / total
    total_ad = advancers + decliners
    ad_norm = advancers / total_ad if total_ad > 0 else 0.5
    total_hl = new_highs + new_lows
    hl_norm = new_highs / total_hl if total_hl > 0 else 0.5

    b = 0.5 * vwap_pct + 0.25 * ad_norm + 0.25 * hl_norm

    if b > 0.60:
        return Breadth.STRONG
    elif b < 0.40:
        return Breadth.WEAK
    return Breadth.MIXED


class L1MarketContext:
    def __init__(self):
        self.vix_history: list[float] = []

    def compute(self, nifty_df: pl.DataFrame, vix_value: float,
                stock_data: dict, df_15m: pl.DataFrame | None = None,
                premarket_bias: str = "Neutral",
                bank_nifty_divergence: float = 0.0,
                event_flag: str | None = None,
                current_time: time | None = None) -> MarketContextFrame:
        self.vix_history.append(vix_value)
        if len(self.vix_history) > 90:
            self.vix_history = self.vix_history[-90:]

        now = current_time or datetime.now().time()
        use_cold = should_use_cold_start(now)

        # Compute current 5-min bucket index (0-74) for diurnal vol baseline
        minutes_since_915 = max(0, (now.hour - 9) * 60 + now.minute - 15)
        current_bucket = max(0, min(74, minutes_since_915 // 5))

        regime, confidence = classify_regime(nifty_df, df_15m, use_cold, current_bucket)
        vix_band = classify_vix_band(vix_value, self.vix_history)
        breadth = compute_breadth(stock_data)

        # Use diurnal vol_z for volatility qualifier
        latest_vol_z = compute_vol_z_diurnal(nifty_df, current_bucket=current_bucket)

        return MarketContextFrame(
            regime=regime,
            regime_confidence=round(confidence, 2),
            volatility_qualifier=classify_volatility_qualifier(latest_vol_z),
            vix_band=vix_band.value,
            vix_value=vix_value,
            vix_trajectory=classify_vix_trajectory(self.vix_history),
            time_bucket=get_time_bucket(now),
            event_flag=event_flag,
            breadth=breadth.value,
            premarket_bias=premarket_bias,
            bank_nifty_divergence=bank_nifty_divergence,
        )
