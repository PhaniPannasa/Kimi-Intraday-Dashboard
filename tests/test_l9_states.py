import pytest
from datetime import datetime, timezone
from engine.layers.l9_monitor import L9ShadowLedger
from models.enums import ThesisState


def make_thesis(thesis_id="t1", symbol="X", direction="LONG",
                setup_type=1, trigger=100, invalidation=95, t1=110, t2=115):
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "direction": direction,
        "setup_type": setup_type,
        "trigger": trigger,
        "invalidation": invalidation,
        "t1": t1,
        "t2": t2,
    }


@pytest.mark.asyncio
async def test_created_to_active():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_create(thesis)
    assert ledger.theses["t1"]["state"] == ThesisState.CREATED.value
    await ledger.on_trigger("t1", entry_price=100)
    assert "t1" in ledger.active
    assert ledger.active["t1"]["state"] == ThesisState.ACTIVE.value


@pytest.mark.asyncio
async def test_pending_expiry():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_create(thesis)
    # on_pending is async; just set the state directly for this test
    thesis["state"] = ThesisState.PENDING.value
    thesis["pending_ts"] = datetime.now(timezone.utc)
    # Also add a t2 thesis for the on_pending call
    t2 = make_thesis(thesis_id="t2")
    await ledger.on_create(t2)
    await ledger.on_pending("t2")
    expired = ledger.on_pending_expiry("11:01")
    assert len(expired) == 2
    for e in expired:
        assert e["state"] == ThesisState.EXPIRED.value


def test_should_extend_vwap():
    ledger = L9ShadowLedger()
    assert ledger.should_extend(2, "13:55", vix_recovering=True, vol_above_80th=True) is True
    assert ledger.should_extend(1, "10:55", vix_recovering=True, vol_above_80th=True) is False
