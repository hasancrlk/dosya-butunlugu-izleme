"""Tests for the recursive directory scanner."""

from __future__ import annotations

from pathlib import Path

from app.services.scanner import scan_directory


def test_scan_counts_files(sample_dir: Path) -> None:
    result = scan_directory(str(sample_dir))
    # file_a.txt, file_b.bin, subdir/nested.log
    assert result.file_count == 3
    assert result.error_count == 0


def test_scan_returns_hashes(sample_dir: Path) -> None:
    result = scan_directory(str(sample_dir))
    for rec in result.file_records:
        assert rec.sha256 is not None
        assert len(rec.sha256) == 64  # hex SHA-256


def test_scan_nonexistent_dir() -> None:
    result = scan_directory("/nonexistent/dir/xyz")
    assert result.file_count == 0
    assert result.error_count > 0


def test_scan_empty_dir(tmp_path: Path) -> None:
    result = scan_directory(str(tmp_path))
    assert result.file_count == 0
    assert result.error_count == 0
