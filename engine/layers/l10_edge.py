from typing import Optional

from models.enums import SetupType, Regime, Direction


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
