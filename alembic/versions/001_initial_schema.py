"""Initial schema.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── baseline_sessions ──────────────────────────────────────
    op.create_table(
        "baseline_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("file_count", sa.Integer(), server_default="0"),
        sa.Column("error_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="completed"),
    )

    # ── baseline_entries ───────────────────────────────────────
    op.create_table(
        "baseline_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("baseline_sessions.id"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mtime", sa.Float(), nullable=False),
    )
    op.create_index("ix_baseline_entries_session", "baseline_entries", ["session_id"])

    # ── scan_sessions ─────────────────────────────────────────
    op.create_table(
        "scan_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("baseline_id", sa.Integer(), sa.ForeignKey("baseline_sessions.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("total_modified", sa.Integer(), server_default="0"),
        sa.Column("total_added", sa.Integer(), server_default="0"),
        sa.Column("total_deleted", sa.Integer(), server_default="0"),
        sa.Column("total_errors", sa.Integer(), server_default="0"),
    )

    # ── scan_findings ─────────────────────────────────────────
    op.create_table(
        "scan_findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("scan_sessions.id"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "change_type",
            sa.Enum("MODIFIED", "ADDED", "DELETED", name="changetype"),
            nullable=False,
        ),
        sa.Column("old_hash", sa.String(64)),
        sa.Column("new_hash", sa.String(64)),
        sa.Column("old_size", sa.Integer()),
        sa.Column("new_size", sa.Integer()),
        sa.Column("detail", sa.Text()),
    )
    op.create_index("ix_scan_findings_session", "scan_findings", ["session_id"])

    # ── audit_log (append-only) ───────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(100), server_default="system"),
        sa.Column("detail", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("ix_scan_findings_session", table_name="scan_findings")
    op.drop_table("scan_findings")
    op.drop_table("scan_sessions")
    op.drop_index("ix_baseline_entries_session", table_name="baseline_entries")
    op.drop_table("baseline_entries")
    op.drop_table("baseline_sessions")
