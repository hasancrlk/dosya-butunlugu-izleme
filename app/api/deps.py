"""Shared API dependencies: authentication and path authorization."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    key = get_settings().API_KEY
    if not key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API key is not configured.")
    if not x_api_key or not hmac.compare_digest(x_api_key, key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key.")


def authorize_path(target_path: str) -> str:
    """Resolve *target_path* and ensure it lies inside FIM_ALLOWED_PATHS."""
    real = os.path.realpath(target_path)
    for allowed in get_settings().ALLOWED_PATHS:
        root = os.path.realpath(allowed)
        if os.path.commonpath([real, root]) == root:
            return real
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Target path is not in FIM_ALLOWED_PATHS.")
