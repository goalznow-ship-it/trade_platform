"""Stateful early-signal transition monitor backed only by real analysis data."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import logger
from app.core.websocket_manager import ws_manager
from app.models.admin import Notification
from app.models.user import User


class EarlySignalMonitor:
    def __init__(self) -> None:
        self._previous: dict[str, dict] = {}
        self._initialized = False

    @staticmethod
    def quality_score(signal: dict) -> float:
        confidence = float(signal.get("confidence") or 0)
        opportunity = float(signal.get("opportunity_score") or 0)
        execution = signal.get("execution") or {}
        alignment = signal.get("alignment") or {}
        execution_bonus = 8 if execution.get("approved") else 0
        alignment_bonus = 7 if alignment.get("major_aligned") else 0
        return round(
            min(100, confidence * 0.65 + opportunity * 0.2 + execution_bonus + alignment_bonus),
            1,
        )

    @staticmethod
    def _state(signal: dict) -> dict:
        direction = str(signal.get("direction") or "neutral").lower()
        confidence = float(signal.get("confidence") or 0)
        execution = signal.get("execution") or {}
        approved = execution.get("approved") is not False
        if direction not in {"long", "short"}:
            stage = "reject"
        elif confidence >= 70 and approved:
            stage = "confirmed"
        elif confidence >= 50:
            stage = "watch"
        else:
            stage = "reject"
        return {
            "direction": direction,
            "confidence": confidence,
            "stage": stage,
            "quality_score": EarlySignalMonitor.quality_score(signal),
        }

    async def process(self, signals: list[dict]) -> list[dict]:
        current = {
            str(signal.get("symbol")): self._state(signal)
            for signal in signals
            if signal.get("symbol")
        }
        if not self._initialized:
            self._previous = current
            self._initialized = True
            return []

        transitions = []
        for signal in signals:
            symbol = str(signal.get("symbol") or "")
            state = current.get(symbol)
            previous = self._previous.get(symbol)
            if not state or not previous or state["stage"] == "reject":
                continue
            direction_changed = previous["direction"] != state["direction"]
            stage_changed = previous["stage"] != state["stage"]
            confidence_jump = state["confidence"] - previous["confidence"] >= 8
            if state["stage"] == "confirmed" and (stage_changed or direction_changed):
                transitions.append({**state, "symbol": symbol, "type": "signal"})
            elif state["stage"] == "watch" and (
                direction_changed
                or previous["stage"] == "reject"
                or confidence_jump
            ):
                transitions.append({**state, "symbol": symbol, "type": "signal_watch"})

        self._previous = current
        if transitions:
            await self._notify_active_users(transitions)
        return transitions

    async def _notify_active_users(self, transitions: list[dict]) -> None:
        async with async_session_factory() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            pending = []
            for user in users:
                settings = user.notification_settings or {}
                if settings.get("signal_alerts") is False:
                    continue
                for transition in transitions:
                    direction = transition["direction"].upper()
                    confidence = transition["confidence"]
                    quality = transition["quality_score"]
                    if transition["type"] == "signal":
                        title = f"Təsdiqlənmiş {direction}: {transition['symbol']}"
                        message = (
                            f"İnam {confidence:.0f}% · keyfiyyət {quality:.0f}/100. "
                            "Execution gate keçilib; entry, SL və TP-ni AI Terminalda yoxlayın."
                        )
                    else:
                        title = f"Erkən {direction} izləməsi: {transition['symbol']}"
                        message = (
                            f"İnam {confidence:.0f}% · keyfiyyət {quality:.0f}/100. "
                            "Siqnal hələ trade-ready deyil; təsdiq gözlənilir."
                        )
                    notification = Notification(
                        user_id=user.id,
                        type=transition["type"],
                        title=title,
                        message=message,
                        channel="in_app",
                    )
                    db.add(notification)
                    pending.append((user.id, transition, title, message, notification))
            await db.commit()
            for user_id, transition, title, message, notification in pending:
                await ws_manager.send_to_user(
                    user_id,
                    "notification",
                    {
                        "id": notification.id,
                        "type": transition["type"],
                        "title": title,
                        "message": message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    channel="notifications",
                )
        logger.info("Early signal monitor created %s transition alerts", len(transitions))


early_signal_monitor = EarlySignalMonitor()
