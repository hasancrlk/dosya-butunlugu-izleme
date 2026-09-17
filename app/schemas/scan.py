"""Schemas for scan endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """POST body for running a scan."""

    baseline_id: int = Field(..., description="ID of the baseline to compare against.")


class ScanFindingOut(BaseModel):
    """A single change finding."""

    file_path: str
    change_type: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    old_size: Optional[int] = None
    new_size: Optional[int] = None
    detail: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    """Response after a scan completes."""

    id: int
    baseline_id: int
    created_at: datetime
    status: str
    total_modified: int
    total_added: int
    total_deleted: int
    total_errors: int
    findings: list[ScanFindingOut] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}
