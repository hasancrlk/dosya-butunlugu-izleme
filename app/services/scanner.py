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
    failed: list[HashResult] = field(default_factory=list)  # seen but unreadable
    errors: list[str] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.file_records)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def scan_directory(target_path: str, follow_symlinks: bool | None = None) -> ScanResult:
    """Recursively walk *target_path* and hash every regular file and symlink.

    Errors are accumulated instead of raised. Unreadable files are kept in
    ``failed`` so the diff engine does not report them as deleted.
    """
    if follow_symlinks is None:
        follow_symlinks = get_settings().FOLLOW_SYMLINKS

    result = ScanResult(target_path=target_path)
    if not os.path.isdir(target_path):
        result.errors.append(f"Target path is not a directory: {target_path}")
        return result

    seen_real_dirs: set[str] = set()

    def _onerror(exc: OSError) -> None:
        result.errors.append(f"Cannot read directory {exc.filename}: {exc.strerror}")

    for dirpath, dirnames, filenames in os.walk(
        target_path, followlinks=follow_symlinks, onerror=_onerror
    ):
        real_dir = os.path.realpath(dirpath)
        if real_dir in seen_real_dirs:
            result.errors.append(f"Symlink loop detected, skipping: {dirpath} -> {real_dir}")
            dirnames.clear()
            continue
        seen_real_dirs.add(real_dir)

        candidates = list(filenames)
        if not follow_symlinks:
            # os.walk lists symlinked dirs in dirnames — record the links themselves
            candidates += [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]

        for name in candidates:
            hr = hash_file(
                os.path.join(dirpath, name),
                follow_symlinks=follow_symlinks,
                root=target_path,
            )
            if hr.ok:
                result.file_records.append(hr)
            elif hr.error and hr.error.startswith("Not a regular file"):
                continue  # sockets, FIFOs, devices: ignored by design
            else:
                result.failed.append(hr)
                result.errors.append(hr.error)  # type: ignore[arg-type]

    return result
