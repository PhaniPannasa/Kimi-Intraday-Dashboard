from config import settings
from telegram.ext import Application


class TelegramAlerter:
    def __init__(self):
        self.chat_id = settings.telegram_chat_id
        self.bot = None
        if settings.telegram_bot_token:
            self.bot = Application.builder().token(settings.telegram_bot_token).build().bot

    async def send(self, message: str):
        if self.bot and self.chat_id:
            await self.bot.send_message(chat_id=self.chat_id, text=message)

    def format_thesis_alert(self, thesis: dict) -> str:
        lines = [
            f"*New Thesis: {thesis['symbol']}*",
            f"Direction: {thesis['direction']}",
            f"Trigger: {thesis.get('trigger', 'N/A')}",
            f"T1: {thesis.get('t1', 'N/A')}",
            f"T2: {thesis.get('t2', 'N/A')}",
            f"Invalidation: {thesis.get('invalidation', 'N/A')}",
            f"Grade: {thesis.get('grade', 'N/A')}",
            f"Net R:R: {thesis.get('net_rr', 'N/A')}",
        ]
        return "\n".join(lines)

    def format_invalidation_alert(self, thesis: dict, reason: str) -> str:
        return f"*Invalidated: {thesis['symbol']}*\nReason: {reason}\nState: {thesis.get('state', 'N/A')}"


alert = TelegramAlerter()
