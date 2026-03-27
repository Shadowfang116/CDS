"""P28: Add waiver_category to exceptions

Revision ID: p28_exception_waiver_category
Revises: p27_audit_case_id_and_guard
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'p28_exception_waiver_category'
down_revision = 'p27_audit_case_id_and_guard'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('exceptions', sa.Column('waiver_category', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('exceptions', 'waiver_category')
