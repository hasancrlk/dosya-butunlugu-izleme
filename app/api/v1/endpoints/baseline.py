"""POST /api/v1/baseline — create a new baseline snapshot."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.db.repository import create_baseline_session, add_baseline_entries
from app.schemas.baseline import BaselineRequest, BaselineResponse
from app.services.scanner import scan_directory

router = APIRouter()


@router.post("/baseline", response_model=BaselineResponse, status_code=201)
def create_baseline(
    body: BaselineRequest,
    db: Session = Depends(get_db_session),
):
    """Scan a directory and persist the baseline snapshot."""
    scan_result = scan_directory(
        body.target_path,
        follow_symlinks=body.follow_symlinks,
    )

    if scan_result.file_count == 0 and scan_result.error_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No files could be read. Errors: {scan_result.errors}",
        )

    session_obj = create_baseline_session(
        db,
        target_path=body.target_path,
        file_count=scan_result.file_count,
        error_count=scan_result.error_count,
    )

    entries = [
        {
            "file_path": r.file_path,
            "sha256": r.sha256,
            "size_bytes": r.size_bytes,
            "mtime": r.mtime,
        }
        for r in scan_result.file_records
    ]
    add_baseline_entries(db, session_obj.id, entries)

    return BaselineResponse(
        id=session_obj.id,
        target_path=session_obj.target_path,
        created_at=session_obj.created_at,
        file_count=session_obj.file_count,
        error_count=session_obj.error_count,
        status=session_obj.status,
        errors=scan_result.errors,
    )
