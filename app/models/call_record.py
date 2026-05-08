"""
Call Record SQLAlchemy model.
Extended to store NLP pre-classification fields:
  sentiment, intent, priority
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class CallRecord(Base):
    __tablename__ = "call_records"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employee_id = Column(Integer, nullable=True, index=True)
    visitor_name = Column(String(255), nullable=True)
    audio_path  = Column(String(255), nullable=True)
    duration    = Column(String(50),  nullable=True)
    status      = Column(String(50),  default="Completed")

    transcript  = Column(Text,        nullable=True)
    rating      = Column(Integer,     nullable=True)
    explanation = Column(Text,        nullable=True)

    # Store JSON arrays as Text strings (SQLite-compatible)
    strengths   = Column(Text, nullable=True)
    weaknesses  = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)

    # ── NLP pre-classification fields (added for hybrid AI pipeline) ──────────
    sentiment   = Column(String(20),  nullable=True)   # positive | negative | neutral
    intent      = Column(String(30),  nullable=True)   # complaint | request | information | other
    priority    = Column(String(10),  nullable=True)   # low | medium | high

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
