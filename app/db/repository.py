"""Data-access helpers (repository pattern)."""

from __future__ import annotations

import hmac
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import GENESIS_HASH, AuditLog
from app.models.baseline import BaselineEntry, BaselineSession
from app.models.scan import ScanFinding, ScanSession
from app.services.integrity import audit_entry_hash


# ── Audit ──────────────────────────────────────────────────────────
def audit(db: Session, action: str, detail: str | None = None, actor: str = "system") -> None:
    last = (
        db.query(AuditLog).order_by(AuditLog.id.desc()).with_for_update().first()
    )
    prev = last.entry_hash if last else GENESIS_HASH
    ts = datetime.now(UTC)
    db.add(AuditLog(
        timestamp=ts, action=action, actor=actor, detail=detail,
        prev_hash=prev, entry_hash=audit_entry_hash(prev, ts, action, actor, detail),
    ))
    db.flush()


def verify_audit_chain(db: Session) -> tuple[bool, int | None]:
    """Return (ok, id_of_first_broken_row)."""
    prev = GENESIS_HASH
    for row in db.query(AuditLog).order_by(AuditLog.id).yield_per(1000):
        expected = audit_entry_hash(prev, row.timestamp, row.action, row.actor, row.detail)
        if row.prev_hash != prev or not hmac.compare_digest(expected, row.entry_hash):
            return False, row.id
        prev = row.entry_hash
    return True, None


# ── Baseline ───────────────────────────────────────────────────────
def create_baseline_session(db: Session, **fields) -> BaselineSession:
    obj = BaselineSession(**fields)
    db.add(obj)
    db.flush()
    audit(db, "BASELINE_CREATED", f"session_id={obj.id} path={obj.target_path}")
    return obj


def add_baseline_entries(db: Session, session_id: int, entries: list[dict]) -> int:
    db.add_all(BaselineEntry(session_id=session_id, **e) for e in entries)
    db.flush()
    return len(entries)


def get_baseline_session(db: Session, session_id: int) -> BaselineSession | None:
    return (
        db.query(BaselineSession)
        .options(joinedload(BaselineSession.entries))
        .filter(BaselineSession.id == session_id)
        .first()
    )


# ── Scan ───────────────────────────────────────────────────────────
def create_scan_session(db: Session, **fields) -> ScanSession:
    scan = ScanSession(**fields)
    db.add(scan)
    db.flush()
    audit(db, "SCAN_COMPLETED", f"scan_id={scan.id} baseline_id={scan.baseline_id}")
    return scan


def add_scan_findings(db: Session, session_id: int, findings: list[dict]) -> int:
    db.add_all(ScanFinding(session_id=session_id, **f) for f in findings)
    db.flush()
    return len(findings)


def get_scan_session(db: Session, scan_id: int) -> ScanSession | None:
    return (
        db.query(ScanSession)
        .options(joinedload(ScanSession.findings), joinedload(ScanSession.baseline))
        .filter(ScanSession.id == scan_id)
        .first()
    )


def list_scan_sessions(db: Session) -> Sequence[ScanSession]:
    return db.query(ScanSession).order_by(ScanSession.created_at.desc()).all()
