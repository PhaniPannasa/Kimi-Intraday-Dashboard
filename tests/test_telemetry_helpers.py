"""Unit tests for core/telemetry.py — pure functions, no fixtures."""

import sys
from pathlib import Path

_engine_root = Path(__file__).resolve().parent.parent / "engine"
if str(_engine_root) not in sys.path:
    sys.path.insert(0, str(_engine_root))

from unittest.mock import MagicMock

from core.telemetry import (
    endpoint_source,
    pipeline_phase,
    layers_realness,
    snapshot,
)


def _fake_pipeline_empty():
    p = MagicMock()
    p.latest_context = None
    p.latest_long_rankings = []
    p.latest_short_rankings = []
    p.latest_theses = []
    p.aggregator = MagicMock()
    p.aggregator._buffers = {}
    return p


def _fake_pipeline_with_rankings():
    p = _fake_pipeline_empty()
    p.latest_long_rankings = [MagicMock()]
    return p


def test_endpoint_source_market_context_empty_returns_mock():
    p = _fake_pipeline_empty()
    assert endpoint_source(p, "/market/context") == "mock"


def test_endpoint_source_rankings_with_data_returns_pipeline():
    p = _fake_pipeline_with_rankings()
    assert endpoint_source(p, "/rankings/top25/long") == "pipeline"


def test_endpoint_source_unknown_path_returns_unknown():
    p = _fake_pipeline_empty()
    assert endpoint_source(p, "/nonexistent/path") == "unknown"


def test_pipeline_phase_closed_when_no_session():
    p = _fake_pipeline_empty()
    session = MagicMock()
    session.current_phase.return_value = "closed"
    assert pipeline_phase(p, session) == "closed"


def test_layers_realness_all_false_when_empty():
    p = _fake_pipeline_empty()
    flags = layers_realness(p)
    for k in ("l1_real", "l3_real", "l5_real", "l6_real", "l8_real", "l10_real"):
        assert flags[k] is False, f"{k} should be False for empty pipeline"


def test_layers_realness_l1_true_when_context_has_real_vix():
    p = _fake_pipeline_empty()
    ctx = MagicMock()
    ctx.vix_value = 23.5  # not the hardcoded 15.0
    p.latest_context = ctx
    assert layers_realness(p)["l1_real"] is True


def test_layers_realness_l1_false_when_vix_is_placeholder():
    p = _fake_pipeline_empty()
    ctx = MagicMock()
    ctx.vix_value = 15.0  # placeholder
    p.latest_context = ctx
    assert layers_realness(p)["l1_real"] is False


def test_layers_realness_all_values_are_bools():
    """Regression: l10_real used to leak a dict or MagicMock through the `and` short-circuit;
    every l*_real value must be a Python bool so the JSON output is consistent."""
    p = _fake_pipeline_empty()
    flags = layers_realness(p)
    for k, v in flags.items():
        assert isinstance(v, bool), f"{k}={v!r} (type {type(v).__name__}) should be bool"


def test_layers_realness_l10_true_when_edge_store_populated():
    p = _fake_pipeline_empty()
    p.l10 = MagicMock()
    p.l10.edge_store = {("breakout", "trending-up"): "tier-1-stats"}
    assert layers_realness(p)["l10_real"] is True


def test_layers_realness_l10_false_when_edge_store_empty_dict():
    p = _fake_pipeline_empty()
    p.l10 = MagicMock()
    p.l10.edge_store = {}
    assert layers_realness(p)["l10_real"] is False


def test_snapshot_returns_full_dict_shape():
    p = _fake_pipeline_empty()
    session = MagicMock()
    session.current_phase.return_value = "closed"
    snap = snapshot(p, session, ws_connections=2, scheduler_running=True)
    assert "endpoints" in snap
    assert "pipeline" in snap
    assert "layers" in snap
    assert snap["pipeline"]["phase"] == "closed"
    assert snap["pipeline"]["ws_connections"] == 2
    assert snap["pipeline"]["scheduler_running"] is True
    assert isinstance(snap["timestamp"], str)
