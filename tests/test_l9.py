import pytest
from datetime import datetime, timezone
from layers.l9_monitor import L9ShadowLedger
from models.enums import ThesisState


def make_thesis(thesis_id="test-1", symbol="RELIANCE", direction="LONG",
                trigger=2500.0, invalidation=2450.0, t1=2550.0, t2=2600.0):
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "direction": direction,
        "trigger": trigger,
        "invalidation": invalidation,
        "t1": t1,
        "t2": t2
    }


@pytest.mark.asyncio
async def test_register_thesis():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.register(thesis)
    assert thesis["thesis_id"] in ledger.active


@pytest.mark.asyncio
async def test_check_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.register(thesis)
    # Price drops below invalidation -- thesis should be invalidated
    invalidated = await ledger.check(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_check_t1_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.register(thesis)
    # Price hits T1
    hits = await ledger.check(price=2560.0)
    assert any(t["thesis_id"] == "test-1" for t in hits)
    # After hitting T1, thesis should no longer be active
    assert "test-1" not in ledger.active
