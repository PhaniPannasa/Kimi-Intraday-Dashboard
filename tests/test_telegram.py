import pytest
from unittest.mock import AsyncMock, patch
from core.alerts.telegram import TelegramAlerter


@pytest.mark.asyncio
async def test_send_alert_calls_bot():
    with patch("core.alerts.telegram.Application") as mock_app:
        alerter = TelegramAlerter()
        mock_bot = AsyncMock()
        alerter.bot = mock_bot
        alerter.chat_id = "12345"
        await alerter.send("Test message")
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_format_thesis_alert():
    alerter = TelegramAlerter()
    thesis = {
        "symbol": "RELIANCE", "direction": "LONG",
        "trigger": 2500, "t1": 2550, "grade": "ATTRACTIVE"
    }
    msg = alerter.format_thesis_alert(thesis)
    assert "RELIANCE" in msg
    assert "LONG" in msg
    assert "ATTRACTIVE" in msg
