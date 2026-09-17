"""Data-access helpers (repository pattern)."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.baseline import BaselineEntry, BaselineSession
from app.models.scan import ScanFinding, ScanSession


# ── Audit helpers ──────────────────────────────────────────────────
def _audit(db: Session, action: str, detail: str | None = None) -> None:
    db.add(AuditLog(action=action, detail=detail))


# ── Baseline ───────────────────────────────────────────────────────
def create_baseline_session(
    db: Session,
    target_path: str,
    file_count: int = 0,
    error_count: int = 0,
    status: str = "completed",
) -> BaselineSession:
    session_obj = BaselineSession(
        target_path=target_path,
        file_count=file_count,
        error_count=error_count,
        status=status,
    )
    db.add(session_obj)
    db.flush()
    _audit(db, "BASELINE_CREATED", f"session_id={session_obj.id} path={target_path}")
    return session_obj


def add_baseline_entries(
    db: Session, session_id: int, entries: list[dict]
) -> int:
    objects = [
        BaselineEntry(session_id=session_id, **entry) for entry in entries
    ]
    db.add_all(objects)
    db.flush()
    return len(objects)


def get_baseline_session(
    db: Session, session_id: int
) -> BaselineSession | None:
    return (
        db.query(BaselineSession)
        .options(joinedload(BaselineSession.entries))
        .filter(BaselineSession.id == session_id)
        .first()
    )


# ── Scan ───────────────────────────────────────────────────────────
def create_scan_session(
    db: Session,
    baseline_id: int,
    total_modified: int = 0,
    total_added: int = 0,
    total_deleted: int = 0,
    total_errors: int = 0,
    status: str = "completed",
) -> ScanSession:
    scan = ScanSession(
        baseline_id=baseline_id,
        total_modified=total_modified,
        total_added=total_added,
        total_deleted=total_deleted,
        total_errors=total_errors,
        status=status,
    )
    db.add(scan)
    db.flush()
    _audit(db, "SCAN_COMPLETED", f"scan_id={scan.id} baseline_id={baseline_id}")
    return scan


def add_scan_findings(
    db: Session, session_id: int, findings: list[dict]
) -> int:
    objects = [
        ScanFinding(session_id=session_id, **finding) for finding in findings
    ]
    db.add_all(objects)
    db.flush()
    return len(objects)


def get_scan_session(
    db: Session, scan_id: int
) -> ScanSession | None:
    return (
        db.query(ScanSession)
        .options(
            joinedload(ScanSession.findings),
            joinedload(ScanSession.baseline),
        )
        .filter(ScanSession.id == scan_id)
        .first()
    )


def list_scan_sessions(db: Session) -> Sequence[ScanSession]:
    return db.query(ScanSession).order_by(ScanSession.created_at.desc()).all()
