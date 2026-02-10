"""P23: Export model Phase 8 - status, error fields, request_id, timestamps

Revision ID: p23_exports_phase8
Revises: p22_audit_request_id
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = "p23_exports_phase8"
down_revision = "p22_audit_request_id"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exports", sa.Column("status", sa.String(), nullable=True))
    op.add_column("exports", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("exports", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.add_column("exports", sa.Column("error_code", sa.String(), nullable=True))
    op.add_column("exports", sa.Column("error_message", sa.String(1000), nullable=True))
    op.add_column("exports", sa.Column("request_id", sa.String(), nullable=True))
    op.add_column("exports", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # Backfill: existing rows are completed exports
    op.execute(
        "UPDATE exports SET status = 'succeeded', updated_at = created_at WHERE status IS NULL"
    )

    op.alter_column(
        "exports",
        "status",
        existing_type=sa.String(),
        nullable=False,
        server_default=sa.text("'succeeded'"),
    )
    op.alter_column(
        "exports",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.func.now(),
    )

    # Allow minio_key to be null for pending/failed exports
    op.alter_column(
        "exports",
        "minio_key",
        existing_type=sa.String(),
        nullable=True,
    )

    op.create_index(
        "idx_exports_org_case_type_status",
        "exports",
        ["org_id", "case_id", "export_type", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index("idx_exports_org_case_type_status", table_name="exports")
    op.alter_column(
        "exports",
        "minio_key",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("exports", "updated_at")
    op.drop_column("exports", "request_id")
    op.drop_column("exports", "error_message")
    op.drop_column("exports", "error_code")
    op.drop_column("exports", "finished_at")
    op.drop_column("exports", "started_at")
    op.drop_column("exports", "status")
