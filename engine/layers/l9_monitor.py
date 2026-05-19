from datetime import datetime, timezone, time
from typing import List

from db.timescale import db as timescale_db
from models.enums import ThesisState, SetupType


SETUP_PENDING_EXPIRY = {
    SetupType.ORB_15MIN: time(11, 0),
    SetupType.VWAP_RECLAIM: time(14, 0),
    SetupType.SUPERTREND_PULLBACK: time(14, 30),
    SetupType.MEAN_REVERSION: time(13, 30),
    SetupType.FIRST_HOUR_BREAKOUT: time(12, 0),
    SetupType.CPR_BREAKOUT: time(14, 0),
}

FORCE_EXPIRE_TIME = time(15, 15)
EXTENSIBLE_SETUPS = {SetupType.VWAP_RECLAIM, SetupType.SUPERTREND_PULLBACK}
EXTENSION_MINUTES = 30


class L9ShadowLedger:
    """Tracks thesis lifecycles: CREATED -> PENDING -> ACTIVE -> terminal."""

    def __init__(self):
        self.theses: dict[str, dict] = {}
        self.active: dict[str, dict] = {}
        self.history: list[dict] = []
        self._db = timescale_db

    async def _persist_outcome(self, thesis: dict, exit_reason: str, exit_price: float):
        """INSERT a row into thesis_outcomes hypertable."""
        try:
            await self._db.execute(
                """
                INSERT INTO thesis_outcomes
                (thesis_id, symbol, setup_type, regime, direction, sector, time_bucket,
                 entry_price, exit_price, exit_reason, mfe_pct, mae_pct,
                 net_return, r_multiple, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW())
                """,
                thesis.get("thesis_id"),
                thesis.get("symbol"),
                thesis.get("setup_type", 1),
                thesis.get("regime", "Range-Bound"),
                thesis.get("direction", "LONG"),
                thesis.get("sector", "Bank"),
                thesis.get("time_bucket", "Trend Establishment"),
                thesis.get("entry_price"),
                exit_price,
                exit_reason,
                thesis.get("mfe_pct", 0.0),
                thesis.get("mae_pct", 0.0),
                thesis.get("net_return", 0.0),
                thesis.get("r_multiple", 0.0),
            )
        except Exception:
            pass

    async def on_create(self, thesis: dict):
        thesis["state"] = ThesisState.CREATED.value
        thesis["created_ts"] = datetime.now(timezone.utc)
        self.theses[thesis["thesis_id"]] = thesis

    async def on_pending(self, thesis_id: str):
        t = self.theses.get(thesis_id)
        if t:
            t["state"] = ThesisState.PENDING.value
            t["pending_ts"] = datetime.now(timezone.utc)

    async def on_trigger(self, thesis_id: str, entry_price: float):
        t = self.theses.pop(thesis_id, None)
        if t is None:
            return
        t["state"] = ThesisState.ACTIVE.value
        t["entry_ts"] = datetime.now(timezone.utc)
        t["entry_price"] = entry_price
        t["mfe_pct"] = 0.0
        t["mae_pct"] = 0.0
        self.active[thesis_id] = t

    async def on_pending_expiry(self, current_time_str: str) -> List[dict]:
        h, m = map(int, current_time_str.split(":"))
        now = time(h, m)
        expired = []
        for tid, t in list(self.theses.items()):
            if t["state"] not in (ThesisState.CREATED.value, ThesisState.PENDING.value):
                continue
            setup = SetupType(t.get("setup_type", 1))
            expiry = SETUP_PENDING_EXPIRY.get(setup, FORCE_EXPIRE_TIME)
            if now >= expiry:
                t["state"] = ThesisState.EXPIRED.value
                t["exit_ts"] = datetime.now(timezone.utc)
                expired.append(t)
                del self.theses[tid]
                self.history.append(t)
        for t in expired:
            await self._persist_outcome(t, "EXPIRED", t.get("exit_price", 0.0))
        return expired

    def should_extend(self, setup_type: int, current_time_str: str,
                      vix_recovering: bool = False, vol_above_80th: bool = False) -> bool:
        setup = SetupType(setup_type)
        if setup not in EXTENSIBLE_SETUPS:
            return False
        return vix_recovering and vol_above_80th

    async def on_tick(self, price: float) -> List[dict]:
        terminal = []
        for tid, t in list(self.active.items()):
            entry = t.get("entry_price") or t["trigger"]
            raw_pct = (price - entry) / entry * 100
            if t["direction"] == "SHORT":
                raw_pct = -raw_pct
            t["mfe_pct"] = max(t.get("mfe_pct", 0), raw_pct)
            t["mae_pct"] = min(t.get("mae_pct", 0), raw_pct)
            hit = self._check_exits(t, price)
            if hit:
                terminal.append(hit)
                del self.active[tid]
                self.history.append(hit)
                await self._persist_outcome(hit, hit["state"], hit["exit_price"])
        return terminal

    def _check_exits(self, t: dict, price: float) -> dict | None:
        if t["direction"] == "LONG":
            if price >= t["t2"]:
                t["state"] = ThesisState.T2_HIT.value
                return self._finalize(t, price)
            elif price >= t["t1"]:
                t["state"] = ThesisState.T1_HIT.value
                return self._finalize(t, price)
            elif price <= t["invalidation"]:
                t["state"] = ThesisState.STOPPED_OUT.value
                return self._finalize(t, price)
        else:
            if price <= t["t2"]:
                t["state"] = ThesisState.T2_HIT.value
                return self._finalize(t, price)
            elif price <= t["t1"]:
                t["state"] = ThesisState.T1_HIT.value
                return self._finalize(t, price)
            elif price >= t["invalidation"]:
                t["state"] = ThesisState.STOPPED_OUT.value
                return self._finalize(t, price)
        return None

    def _finalize(self, t: dict, exit_price: float) -> dict:
        t["exit_price"] = exit_price
        t["exit_ts"] = datetime.now(timezone.utc)
        entry = t.get("entry_price") or t["trigger"]
        invalidation = t["invalidation"]

        if t["direction"] == "LONG":
            gross_return_pct = (exit_price - entry) / entry * 100
        else:
            gross_return_pct = (entry - exit_price) / entry * 100
        t["gross_return_pct"] = round(gross_return_pct, 4)

        cost_pct = t.get("cost_breakdown", {}).get("cost_pct", 0.0) if isinstance(t.get("cost_breakdown"), dict) else 0.0
        t["net_return_pct"] = round(gross_return_pct - cost_pct, 4)

        risk = abs(entry - invalidation)
        risk_pct = risk / entry
        t["r_multiple"] = round(gross_return_pct / (risk_pct * 100), 4) if risk_pct > 0 else 0.0

        created_ts = t.get("created_ts")
        entry_ts = t.get("entry_ts")
        if created_ts and entry_ts:
            t["time_to_trigger_min"] = int((entry_ts - created_ts).total_seconds() / 60)
        exit_ts = t["exit_ts"]
        if entry_ts and exit_ts:
            t["time_to_exit_min"] = int((exit_ts - entry_ts).total_seconds() / 60)
        return t

    async def on_force_expire(self) -> List[dict]:
        expired = list(self.active.values())
        for t in expired:
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            self.history.append(t)
        self.active.clear()
        for t in list(self.theses.values()):
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            expired.append(t)
            self.history.append(t)
        self.theses.clear()
        for t in expired:
            await self._persist_outcome(t, "FORCE_EXPIRED", t.get("exit_price", 0.0))
        return expired

    # Backward-compatible method for old on_trigger signature
    async def on_trigger_legacy(self, thesis: dict):
        thesis["state"] = ThesisState.ACTIVE.value
        thesis["entry_ts"] = datetime.now(timezone.utc)
        thesis["entry_price"] = thesis.get("entry_price") or thesis["trigger"]
        thesis["mfe_pct"] = 0.0
        thesis["mae_pct"] = 0.0
        self.active[thesis["thesis_id"]] = thesis
