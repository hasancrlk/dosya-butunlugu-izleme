"""Report generation — JSON and CSV export."""

from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import get_scan_session
from app.schemas.report import ReportFinding, ReportResponse


def build_report(db: Session, scan_id: int) -> ReportResponse | None:
    """Build a full report for the given *scan_id*."""
    scan = get_scan_session(db, scan_id)
    if scan is None:
        return None

    findings = [
        ReportFinding(
            file_path=f.file_path,
            change_type=f.change_type.value if hasattr(f.change_type, 'value') else f.change_type,
            old_hash=f.old_hash,
            new_hash=f.new_hash,
            old_size=f.old_size,
            new_size=f.new_size,
            detail=f.detail,
        )
        for f in scan.findings
    ]

    return ReportResponse(
        scan_id=scan.id,
        baseline_id=scan.baseline_id,
        baseline_path=scan.baseline.target_path,
        scanned_at=scan.created_at,
        status=scan.status,
        summary={
            "total_modified": scan.total_modified,
            "total_added": scan.total_added,
            "total_deleted": scan.total_deleted,
            "total_errors": scan.total_errors,
        },
        findings=findings,
    )


def report_to_csv(report: ReportResponse) -> str:
    """Serialize a ReportResponse to CSV text."""
    output = io.StringIO()
    fieldnames = [
        "file_path",
        "change_type",
        "old_hash",
        "new_hash",
        "old_size",
        "new_size",
        "detail",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for finding in report.findings:
        writer.writerow(finding.model_dump())
    return output.getvalue()


def report_to_json(report: ReportResponse) -> dict[str, Any]:
    """Serialize a ReportResponse to a plain dict (JSON-ready)."""
    return report.model_dump(mode="json")
