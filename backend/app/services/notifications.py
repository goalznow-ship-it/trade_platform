import httpx
from typing import Optional, List
from app.core.config import settings
from app.core.logging import logger

class NotificationService:
    def __init__(self):
        self.logger = logger

    async def send_telegram(self, chat_id: str, message: str) -> bool:
        if not settings.TELEGRAM_BOT_TOKEN:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def send_discord(self, webhook_url: str, message: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json={'content': message})
                return resp.status_code == 204
        except Exception:
            return False

    async def send_signal_notification(self, user_id: int, signal: dict, channels: List[str]):
        message = self._format_signal_message(signal)
        for channel in channels:
            if channel == 'telegram':
                await self.send_telegram(str(user_id), message)
            elif channel == 'discord':
                await self.send_discord(str(user_id), message)

    def _format_signal_message(self, signal: dict) -> str:
        direction_emoji = '🟢' if signal['direction'] == 'long' else '🔴'
        msg = (
            f"{direction_emoji} <b>TRADE SIGNAL</b>\n"
            f"Symbol: {signal['symbol']}\n"
            f"Direction: <b>{signal['direction'].upper()}</b>\n"
            f"Confidence: {signal['confidence']}%\n"
            f"Entry: ${signal['entry_price']}\n"
            f"SL: ${signal['stop_loss']}\n"
            f"TP1: ${signal['take_profit_1']}\n"
            f"TP2: ${signal['take_profit_2'] if signal.get('take_profit_2') else 'N/A'}\n"
            f"RR: {signal['risk_reward']}\n"
            f"Leverage: {signal['leverage']}x\n"
            f"Reason: {signal.get('reason', 'N/A')}"
        )
        return msg

notification_service = NotificationService()
