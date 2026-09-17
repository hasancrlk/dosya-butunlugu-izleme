"""Schemas for report endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportFinding(BaseModel):
    """Finding entry inside a report."""

    file_path: str
    change_type: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    old_size: Optional[int] = None
    new_size: Optional[int] = None
    detail: Optional[str] = None

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
