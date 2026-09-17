"""Recursive directory scanner."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from app.config import get_settings
from app.services.hasher import HashResult, hash_file

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of scanning a directory tree."""

    target_path: str
    file_records: list[HashResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.file_records)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def scan_directory(
    target_path: str,
    follow_symlinks: bool | None = None,
) -> ScanResult:
    """Recursively walk *target_path*, hash every regular file.

    Symlink loops and permission errors are accumulated in
    ``ScanResult.errors`` instead of raising.
    """
    if follow_symlinks is None:
        follow_symlinks = get_settings().FOLLOW_SYMLINKS

    result = ScanResult(target_path=target_path)
    seen_real_dirs: set[str] = set()

    if not os.path.isdir(target_path):
        result.errors.append(f"Target path is not a directory: {target_path}")
        return result

    for dirpath, dirnames, filenames in os.walk(
        target_path, followlinks=follow_symlinks
    ):
        # Symlink-loop guard for directories
        real_dir = os.path.realpath(dirpath)
        if real_dir in seen_real_dirs:
            msg = f"Symlink loop detected, skipping: {dirpath} -> {real_dir}"
            logger.warning(msg)
            result.errors.append(msg)
            dirnames.clear()  # stop descending
            continue
        seen_real_dirs.add(real_dir)

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)

            # Skip non-regular files (sockets, devices, …)
            try:
                if not os.path.isfile(fpath):
                    continue
            except OSError as exc:
                msg = f"Cannot stat {fpath}: {exc}"
                logger.warning(msg)
                result.errors.append(msg)
                continue

            hr = hash_file(fpath)
            if hr.ok:
                result.file_records.append(hr)
            else:
                result.errors.append(hr.error)  # type: ignore[arg-type]

    return result
