"""Diff engine — compare baseline entries with a fresh directory scan."""

from __future__ import annotations

import stat
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.models.scan import ChangeType
from app.services.hasher import HashResult


@dataclass
class DiffFinding:
    """A single difference between baseline and current state."""

    file_path: str
    change_type: ChangeType
    old_hash: str | None = None
    new_hash: str | None = None
    old_size: int | None = None
    new_size: int | None = None
    detail: str | None = None


@dataclass
class DiffReport:
    """Aggregated diff between a baseline and a scan."""

    findings: list[DiffFinding] = field(default_factory=list)
    total_modified: int = 0
    total_added: int = 0
    total_deleted: int = 0


def _metadata_changes(old: Any, new: HashResult) -> list[str]:
    reasons = []
    old_mode = getattr(old, "mode", None)
    if old_mode is not None and new.mode is not None and old_mode != new.mode:
        reasons.append(
            f"mode {stat.filemode(old_mode)} -> {stat.filemode(new.mode)}"
        )
    for attr in ("uid", "gid"):
        o, n = getattr(old, attr, None), getattr(new, attr)
        if o is not None and n is not None and o != n:
            reasons.append(f"{attr} {o} -> {n}")
    return reasons


def compute_diff(
    baseline_entries: Sequence[Any],
    current_scan: list[HashResult],
    failed: Iterable[HashResult] = (),
) -> DiffReport:
    """Return the changes between *baseline_entries* and *current_scan*.

    - **MODIFIED** — content hash, size, permissions or ownership changed
      (mtime alone is ignored: it changes on harmless `touch`/copies)
    - **ADDED**    — on disk but not in baseline
    - **DELETED**  — in baseline and truly absent from disk

    Files in *failed* exist but could not be read; they are never reported as
    DELETED. If their metadata changed they are reported as MODIFIED.
    """
    report = DiffReport()
    baseline_map = {e.file_path: e for e in baseline_entries}
    current_map = {hr.file_path: hr for hr in current_scan if hr.ok}
    failed_map = {hr.file_path: hr for hr in failed}

    for path, old in baseline_map.items():
        cur = current_map.get(path)

        if cur is None:
            bad = failed_map.get(path)
            if bad is not None:
                reasons = _metadata_changes(old, bad)
                if reasons:
                    report.findings.append(DiffFinding(
                        file_path=path, change_type=ChangeType.MODIFIED,
                        old_hash=old.sha256, old_size=old.size_bytes,
                        detail="Content unreadable; " + "; ".join(reasons),
                    ))
                    report.total_modified += 1
                continue

            report.findings.append(DiffFinding(
                file_path=path, change_type=ChangeType.DELETED,
                old_hash=old.sha256, old_size=old.size_bytes,
                detail="File no longer exists on disk.",
            ))
            report.total_deleted += 1
            continue

        reasons = []
        if cur.sha256 != old.sha256:
            reasons.append("content hash changed")
        if cur.size_bytes != old.size_bytes:
            reasons.append(f"size {old.size_bytes} -> {cur.size_bytes}")
        reasons += _metadata_changes(old, cur)

        if reasons:
            report.findings.append(DiffFinding(
                file_path=path, change_type=ChangeType.MODIFIED,
                old_hash=old.sha256, new_hash=cur.sha256,
                old_size=old.size_bytes, new_size=cur.size_bytes,
                detail="; ".join(reasons),
            ))
            report.total_modified += 1

    for path, cur in current_map.items():
        if path not in baseline_map:
            report.findings.append(DiffFinding(
                file_path=path, change_type=ChangeType.ADDED,
                new_hash=cur.sha256, new_size=cur.size_bytes,
                detail="New file detected.",
            ))
            report.total_added += 1

    return report
