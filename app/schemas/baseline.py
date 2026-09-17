"""Schemas for baseline endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class BaselineRequest(BaseModel):
    """POST body for creating a baseline."""

    target_path: str = Field(..., description="Absolute path to directory to baseline.")
    follow_symlinks: bool | None = Field(
        None, description="Override global FOLLOW_SYMLINKS setting."
    )


class BaselineEntryOut(BaseModel):
    """Single file entry in a baseline."""

    file_path: str
    sha256: str
    size_bytes: int
    mtime: float
    mode: int | None = None
    uid: int | None = None
    gid: int | None = None

    model_config = {"from_attributes": True}


class BaselineResponse(BaseModel):
    """Response after baseline creation."""

    id: int
    target_path: str
    follow_symlinks: bool
    created_at: datetime
    file_count: int
    error_count: int
    status: str
    errors: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}
