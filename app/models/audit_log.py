"""Append-only, hash-chained audit log model."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from .base import Base

GENESIS_HASH = "0" * 64


class AuditLog(Base):
    """Tamper-evident audit trail.

    Each row stores HMAC(prev_hash | timestamp | action | actor | detail).
    Editing, deleting or reordering rows breaks the chain (see verify_audit_chain).
    On PostgreSQL a trigger additionally rejects UPDATE/DELETE.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    action = Column(String(50), nullable=False)
    actor = Column(String(100), default="system", nullable=False)
    detail = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog [{self.action}] {self.timestamp}>"
