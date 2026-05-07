"""P33: Production pilot hardening

Revision ID: p33_production_pilot_hardening
Revises: p32_ocr_candidate_quality_fields
Create Date: 2026-04-06 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "p33_production_pilot_hardening"
down_revision = "p32_ocr_candidate_quality_fields"
branch_labels = None
depends_on = None


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _column_type(inspector, table_name: str, column_name: str):
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column["type"]
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "audit_log" in tables and "audit_logs" not in tables:
        op.rename_table("audit_log", "audit_logs")
        inspector = sa.inspect(bind)
        tables = set(inspector.get_table_names())

    user_columns = _columns(inspector, "users")
    if "is_active" not in user_columns:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "failed_login_attempts" not in user_columns:
        op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    if "locked_until" not in user_columns:
        op.add_column("users", sa.Column("locked_until", sa.DateTime(), nullable=True))
    if "last_login_at" not in user_columns:
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    if "must_change_password" not in user_columns:
        op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))

    case_columns = _columns(inspector, "cases")
    if "dossier_json" not in case_columns:
        op.add_column("cases", sa.Column("dossier_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    document_page_columns = _columns(inspector, "document_pages")
    if "corrected_text" not in document_page_columns:
        op.add_column("document_pages", sa.Column("corrected_text", sa.Text(), nullable=True))
    if "corrected_by_user_id" not in document_page_columns:
        op.add_column("document_pages", sa.Column("corrected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "corrected_at" not in document_page_columns:
        op.add_column("document_pages", sa.Column("corrected_at", sa.DateTime(), nullable=True))

    exception_columns = _columns(inspector, "exceptions")
    if "evidence_refs" not in exception_columns:
        op.add_column("exceptions", sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if "is_manual" not in exception_columns:
        op.add_column("exceptions", sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "source_document_id" not in exception_columns:
        op.add_column("exceptions", sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "source_page" not in exception_columns:
        op.add_column("exceptions", sa.Column("source_page", sa.Integer(), nullable=True))

    cp_columns = _columns(inspector, "cps")
    if "due_date" not in cp_columns:
        op.add_column("cps", sa.Column("due_date", sa.DateTime(), nullable=True))

    audit_columns = _columns(inspector, "audit_logs")
    if "actor_user_id" in audit_columns and "actor_id" not in audit_columns:
        op.alter_column("audit_logs", "actor_user_id", new_column_name="actor_id")
        audit_columns = _columns(sa.inspect(bind), "audit_logs")
    if "before_snapshot" in audit_columns and "before_json" not in audit_columns:
        op.alter_column("audit_logs", "before_snapshot", new_column_name="before_json")
        audit_columns = _columns(sa.inspect(bind), "audit_logs")
    if "metadata" in audit_columns and "after_json" not in audit_columns:
        op.alter_column("audit_logs", "metadata", new_column_name="after_json")
        audit_columns = _columns(sa.inspect(bind), "audit_logs")
    elif "after_snapshot" in audit_columns and "after_json" not in audit_columns:
        op.alter_column("audit_logs", "after_snapshot", new_column_name="after_json")
        audit_columns = _columns(sa.inspect(bind), "audit_logs")
    if "case_id" not in audit_columns:
        op.add_column("audit_logs", sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "before_json" not in audit_columns:
        op.add_column("audit_logs", sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if "after_json" not in audit_columns:
        op.add_column("audit_logs", sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if "ip_address" not in audit_columns:
        op.add_column("audit_logs", sa.Column("ip_address", sa.String(), nullable=True))
    audit_columns = _columns(sa.inspect(bind), "audit_logs")
    if "before_snapshot" in audit_columns and "before_json" in audit_columns:
        op.execute(
            sa.text(
                "UPDATE audit_logs SET before_json = COALESCE(before_json, before_snapshot) "
                "WHERE before_snapshot IS NOT NULL"
            )
        )
    if "after_snapshot" in audit_columns and "after_json" in audit_columns:
        op.execute(
            sa.text(
                "UPDATE audit_logs SET after_json = COALESCE(after_json, after_snapshot) "
                "WHERE after_snapshot IS NOT NULL"
            )
        )

    # Convert entity_id UUID column to text to support non-UUID entities in append-only logs.
    entity_id_type = _column_type(sa.inspect(bind), "audit_logs", "entity_id")
    if isinstance(entity_id_type, postgresql.UUID):
        op.alter_column(
            "audit_logs",
            "entity_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.String(),
            postgresql_using="entity_id::text",
            existing_nullable=True,
        )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "audit_logs", "idx_audit_logs_org_created"):
        op.create_index("idx_audit_logs_org_created", "audit_logs", ["org_id", "created_at"], unique=False)
    if not _has_index(inspector, "audit_logs", "idx_audit_logs_org_case_created"):
        op.create_index("idx_audit_logs_org_case_created", "audit_logs", ["org_id", "case_id", "created_at"], unique=False)


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "entity_id",
        existing_type=sa.String(),
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using="nullif(entity_id, '')::uuid",
        existing_nullable=True,
    )
    op.drop_index("idx_audit_logs_org_case_created", table_name="audit_logs")
    op.drop_index("idx_audit_logs_org_created", table_name="audit_logs")
    op.drop_column("audit_logs", "ip_address")
    op.drop_column("audit_logs", "before_json")
    op.drop_column("audit_logs", "case_id")
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("after_json", new_column_name="metadata")
        batch_op.alter_column("actor_id", new_column_name="actor_user_id")
    op.rename_table("audit_logs", "audit_log")

    op.drop_column("cps", "due_date")
    op.drop_column("exceptions", "source_page")
    op.drop_column("exceptions", "source_document_id")
    op.drop_column("exceptions", "is_manual")
    op.drop_column("exceptions", "evidence_refs")
    op.drop_column("document_pages", "corrected_at")
    op.drop_column("document_pages", "corrected_by_user_id")
    op.drop_column("document_pages", "corrected_text")
    op.drop_column("cases", "dossier_json")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "is_active")
