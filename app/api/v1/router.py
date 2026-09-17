"""Aggregate v1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import baseline, reports, scan

v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

v1_router.include_router(baseline.router)
v1_router.include_router(scan.router)
v1_router.include_router(reports.router)
