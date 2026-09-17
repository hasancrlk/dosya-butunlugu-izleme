"""Baseline session and entry models."""

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class BaselineSession(Base):
    """Represents a single baseline-creation run."""

    __tablename__ = "baseline_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_path = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    file_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String(20), default="completed")
    follow_symlinks = Column(Boolean, default=False, nullable=False)
    signature = Column(String(64), nullable=True)  # HMAC-SHA256 of the entries

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
        Integer, ForeignKey("baseline_sessions.id"), nullable=False, index=True
    )
    file_path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    mtime = Column(Float, nullable=False)
    mode = Column(Integer, nullable=True)
    uid = Column(Integer, nullable=True)
    gid = Column(Integer, nullable=True)

    session = relationship("BaselineSession", back_populates="entries")

    def __repr__(self) -> str:
        return f"<BaselineEntry path='{self.file_path}' sha256='{self.sha256[:12]}…'>"
