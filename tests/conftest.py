"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Override DB URL BEFORE any app import
os.environ["FIM_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["FIM_API_KEY"] = "test-api-key"
os.environ["FIM_HMAC_KEY"] = "test-hmac-key-that-is-long-enough-123"

from app.config import get_settings
from app.db.session import reset_engine
from app.models.base import Base


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    get_settings.cache_clear()
    reset_engine()
    yield
    get_settings.cache_clear()
    reset_engine()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Yield a fresh in-memory SQLite session with tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def sample_dir(tmp_path: Path) -> Path:
    """Create a small directory tree with known files for testing."""
    (tmp_path / "file_a.txt").write_text("Hello World\n")
    (tmp_path / "file_b.bin").write_bytes(b"\x00\x01\x02\x03")

    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.log").write_text("log entry 1\n")

    return tmp_path


@pytest.fixture()
def sample_dir_modified(sample_dir: Path) -> Path:
    """Modify the sample directory to simulate changes."""
    # Modify an existing file
    (sample_dir / "file_a.txt").write_text("Modified Content\n")

    # Add a new file
    (sample_dir / "new_file.dat").write_bytes(b"new data")

    # Delete a file
    (sample_dir / "file_b.bin").unlink()

    return sample_dir
