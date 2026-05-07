"""Add CP waiver tracking columns.

Revision ID: 0004_cp_waiver_tracking
Revises: 0003_audit_log_columns
Create Date: 2026-04-06 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0004_cp_waiver_tracking"
down_revision = "0003_audit_log_columns"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("cps", "waiver_reason"):
        op.add_column("cps", sa.Column("waiver_reason", sa.Text(), nullable=True))
    if not _has_column("cps", "waived_at"):
        op.add_column("cps", sa.Column("waived_at", sa.DateTime(), nullable=True))
    if not _has_column("cps", "waived_by_user_id"):
        op.add_column(
            "cps",
            sa.Column("waived_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("cps", "waived_by_user_id"):
        op.drop_column("cps", "waived_by_user_id")
    if _has_column("cps", "waived_at"):
        op.drop_column("cps", "waived_at")
    if _has_column("cps", "waiver_reason"):
        op.drop_column("cps", "waiver_reason")
