"""Normalize audit log schema for snapshots and case timeline queries.

Revision ID: 0003_audit_log_columns
Revises: 0002_user_auth_hardening
Create Date: 2026-04-06 16:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_audit_log_columns"
down_revision = "0002_user_auth_hardening"
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


def _indexes(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _is_string_type(column_type: object) -> bool:
    type_name = column_type.__class__.__name__.lower()
    return "char" in type_name or "string" in type_name or "text" in type_name


def _rename_index(old_name: str, new_name: str, existing_indexes: set[str]) -> None:
    if old_name in existing_indexes and new_name not in existing_indexes:
        op.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = _table_name(inspector)

    if table_name == "audit_logs":
        existing_indexes = _indexes(inspector, table_name)
        op.rename_table("audit_logs", "audit_log")
        _rename_index("idx_audit_logs_org_created", "idx_audit_log_org_created", existing_indexes)
        _rename_index("idx_audit_logs_org_case_created", "idx_audit_log_org_case_created", existing_indexes)
        inspector = sa.inspect(bind)
        table_name = "audit_log"

    columns = _columns(inspector, table_name)
    if "actor_id" in columns and "actor_user_id" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("actor_id", new_column_name="actor_user_id")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "after_json" in columns and "metadata" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("after_json", new_column_name="metadata")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "before_json" in columns and "before_snapshot" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("before_json", new_column_name="before_snapshot")
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "metadata" not in columns:
        op.add_column(table_name, sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "case_id" not in columns:
        op.add_column(table_name, sa.Column("case_id", sa.String(), nullable=True))
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)
    elif not _is_string_type(columns["case_id"]["type"]):
        op.alter_column(
            table_name,
            "case_id",
            existing_type=columns["case_id"]["type"],
            type_=sa.String(),
            postgresql_using="case_id::text",
            existing_nullable=True,
        )
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "ip_address" not in columns:
        op.add_column(table_name, sa.Column("ip_address", sa.String(length=45), nullable=True))
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "before_snapshot" not in columns:
        op.add_column(table_name, sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "after_snapshot" not in columns:
        op.add_column(table_name, sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    existing_indexes = _indexes(inspector, table_name)
    if "idx_audit_log_org_created" not in existing_indexes:
        op.create_index("idx_audit_log_org_created", table_name, ["org_id", "created_at"], unique=False)
    if "idx_audit_log_org_case_created" not in existing_indexes:
        op.create_index("idx_audit_log_org_case_created", table_name, ["org_id", "case_id", "created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = _table_name(inspector)
    columns = _columns(inspector, table_name)

    if "after_snapshot" in columns:
        op.drop_column(table_name, "after_snapshot")
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

    if "case_id" in columns and _is_string_type(columns["case_id"]["type"]):
        op.alter_column(
            table_name,
            "case_id",
            existing_type=columns["case_id"]["type"],
            type_=postgresql.UUID(as_uuid=True),
            postgresql_using="NULLIF(case_id, '')::uuid",
            existing_nullable=True,
        )
        inspector = sa.inspect(bind)
        columns = _columns(inspector, table_name)

    if "actor_user_id" in columns and "actor_id" not in columns:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("actor_user_id", new_column_name="actor_id")
        inspector = sa.inspect(bind)

    if table_name == "audit_log":
        existing_indexes = _indexes(inspector, table_name)
        op.rename_table("audit_log", "audit_logs")
        _rename_index("idx_audit_log_org_created", "idx_audit_logs_org_created", existing_indexes)
        _rename_index("idx_audit_log_org_case_created", "idx_audit_logs_org_case_created", existing_indexes)
