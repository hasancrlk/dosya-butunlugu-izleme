"""GET /api/v1/reports/{scan_id} — retrieve scan report."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.report_service import build_report, report_to_csv, report_to_json

router = APIRouter()


@router.get("/reports/{scan_id}")
def get_report(
    scan_id: int,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db_session),
):
    """Return the report for a completed scan.

    Query params:
        format: 'json' (default) | 'csv'
    """
    report = build_report(db, scan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    if format == "csv":
        csv_text = report_to_csv(report)
        return StreamingResponse(
            iter([csv_text]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=scan_{scan_id}_report.csv"
            },
        )

    return report_to_json(report)
