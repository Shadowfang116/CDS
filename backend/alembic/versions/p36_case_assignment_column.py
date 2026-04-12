"""Add case assignment column.

Revision ID: p36_case_assignment
Revises: p35_merge_heads
Create Date: 2026-04-12 10:35:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "p36_case_assignment"
down_revision = "p35_merge_heads"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_foreign_key(table_name: str, constrained_columns: list[str], referred_table: str) -> bool:
    inspector = inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("referred_table") != referred_table:
            continue
        if foreign_key.get("constrained_columns") == constrained_columns:
            return True
    return False


def upgrade() -> None:
    if not _has_column("cases", "assigned_to_user_id"):
        op.add_column("cases", sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True))

    if not _has_foreign_key("cases", ["assigned_to_user_id"], "users"):
        op.create_foreign_key(
            "cases_assigned_to_user_id_fkey",
            "cases",
            "users",
            ["assigned_to_user_id"],
            ["id"],
        )


def downgrade() -> None:
    if _has_foreign_key("cases", ["assigned_to_user_id"], "users"):
        op.drop_constraint("cases_assigned_to_user_id_fkey", "cases", type_="foreignkey")

    if _has_column("cases", "assigned_to_user_id"):
        op.drop_column("cases", "assigned_to_user_id")
