"""Volume seasonality: adjust raw volume by time-of-day profile."""
import numpy as np


def compute_seasonal_profile(volumes: np.ndarray, n_buckets: int = 75) -> np.ndarray:
    if len(volumes) < n_buckets:
        return np.ones(n_buckets) * np.mean(volumes) if len(volumes) > 0 else np.ones(n_buckets)
    n_days = len(volumes) // n_buckets
    vols_2d = volumes[-n_days * n_buckets:].reshape(n_days, n_buckets)
    return vols_2d.mean(axis=0)


def adjust_volume(raw_volume: float, seasonal_profile: np.ndarray, bucket_idx: int) -> float:
    if bucket_idx < 0 or bucket_idx >= len(seasonal_profile):
        return 1.0
    seasonal = seasonal_profile[bucket_idx]
    return raw_volume / seasonal if seasonal > 0 else 1.0


def compute_volume_confirm(v_adj: float, median_adj: float) -> bool:
    return v_adj >= 1.5 * median_adj


def compute_volume_zscore(v_adj: float, mean_adj: float, std_adj: float) -> float:
    if std_adj == 0:
        return 0.0
    return (v_adj - mean_adj) / std_adj
