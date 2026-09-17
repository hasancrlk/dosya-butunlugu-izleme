"""Streaming SHA-256 file hasher with graceful error handling."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class HashResult:
    """Result of hashing a single file."""

    file_path: str
    sha256: str | None = None
    size_bytes: int = 0
    mtime: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class HasherReport:
    """Aggregated report from hashing multiple files."""

    results: list[HashResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def hash_file(file_path: str, chunk_size: int | None = None) -> HashResult:
    """Compute SHA-256 of *file_path* using streaming 64 KB chunks.

    Handles:
    - PermissionError  → logged, returned as error in HashResult
    - Symlink loops    → detected via os.path.realpath comparison
    - OSError variants → caught and reported gracefully
    """
    if chunk_size is None:
        chunk_size = get_settings().HASH_CHUNK_SIZE

    try:
        # Symlink-loop guard: resolve and compare
        real_path = os.path.realpath(file_path)
        if os.path.islink(file_path) and not os.path.exists(real_path):
            msg = f"Broken or circular symlink: {file_path} -> {real_path}"
            logger.warning(msg)
            return HashResult(file_path=file_path, error=msg)

        stat = os.stat(real_path)
        sha = hashlib.sha256()

        with open(real_path, "rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                sha.update(chunk)

        return HashResult(
            file_path=file_path,
            sha256=sha.hexdigest(),
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
        )

    except PermissionError:
        msg = f"Permission denied: {file_path}"
        logger.warning(msg)
        return HashResult(file_path=file_path, error=msg)

    except OSError as exc:
        msg = f"OS error on {file_path}: {exc}"
        logger.warning(msg)
        return HashResult(file_path=file_path, error=msg)
