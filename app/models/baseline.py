"""Baseline session and entry models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class BaselineSession(Base):
    """Represents a single baseline-creation run."""

    __tablename__ = "baseline_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_path = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    file_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String(20), default="completed")

    entries = relationship(
        "BaselineEntry", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BaselineSession id={self.id} path='{self.target_path}'>"


class BaselineEntry(Base):
    """A single file record inside a baseline."""

    __tablename__ = "baseline_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("baseline_sessions.id"), nullable=False
    )
    file_path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    mtime = Column(Float, nullable=False)

    session = relationship("BaselineSession", back_populates="entries")

    def __repr__(self) -> str:
        return f"<BaselineEntry path='{self.file_path}' sha256='{self.sha256[:12]}…'>"
