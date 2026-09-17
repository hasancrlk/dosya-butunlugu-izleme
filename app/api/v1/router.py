"""Aggregate v1 API router (all routes require X-API-Key)."""

from fastapi import APIRouter, Depends

from app.api.deps import require_api_key
from app.api.v1.endpoints import audit, baseline, reports, scan

v1_router = APIRouter(prefix="/api/v1", tags=["v1"], dependencies=[Depends(require_api_key)])

v1_router.include_router(baseline.router)
v1_router.include_router(scan.router)
v1_router.include_router(reports.router)
v1_router.include_router(audit.router)
