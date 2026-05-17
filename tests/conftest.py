import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure engine/ is on sys.path so ``from main import app`` works
_engine_root = Path(__file__).resolve().parent.parent / "engine"
if str(_engine_root) not in sys.path:
    sys.path.insert(0, str(_engine_root))

from main import app  # noqa: E402


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
