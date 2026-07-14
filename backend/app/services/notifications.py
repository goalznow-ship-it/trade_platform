"""
Multi-channel Notification Service
Supports: in-app WebSocket, Telegram, email
"""

from typing import Optional
from datetime import datetime, timezone
from app.core.websocket_manager import ws_manager
from app.core.logging import logger

class NotificationsService:
    async def send_signal_alert(self, user_id: int, signal: dict):
        conf = signal.get('confidence', 0)
        if conf < 85:
            return

        title = f"{'🔥' if conf >= 90 else '✅'} AI HIGH CONFIDENCE SIGNAL"
        message = (
            f"{signal['symbol']}\n"
            f"Direction: {signal['direction'].upper()}\n"
            f"Confidence: {conf}%\n"
            f"Entry: ${signal.get('entry_zone', {}).get('min', 0):.0f}-${signal.get('entry_zone', {}).get('max', 0):.0f}\n"
            f"TP: ${signal.get('take_profit', [0])[2]:.0f}\n"
            f"Risk: {signal.get('risk', 'medium').upper()}"
        )
        await ws_manager.send_to_user(user_id, "signal_alert", {
            "type": "signal_alert",
            "title": title,
            "message": message,
            "signal": signal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Signal alert sent to user {user_id}: {signal['symbol']} {signal['direction']} {conf}%")

    async def send_whale_alert(self, user_id: int, whale: dict):
        title = f"🐋 Whale Alert: {whale['symbol']}"
        message = (
            f"Amount: {whale['amount']}\n"
            f"Value: {whale['value']}\n"
            f"Impact: {whale.get('impact', 0)}% {whale.get('direction', 'neutral').upper()}"
        )
        await ws_manager.send_to_user(user_id, "whale_alert", {
            "type": "whale_alert",
            "title": title,
            "message": message,
            "whale": whale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def send_breakout_alert(self, user_id: int, symbol: str, price: float, direction: str):
        title = f"🚀 Breakout: {symbol}"
        message = f"{symbol} broke {direction.upper()} at ${price:.0f}"
        await ws_manager.send_to_user(user_id, "breakout_alert", {
            "type": "breakout_alert", "title": title, "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def send_tp_alert(self, user_id: int, symbol: str, tp_level: int, price: float):
        title = f"🎯 TP{tp_level} Hit: {symbol}"
        message = f"{symbol} reached TP{tp_level} at ${price:.0f}"
        await ws_manager.send_to_user(user_id, "tp_alert", {
            "type": "tp_alert", "title": title, "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

notifications_service = NotificationsService()
