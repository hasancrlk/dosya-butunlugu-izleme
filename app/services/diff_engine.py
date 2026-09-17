"""Diff engine — compare baseline entries with a fresh directory scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.models.baseline import BaselineEntry
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


def compute_diff(
    baseline_entries: Sequence[BaselineEntry],
    current_scan: list[HashResult],
) -> DiffReport:
    """Return the set of changes between *baseline_entries* and *current_scan*.

    Change types:
      - **MODIFIED** — same path, different hash or size or mtime
      - **ADDED**    — path exists on disk but not in baseline
      - **DELETED**  — path in baseline but missing from disk
    """
    report = DiffReport()

    baseline_map: dict[str, BaselineEntry] = {
        entry.file_path: entry for entry in baseline_entries
    }
    current_map: dict[str, HashResult] = {
        hr.file_path: hr for hr in current_scan if hr.ok
    }

    # Detect MODIFIED and DELETED
    for path, bl_entry in baseline_map.items():
        cur = current_map.get(path)
        if cur is None:
            report.findings.append(
                DiffFinding(
                    file_path=path,
                    change_type=ChangeType.DELETED,
                    old_hash=bl_entry.sha256,
                    old_size=bl_entry.size_bytes,
                    detail="File no longer exists on disk.",
                )
            )
            report.total_deleted += 1
        elif cur.sha256 != bl_entry.sha256:
            report.findings.append(
                DiffFinding(
                    file_path=path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=bl_entry.sha256,
                    new_hash=cur.sha256,
                    old_size=bl_entry.size_bytes,
                    new_size=cur.size_bytes,
                    detail="Hash mismatch detected.",
                )
            )
            report.total_modified += 1

    # Detect ADDED (new files not in baseline)
    for path, cur in current_map.items():
        if path not in baseline_map:
            report.findings.append(
                DiffFinding(
                    file_path=path,
                    change_type=ChangeType.ADDED,
                    new_hash=cur.sha256,
                    new_size=cur.size_bytes,
                    detail="New file detected.",
                )
            )
            report.total_added += 1

    return report
