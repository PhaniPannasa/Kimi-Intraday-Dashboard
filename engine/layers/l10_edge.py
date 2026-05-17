from typing import Optional
import random

from models.enums import SetupType, Regime, Direction


def wilson_ci(hit_rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = hit_rate
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg FDR correction -- standard step-up procedure.

    1. Sort p-values ascending
    2. Find largest rank k where p_(k) <= (k/m) * alpha
    3. Reject ALL hypotheses with rank <= k
    """
    if not p_values:
        return []
    m = len(p_values)
    sorted_idx = sorted(range(m), key=lambda i: p_values[i])

    k = 0
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            k = rank
        else:
            break

    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if rank <= k:
            significant[idx] = True
    return significant


def bayesian_bootstrap(returns: list[float], n_bootstrap: int = 10000) -> dict:
    """Bayesian bootstrap for mean net return."""
    means = []
    n = len(returns)
    for _ in range(n_bootstrap):
        weights = [random.random() for _ in range(n)]
        total = sum(weights)
        weights = [w / total for w in weights]
        mean = sum(w * r for w, r in zip(weights, returns))
        means.append(mean)
    means.sort()
    return {
        "mean": sum(means) / len(means),
        "ci_lower": means[int(0.025 * n_bootstrap)],
        "ci_upper": means[int(0.975 * n_bootstrap)],
    }


def check_min_samples(n: int, threshold: int = 15) -> bool:
    """Return True if the sample count meets the minimum threshold."""
    return n >= threshold


def check_confidence_interval(hit_rate: float, ci_lower: float, ci_upper: float) -> bool:
    """Return True if the hit rate falls within the confidence interval bounds."""
    return ci_lower <= hit_rate <= ci_upper


class L10EdgeLookup:
    """Edge-statistics lookup table (Layer 10).

    Stores pre-computed edge metrics (hit rate, confidence interval, average
    net return) keyed by ``(setup_type, regime, direction, sector, time_bucket)``
    and answers whether a given combination is statistically significant.
    """

    def __init__(self):
        self.edge_store: dict[tuple, dict] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce(val):
        """Extract ``.value`` from an enum member, or return the raw value."""
        return val.value if isinstance(val, (SetupType, Regime, Direction)) else val

    def _make_key(
        self,
        setup_type: SetupType,
        regime: Regime,
        direction: Direction,
        sector: Optional[int],
        time_bucket: Optional[int],
    ) -> tuple:
        return (
            self._coerce(setup_type),
            self._coerce(regime),
            self._coerce(direction),
            sector,
            time_bucket,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, rows: list[dict]) -> None:
        """Load edge-statistic rows into the lookup store.

        Each row should contain at least the keys
        ``setup_type``, ``regime``, ``direction``, ``sector``, ``time_bucket``,
        ``n``, ``hit_rate``, ``ci_lower``, ``ci_upper``, ``avg_net_return``,
        ``std_net_return``.
        """
        for row in rows:
            key = self._make_key(
                row["setup_type"],
                row["regime"],
                row["direction"],
                row.get("sector"),
                row.get("time_bucket"),
            )
            self.edge_store[key] = row

    def lookup(
        self,
        setup_type: SetupType,
        regime: Regime,
        direction: Direction,
        sector: Optional[int] = None,
        time_bucket: Optional[int] = None,
    ) -> dict:
        """Look up edge statistics for the given combination.

        Returns a dictionary with keys:
        ``setup_type``, ``regime``, ``direction``, ``sector``, ``time_bucket``,
        ``n``, ``hit_rate``, ``ci_lower``, ``ci_upper``, ``is_significant``,
        ``avg_net_return``, ``std_net_return``.

        ``is_significant`` is ``True`` only when all of the following hold:

        * the sample count meets the minimum threshold (>= 15)
        * the hit rate falls within the confidence interval
        * the lower CI bound exceeds 0.35
        """
        key = self._make_key(setup_type, regime, direction, sector, time_bucket)
        row = self.edge_store.get(key, {})

        n = row.get("n", 0)
        hit_rate = row.get("hit_rate", 0.0)
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)

        if n > 0 and ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(hit_rate, n)

        is_significant = (
            check_min_samples(n)
            and check_confidence_interval(hit_rate, ci_lower, ci_upper)
            and ci_lower > 0.35
        )

        return {
            "setup_type": row.get("setup_type", setup_type),
            "regime": row.get("regime", regime),
            "direction": row.get("direction", direction),
            "sector": sector,
            "time_bucket": time_bucket,
            "n": n,
            "hit_rate": hit_rate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "is_significant": is_significant,
            "avg_net_return": row.get("avg_net_return", 0.0),
            "std_net_return": row.get("std_net_return", 0.0),
        }
