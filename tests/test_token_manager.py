import pytest
from config import settings
from core.auth.token_manager import TokenManager


def test_token_manager_returns_token(monkeypatch):
    monkeypatch.setattr(settings, "upstox_analytics_token", "test-token-abc")
    tm = TokenManager()
    token = tm.get_token()
    assert isinstance(token, str)
    assert len(token) > 0
    assert token == "test-token-abc"


def test_token_manager_headers(monkeypatch):
    monkeypatch.setattr(settings, "upstox_analytics_token", "test-token-abc")
    tm = TokenManager()
    headers = tm.get_headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-token-abc"


def test_token_manager_days_until_expiry():
    tm = TokenManager()
    days = tm.days_until_expiry()
    assert isinstance(days, int)
    assert days >= 0
