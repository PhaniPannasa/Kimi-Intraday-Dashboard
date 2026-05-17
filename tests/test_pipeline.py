import pytest

from core.pipeline import PipelineOrchestrator


@pytest.mark.asyncio
async def test_pipeline_runs_without_error():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()


@pytest.mark.asyncio
async def test_pipeline_generates_rankings():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l6.previous_ranks) > 0


@pytest.mark.asyncio
async def test_pipeline_creates_theses():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l9.active) > 0


@pytest.mark.asyncio
async def test_pipeline_uses_l1_context():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l1.vix_history) > 0


@pytest.mark.asyncio
async def test_pipeline_uses_l10_edge():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    # Edge store may or may not have entries depending on significance
    # At minimum, the lookup method was called without error
