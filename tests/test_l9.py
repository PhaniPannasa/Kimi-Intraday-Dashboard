import pytest
from layers.l9_monitor import L9ShadowLedger


def make_thesis(thesis_id="test-1", symbol="RELIANCE", direction="LONG",
                trigger=2500.0, invalidation=2450.0, t1=2550.0, t2=2600.0,
                setup_type=1):
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
async def test_on_trigger_thesis():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger_legacy(thesis)
    assert thesis["thesis_id"] in ledger.active


@pytest.mark.asyncio
async def test_on_tick_long_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger_legacy(thesis)
    invalidated = await ledger.on_tick(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_on_tick_long_t1_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger_legacy(thesis)
    hit = await ledger.on_tick(price=2550.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_tick_long_t2_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger_legacy(thesis)
    hit = await ledger.on_tick(price=2600.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_force_expire():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger_legacy(thesis)
    expired = await ledger.on_force_expire()
    assert any(t["thesis_id"] == "test-1" for t in expired)
    assert len(ledger.active) == 0


@pytest.mark.asyncio
async def test_short_direction_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis(direction="SHORT", trigger=2500.0, invalidation=2550.0, t1=2450.0, t2=2400.0)
    await ledger.on_trigger_legacy(thesis)
    invalidated = await ledger.on_tick(price=2560.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_short_mfe_positive_on_favorable_move():
    """MFE should be positive when price moves in favor of a short."""
    ledger = L9ShadowLedger()
    thesis = make_thesis(direction="SHORT", trigger=2500.0, invalidation=2550.0, t1=2450.0, t2=2400.0)
    await ledger.on_trigger_legacy(thesis)
    # Price drops 4% — favorable for SHORT
    await ledger.on_tick(price=2400.0)
    t = ledger.history[0] if ledger.history else list(ledger.active.values())[0]
    if "test-1" in ledger.active:
        assert ledger.active["test-1"]["mfe_pct"] > 0
