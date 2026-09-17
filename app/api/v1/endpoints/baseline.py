"""POST /api/v1/baseline — create a new signed baseline snapshot."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import authorize_path
from app.db.session import get_db_session
from app.schemas.baseline import BaselineRequest, BaselineResponse
from app.services.workflow import create_baseline as create_baseline_wf

router = APIRouter()


@router.post("/baseline", response_model=BaselineResponse, status_code=201)
def create_baseline(body: BaselineRequest, db: Session = Depends(get_db_session)):
    target = authorize_path(body.target_path)
    session, result = create_baseline_wf(db, target, body.follow_symlinks)

    if result.file_count == 0 and result.error_count > 0:
        db.rollback()
        raise HTTPException(400, detail=f"No files could be read. Errors: {result.errors[:20]}")

    return BaselineResponse(
        id=session.id,
        target_path=session.target_path,
        follow_symlinks=session.follow_symlinks,
        created_at=session.created_at,
        file_count=session.file_count,
        error_count=session.error_count,
        status=session.status,
        errors=result.errors,
    )
