"""POST /api/v1/scan — run an integrity scan against a baseline."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.scan import ScanFindingOut, ScanRequest, ScanResponse
from app.services.workflow import BaselineNotFoundError, BaselineTamperedError, run_scan

router = APIRouter()


@router.post("/scan", response_model=ScanResponse, status_code=201)
def scan(body: ScanRequest, db: Session = Depends(get_db_session)):
    try:
        scan_obj, diff, result = run_scan(db, body.baseline_id)
    except BaselineNotFoundError:
        raise HTTPException(404, detail="Baseline not found.")
    except BaselineTamperedError:
        raise HTTPException(409, detail="Baseline signature invalid — baseline may be tampered.")

    return ScanResponse(
        id=scan_obj.id,
        baseline_id=scan_obj.baseline_id,
        created_at=scan_obj.created_at,
        status=scan_obj.status,
        total_modified=diff.total_modified,
        total_added=diff.total_added,
        total_deleted=diff.total_deleted,
        total_errors=result.error_count,
        findings=[
            ScanFindingOut(**{**f.__dict__, "change_type": f.change_type.value})
            for f in diff.findings
        ],
        errors=result.errors,
    )
