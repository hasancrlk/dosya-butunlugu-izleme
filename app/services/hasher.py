"""Streaming SHA-256 file hasher with symlink-safe metadata collection."""

from __future__ import annotations

import hashlib
import logging
import os
import stat
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class HashResult:
    """Result of hashing a single file."""

    file_path: str
    sha256: str | None = None
    size_bytes: int = 0
    mtime: float = 0.0
    mode: int | None = None
    uid: int | None = None
    gid: int | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _is_within(path: str, root: str) -> bool:
    root = os.path.realpath(root)
    return os.path.commonpath([os.path.realpath(path), root]) == root


def hash_file(
    file_path: str,
    chunk_size: int | None = None,
    follow_symlinks: bool = False,
    root: str | None = None,
) -> HashResult:
    """Hash *file_path* and collect mode/owner metadata.

    - Symlinks are NOT followed by default: the link target string is hashed,
      so re-pointing a link is detected and nothing outside the tree is read.
    - When following, targets that escape *root* are rejected.
    - Metadata (mode/uid/gid) is returned even when content is unreadable.
    """
    chunk_size = chunk_size or get_settings().HASH_CHUNK_SIZE
    result = HashResult(file_path=file_path)

    try:
        st = os.lstat(file_path)

        if stat.S_ISLNK(st.st_mode):
            if not follow_symlinks:
                target = os.readlink(file_path)
                result.sha256 = hashlib.sha256(f"symlink:{target}".encode()).hexdigest()
                result.size_bytes = len(target)
                result.mtime, result.mode = st.st_mtime, st.st_mode
                result.uid, result.gid = st.st_uid, st.st_gid
                return result
            if root and not _is_within(file_path, root):
                result.error = f"Symlink escapes target directory: {file_path}"
                logger.warning(result.error)
                return result
            st = os.stat(file_path)  # raises on broken/looping links

        result.mtime, result.mode = st.st_mtime, st.st_mode
        result.uid, result.gid, result.size_bytes = st.st_uid, st.st_gid, st.st_size

        if not stat.S_ISREG(st.st_mode):
            result.error = f"Not a regular file: {file_path}"
            return result

        sha = hashlib.sha256()
        with open(file_path, "rb") as fh:
            while chunk := fh.read(chunk_size):
                sha.update(chunk)
        result.sha256 = sha.hexdigest()
        return result

    except PermissionError:
        result.error = f"Permission denied: {file_path}"
    except OSError as exc:
        result.error = f"OS error on {file_path}: {exc}"
    logger.warning(result.error)
    return result
