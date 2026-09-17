"""Integrity hardening: signed baselines, file metadata, hash-chained audit log.

Revision ID: 002
Revises: 001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("baseline_sessions") as t:
        t.add_column(sa.Column("follow_symlinks", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("signature", sa.String(64), nullable=True))

    with op.batch_alter_table("baseline_entries") as t:
        t.alter_column("size_bytes", type_=sa.BigInteger())
        t.add_column(sa.Column("mode", sa.Integer(), nullable=True))
        t.add_column(sa.Column("uid", sa.Integer(), nullable=True))
        t.add_column(sa.Column("gid", sa.Integer(), nullable=True))

    with op.batch_alter_table("scan_findings") as t:
        t.alter_column("old_size", type_=sa.BigInteger())
        t.alter_column("new_size", type_=sa.BigInteger())

    # Pre-existing audit rows cannot be chained retroactively; start a fresh chain.
    op.execute("DELETE FROM audit_log")
    with op.batch_alter_table("audit_log") as t:
        t.add_column(sa.Column("prev_hash", sa.String(64), nullable=False, server_default=""))
        t.add_column(sa.Column("entry_hash", sa.String(64), nullable=False, server_default=""))

    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'audit_log is append-only'; END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER audit_log_no_modify BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
        """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_log_no_modify ON audit_log;")
        op.execute("DROP FUNCTION IF EXISTS audit_log_immutable();")
    with op.batch_alter_table("audit_log") as t:
        t.drop_column("entry_hash")
        t.drop_column("prev_hash")
    with op.batch_alter_table("baseline_entries") as t:
        t.drop_column("gid")
        t.drop_column("uid")
        t.drop_column("mode")
    with op.batch_alter_table("baseline_sessions") as t:
        t.drop_column("signature")
        t.drop_column("follow_symlinks")
