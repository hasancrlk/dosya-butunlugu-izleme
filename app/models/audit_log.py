"""Append-only audit log model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from .base import Base


class AuditLog(Base):
    """Immutable audit trail — INSERT only, never UPDATE or DELETE."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    action = Column(String(50), nullable=False)
    actor = Column(String(100), default="system")
    detail = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog [{self.action}] {self.timestamp}>"
