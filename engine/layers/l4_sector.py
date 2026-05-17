import numpy as np

SECTORS = [
    "Auto", "Bank", "FMCG", "IT", "Media",
    "Metal", "Pharma", "PSU Bank", "Realty", "Energy", "Telecom"
]


def compute_rs_ratio(sector_return: float, nifty_return: float, rolling_std: float) -> float:
    if rolling_std == 0:
        return 1.0
    return (sector_return / max(nifty_return, 0.0001)) / rolling_std


def compute_rs_momentum(rs_series: list) -> float:
    if len(rs_series) < 5:
        return 0.0
    return rs_series[-1] - rs_series[-5]


def rank_sectors(sector_returns: dict, nifty_return: float,
                 sector_histories: dict) -> list:
    results = []
    for sector, ret in sector_returns.items():
        hist = sector_histories.get(sector, [])
        std = np.std(hist) if hist else 0.01
        rs = compute_rs_ratio(ret, nifty_return, std)
        momentum = compute_rs_momentum(hist)
        results.append({"sector": sector, "rs_ratio": rs, "rs_momentum": momentum})
    results.sort(key=lambda x: x["rs_ratio"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


class L4Sector:
    def compute(self, sector_returns: dict, nifty_return: float, histories: dict) -> list:
        return rank_sectors(sector_returns, nifty_return, histories)
