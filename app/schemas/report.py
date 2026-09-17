"""Schemas for report endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReportFinding(BaseModel):
    """Finding entry inside a report."""

    file_path: str
    change_type: str
    old_hash: str | None = None
    new_hash: str | None = None
    old_size: int | None = None
    new_size: int | None = None
    detail: str | None = None

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    """Full report for a scan."""

    scan_id: int
    baseline_id: int
    baseline_path: str
    scanned_at: datetime
    status: str
    summary: dict = Field(default_factory=dict)
    findings: list[ReportFinding] = Field(default_factory=list)

    model_config = {"from_attributes": True}
