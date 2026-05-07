"""Normalize audit_log schema to canonical columns.

Revision ID: 0005_normalize_audit_log_schema
Revises: 0004_cp_waiver_tracking
Create Date: 2026-04-06 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_normalize_audit_log_schema"
down_revision = "0004_cp_waiver_tracking"
branch_labels = None
depends_on = None


def _table_name(inspector) -> str:
    tables = set(inspector.get_table_names())
    if "audit_log" in tables:
        return "audit_log"
    if "audit_logs" in tables:
        return "audit_logs"
    raise RuntimeError("Audit log table not found")


def _columns(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = _table_name(inspector)

    if table_name == "audit_logs":
        op.rename_table("audit_logs", "audit_log")
        table_name = "audit_log"
        inspector = sa.inspect(bind)

    columns = _columns(inspector, table_name)

    if "actor_user_id" in columns and "actor_id" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("actor_user_id", new_column_name="actor_id")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "metadata" in columns and "after_json" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("metadata", new_column_name="after_json")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "before_snapshot" in columns and "before_json" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("before_snapshot", new_column_name="before_json")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "after_snapshot" in columns and "after_json" in columns:
        op.execute(
            sa.text(
                "UPDATE audit_log SET after_json = COALESCE(after_json, after_snapshot) "
                "WHERE after_snapshot IS NOT NULL"
            )
        )

    case_id_column = columns.get("case_id")
    if case_id_column is not None and not isinstance(case_id_column["type"], postgresql.UUID):
        op.alter_column(
            table_name,
            "case_id",
            existing_type=case_id_column["type"],
            type_=postgresql.UUID(as_uuid=True),
            postgresql_using="NULLIF(case_id, '')::uuid",
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = _table_name(inspector)
    columns = _columns(inspector, table_name)

    case_id_column = columns.get("case_id")
    if case_id_column is not None and isinstance(case_id_column["type"], postgresql.UUID):
        op.alter_column(
            table_name,
            "case_id",
            existing_type=case_id_column["type"],
            type_=sa.String(),
            postgresql_using="case_id::text",
            existing_nullable=True,
        )

    columns = _columns(sa.inspect(bind), table_name)
    if "after_json" in columns and "metadata" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("after_json", new_column_name="metadata")

    columns = _columns(sa.inspect(bind), table_name)
    if "before_json" in columns and "before_snapshot" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("before_json", new_column_name="before_snapshot")

    columns = _columns(sa.inspect(bind), table_name)
    if "actor_id" in columns and "actor_user_id" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("actor_id", new_column_name="actor_user_id")
