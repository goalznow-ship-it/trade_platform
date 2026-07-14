from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TradeRating(str, enum.Enum):
    PERFECT = "perfect"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    BAD = "bad"


class Emotion(str, enum.Enum):
    CONFIDENT = "confident"
    HOPEFUL = "hopeful"
    NEUTRAL = "neutral"
    ANXIOUS = "anxious"
    GREEDY = "greedy"
    FEARFUL = "fearful"
    REVENGE = "revenge"
    FOMO = "fomo"


class MistakeType(str, enum.Enum):
    FOMO_ENTRY = "fomo_entry"
    EARLY_EXIT = "early_exit"
    LATE_EXIT = "late_exit"
    NO_STOP_LOSS = "no_stop_loss"
    OVERTRADING = "overtrading"
    WRONG_DIRECTION = "wrong_direction"
    POOR_RISK_MGMT = "poor_risk_management"
    CHASE_PRICE = "chase_price"
    IGNORED_SIGNAL = "ignored_signal"
    BAD_TIMING = "bad_timing"
    OVERLEVERAGE = "overleverage"
    OTHER = "other"


class TradeJournal(Base):
    __tablename__ = "trade_journals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_id = Column(Integer, ForeignKey("trade_history.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)

    notes = Column(Text, nullable=True)
    lessons = Column(Text, nullable=True)
    emotion = Column(String(20), nullable=True)
    mistakes = Column(JSON, default=list)
    tags = Column(JSON, default=list)

    strategy = Column(String(100), nullable=True)
    setup_description = Column(Text, nullable=True)
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)

    rating = Column(String(10), nullable=True)
    win_loss_reason = Column(Text, nullable=True)
    screenshot_urls = Column(JSON, default=list)

    executed_plan = Column(Boolean, default=False)
    followed_rules = Column(Boolean, default=False)
    psychological_state = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
