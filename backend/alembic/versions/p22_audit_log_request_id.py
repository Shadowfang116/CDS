"""P22: Add request_id to audit_log for correlation (Phase 3 structured logging)

Revision ID: p22_audit_request_id
Revises: p20_add_run_id
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = 'p22_audit_request_id'
down_revision = 'p20_add_run_id'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'audit_log',
        sa.Column('request_id', sa.String(), nullable=True),
    )
    op.create_index('ix_audit_log_request_id', 'audit_log', ['request_id'], unique=False)


def downgrade():
    op.drop_index('ix_audit_log_request_id', table_name='audit_log')
    op.drop_column('audit_log', 'request_id')
