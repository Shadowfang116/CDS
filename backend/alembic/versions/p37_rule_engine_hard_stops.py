"""Persist rule-engine hard stops and decision signal.

Revision ID: p37_rule_engine_hard_stops
Revises: p36_case_assignment
Create Date: 2026-07-03 23:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "p37_rule_engine_hard_stops"
down_revision = "p36_case_assignment"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("exceptions", "is_hard_stop"):
        op.add_column(
            "exceptions",
            sa.Column("is_hard_stop", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if not _has_column("evaluation_runs", "decision"):
        op.add_column(
            "evaluation_runs",
            sa.Column("decision", sa.String(length=30), nullable=True),
        )


def downgrade() -> None:
    if _has_column("evaluation_runs", "decision"):
        op.drop_column("evaluation_runs", "decision")

    if _has_column("exceptions", "is_hard_stop"):
        op.drop_column("exceptions", "is_hard_stop")
