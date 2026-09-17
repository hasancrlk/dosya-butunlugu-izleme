"""GET /api/v1/audit/verify — verify the audit hash chain."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repository import verify_audit_chain
from app.db.session import get_db_session

router = APIRouter()


@router.get("/audit/verify")
def verify_audit(db: Session = Depends(get_db_session)):
    ok, broken_id = verify_audit_chain(db)
    return {"intact": ok, "first_broken_id": broken_id}
