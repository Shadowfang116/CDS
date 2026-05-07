"""Add user authentication hardening columns.

Revision ID: 0002_user_auth_hardening
Revises: p33_production_pilot_hardening, p15_user_password_hash
Create Date: 2026-04-06 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0002_user_auth_hardening"
down_revision = ("p33_production_pilot_hardening", "p15_user_password_hash")
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _column(table_name: str, column_name: str) -> dict | None:
    inspector = inspect(op.get_bind())
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column
    return None


def upgrade() -> None:
    if not _has_column("users", "is_active"):
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.alter_column("users", "is_active", server_default=None)

    if not _has_column("users", "failed_login_attempts"):
        op.add_column(
            "users",
            sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("users", "failed_login_attempts", server_default=None)

    if not _has_column("users", "locked_until"):
        op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    else:
        locked_until = _column("users", "locked_until")
        if locked_until is not None and not getattr(locked_until["type"], "timezone", False):
            op.alter_column(
                "users",
                "locked_until",
                existing_type=locked_until["type"],
                type_=sa.DateTime(timezone=True),
                existing_nullable=True,
            )

    if not _has_column("users", "last_login_at"):
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    else:
        last_login_at = _column("users", "last_login_at")
        if last_login_at is not None and not getattr(last_login_at["type"], "timezone", False):
            op.alter_column(
                "users",
                "last_login_at",
                existing_type=last_login_at["type"],
                type_=sa.DateTime(timezone=True),
                existing_nullable=True,
            )

    if not _has_column("users", "must_change_password"):
        op.add_column(
            "users",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    if _has_column("users", "must_change_password"):
        op.drop_column("users", "must_change_password")

    if _has_column("users", "last_login_at"):
        op.drop_column("users", "last_login_at")

    if _has_column("users", "locked_until"):
        op.drop_column("users", "locked_until")

    if _has_column("users", "failed_login_attempts"):
        op.drop_column("users", "failed_login_attempts")

    if _has_column("users", "is_active"):
        op.drop_column("users", "is_active")
