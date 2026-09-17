"""Scan session and finding models."""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class ChangeType(str, enum.Enum):
    """Type of change detected during a scan."""

    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    DELETED = "DELETED"


class ScanSession(Base):
    """Represents a single integrity-scan run."""

    __tablename__ = "scan_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    baseline_id = Column(
        Integer, ForeignKey("baseline_sessions.id"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    status = Column(String(20), default="completed")
    total_modified = Column(Integer, default=0)
    total_added = Column(Integer, default=0)
    total_deleted = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    baseline = relationship("BaselineSession")
    findings = relationship(
        "ScanFinding", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ScanSession id={self.id} baseline={self.baseline_id} "
            f"M={self.total_modified} A={self.total_added} D={self.total_deleted}>"
        )


class ScanFinding(Base):
    """Individual change detected by a scan."""

    __tablename__ = "scan_findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("scan_sessions.id"), nullable=False
    )
    file_path = Column(Text, nullable=False)
    change_type = Column(Enum(ChangeType), nullable=False)
    old_hash = Column(String(64), nullable=True)
    new_hash = Column(String(64), nullable=True)
    old_size = Column(BigInteger, nullable=True)
    new_size = Column(BigInteger, nullable=True)
    detail = Column(Text, nullable=True)

    session = relationship("ScanSession", back_populates="findings")

    def __repr__(self) -> str:
        return f"<ScanFinding {self.change_type.value} '{self.file_path}'>"
