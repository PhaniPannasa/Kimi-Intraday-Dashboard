from datetime import datetime, timezone
from typing import List

from models.enums import ThesisState


class L9ShadowLedger:
    """Tracks active thesis lifecycles — registration, invalidation, T1/T2 hits, and force expiry."""

    def __init__(self):
        self.active: dict[str, dict] = {}
        self.history: list[dict] = []

    async def on_trigger(self, thesis: dict):
        thesis["state"] = ThesisState.ACTIVE.value
        thesis["entry_ts"] = datetime.now(timezone.utc)
        thesis["entry_price"] = thesis.get("entry_price") or thesis["trigger"]
        thesis["mfe_pct"] = 0.0
        thesis["mae_pct"] = 0.0
        self.active[thesis["thesis_id"]] = thesis

    async def on_tick(self, price: float) -> List[dict]:
        triggered = []
        invalidated = []
        for tid, t in list(self.active.items()):
            entry = t.get("entry_price") or t["trigger"]
            raw_pct = (price - entry) / entry * 100

            # Flip sign for SHORT: favorable moves (price down) become positive
            if t["direction"] == "SHORT":
                raw_pct = -raw_pct

            t["mfe_pct"] = max(t.get("mfe_pct", 0), raw_pct)
            t["mae_pct"] = min(t.get("mae_pct", 0), raw_pct)

            if t["direction"] == "LONG":
                if price >= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)
            else:  # SHORT
                if price <= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)

        return triggered + invalidated

    async def on_force_expire(self) -> List[dict]:
        expired = list(self.active.values())
        for t in expired:
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            self.history.append(t)
        self.active.clear()
        return expired
