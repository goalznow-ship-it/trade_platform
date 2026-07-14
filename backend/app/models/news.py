from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True)
    source = Column(String(100))
    category = Column(String(50), default="crypto")
    summary = Column(Text)
    content = Column(Text)
    author = Column(String(100))
    published_at = Column(DateTime)
    language = Column(String(10), default="en")
    image_url = Column(String(1000))
    is_analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NewsAnalysis(Base):
    __tablename__ = "news_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    news_id = Column(Integer, index=True, nullable=False)
    sentiment = Column(String(20))
    sentiment_score = Column(Float)
    impact_score = Column(Float)
    relevant_symbols = Column(JSON)
    market_impact = Column(String(20))
    summary = Column(Text)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
