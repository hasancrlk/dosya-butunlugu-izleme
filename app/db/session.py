"""Database engine and session factory."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models.base import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """Create or return the cached SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        kwargs: dict = {"echo": False}

        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            # In-memory SQLite needs StaticPool so every connection
            # shares the same database (required for tests & single-process use).
            if ":memory:" in settings.DATABASE_URL:
                kwargs["poolclass"] = StaticPool

        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            **kwargs,
        )
        # Enable WAL mode for file-backed SQLite
        if settings.DATABASE_URL.startswith("sqlite") and ":memory:" not in settings.DATABASE_URL:
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional DB session and close it afterwards."""
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    with get_session() as session:
        yield session


def init_db() -> None:
    """Create tables for SQLite (dev/tests). Other databases use `alembic upgrade head`."""
    if not get_settings().DATABASE_URL.startswith("sqlite"):
        return
    # Ensure every model is imported so Base.metadata is fully populated.
    import app.models.audit_log
    import app.models.baseline
    import app.models.scan  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def reset_engine() -> None:
    """Reset the cached engine (useful for tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
