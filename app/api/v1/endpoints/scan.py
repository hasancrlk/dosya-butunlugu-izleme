"""POST /api/v1/scan — run an integrity scan against a baseline."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.db.repository import (
    get_baseline_session,
    create_scan_session,
    add_scan_findings,
)
from app.schemas.scan import ScanRequest, ScanResponse, ScanFindingOut
from app.services.scanner import scan_directory
from app.services.diff_engine import compute_diff

router = APIRouter()


@router.post("/scan", response_model=ScanResponse, status_code=201)
def run_scan(
    body: ScanRequest,
    db: Session = Depends(get_db_session),
):
    """Re-scan the baseline target directory and report changes."""
    baseline = get_baseline_session(db, body.baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found.")

    # Re-scan the same directory
    scan_result = scan_directory(baseline.target_path)

    # Diff
    diff = compute_diff(baseline.entries, scan_result.file_records)

    # Persist scan session
    scan_obj = create_scan_session(
        db,
        baseline_id=baseline.id,
        total_modified=diff.total_modified,
        total_added=diff.total_added,
        total_deleted=diff.total_deleted,
        total_errors=scan_result.error_count,
    )

    # Persist findings
    finding_dicts = [
        {
            "file_path": f.file_path,
            "change_type": f.change_type,
            "old_hash": f.old_hash,
            "new_hash": f.new_hash,
            "old_size": f.old_size,
            "new_size": f.new_size,
            "detail": f.detail,
        }
        for f in diff.findings
    ]
    add_scan_findings(db, scan_obj.id, finding_dicts)

    findings_out = [
        ScanFindingOut(
            file_path=f.file_path,
            change_type=f.change_type.value,
            old_hash=f.old_hash,
            new_hash=f.new_hash,
            old_size=f.old_size,
            new_size=f.new_size,
            detail=f.detail,
        )
        for f in diff.findings
    ]

    return ScanResponse(
        id=scan_obj.id,
        baseline_id=baseline.id,
        created_at=scan_obj.created_at,
        status=scan_obj.status,
        total_modified=diff.total_modified,
        total_added=diff.total_added,
        total_deleted=diff.total_deleted,
        total_errors=scan_result.error_count,
        findings=findings_out,
        errors=scan_result.errors,
    )
