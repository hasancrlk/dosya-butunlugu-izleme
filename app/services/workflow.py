"""Baseline/scan workflows shared by the API and the CLI (single source of truth)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import repository as repo
from app.models.baseline import BaselineSession
from app.models.scan import ScanSession
from app.services.diff_engine import DiffReport, compute_diff
from app.services.integrity import sign_baseline, verify_baseline
from app.services.scanner import ScanResult, scan_directory


class BaselineNotFoundError(Exception):
    pass


class BaselineTamperedError(Exception):
    pass


def create_baseline(
    db: Session, target_path: str, follow_symlinks: bool | None = None
) -> tuple[BaselineSession, ScanResult]:
    target = str(Path(target_path).resolve())
    if follow_symlinks is None:
        follow_symlinks = get_settings().FOLLOW_SYMLINKS

    result = scan_directory(target, follow_symlinks=follow_symlinks)
    entries = [
        {k: getattr(r, k) for k in ("file_path", "sha256", "size_bytes", "mtime", "mode", "uid", "gid")}
        for r in result.file_records
    ]
    session = repo.create_baseline_session(
        db,
        target_path=target,
        follow_symlinks=follow_symlinks,
        file_count=result.file_count,
        error_count=result.error_count,
        signature=sign_baseline(target, follow_symlinks, entries),
    )
    repo.add_baseline_entries(db, session.id, entries)
    return session, result


def run_scan(db: Session, baseline_id: int) -> tuple[ScanSession, DiffReport, ScanResult]:
    baseline = repo.get_baseline_session(db, baseline_id)
    if baseline is None:
        raise BaselineNotFoundError(baseline_id)

    if not verify_baseline(baseline):
        repo.audit(db, "BASELINE_TAMPER_DETECTED", f"baseline_id={baseline_id}")
        db.commit()  # keep the alarm even though the request fails
        raise BaselineTamperedError(baseline_id)

    result = scan_directory(baseline.target_path, follow_symlinks=baseline.follow_symlinks)
    diff = compute_diff(baseline.entries, result.file_records, result.failed)

    scan = repo.create_scan_session(
        db,
        baseline_id=baseline.id,
        total_modified=diff.total_modified,
        total_added=diff.total_added,
        total_deleted=diff.total_deleted,
        total_errors=result.error_count,
    )
    repo.add_scan_findings(db, scan.id, [asdict(f) for f in diff.findings])
    return scan, diff, result
