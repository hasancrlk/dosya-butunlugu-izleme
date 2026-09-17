"""Tests for the streaming SHA-256 hasher."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from app.services.hasher import hash_file


def test_hash_known_content(tmp_path: Path) -> None:
    """Hash of known bytes must match hashlib reference."""
    content = b"FIM-Sentinel test payload"
    f = tmp_path / "known.bin"
    f.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    result = hash_file(str(f))

    assert result.ok
    assert result.sha256 == expected
    assert result.size_bytes == len(content)


def test_hash_empty_file(tmp_path: Path) -> None:
    """Empty file should hash to SHA-256 of empty bytes."""
    f = tmp_path / "empty"
    f.write_bytes(b"")

    expected = hashlib.sha256(b"").hexdigest()
    result = hash_file(str(f))

    assert result.ok
    assert result.sha256 == expected
    assert result.size_bytes == 0


def test_hash_large_file_streaming(tmp_path: Path) -> None:
    """File larger than one chunk must still produce correct hash."""
    chunk_size = 1024
    data = os.urandom(chunk_size * 5)  # 5 chunks
    f = tmp_path / "large.bin"
    f.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    result = hash_file(str(f), chunk_size=chunk_size)

    assert result.ok
    assert result.sha256 == expected


def test_hash_permission_denied(tmp_path: Path) -> None:
    """PermissionError must be caught, not raised."""
    f = tmp_path / "secret"
    f.write_text("secret")

    # Skip on Windows where chmod doesn't reliably deny read
    if os.name == "nt" or os.geteuid() == 0:
        pytest.skip("chmod does not deny read on Windows or for root")

    f.chmod(0o000)
    try:
        result = hash_file(str(f))
        assert not result.ok
        assert "Permission denied" in (result.error or "")
    finally:
        f.chmod(0o644)


def test_hash_nonexistent_file() -> None:
    """Missing file must return an error, not raise."""
    result = hash_file("/nonexistent/path/xyz.bin")
    assert not result.ok
    assert result.error is not None


def test_symlink_not_followed_hashes_link_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = tmp_path / "link"
    link.symlink_to(outside)

    result = hash_file(str(link), follow_symlinks=False)
    assert result.ok
    assert result.sha256 == hashlib.sha256(f"symlink:{outside}".encode()).hexdigest()


def test_followed_symlink_escaping_root_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "outside.txt").write_text("secret")
    link = root / "link"
    link.symlink_to(tmp_path / "outside.txt")

    result = hash_file(str(link), follow_symlinks=True, root=str(root))
    assert not result.ok
    assert "escapes" in (result.error or "")


def test_hash_collects_mode(tmp_path: Path) -> None:
    f = tmp_path / "x"
    f.write_text("x")
    f.chmod(0o640)
    assert hash_file(str(f)).mode & 0o777 == 0o640
