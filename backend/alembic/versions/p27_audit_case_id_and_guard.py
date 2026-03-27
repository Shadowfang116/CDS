"""P27: Add case_id to audit_log and keep append-only (guard at ORM level)

Revision ID: p27_audit_case_id_and_guard
Revises: p25_ocr_review_workflow
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'p27_audit_case_id_and_guard'
down_revision = 'p25_ocr_review_workflow'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('audit_log', sa.Column('case_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('idx_audit_log_org_case_created', 'audit_log', ['org_id', 'case_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('idx_audit_log_org_case_created', table_name='audit_log')
    op.drop_column('audit_log', 'case_id')
