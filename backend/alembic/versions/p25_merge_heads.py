"""Merge p23_exports_phase8 and p24_ocr_override into single head

Revision ID: p25_merge_heads
Revises: p23_exports_phase8, p24_ocr_override
Create Date: 2026-03-20

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'p25_merge_heads'
down_revision = ('p23_exports_phase8', 'p24_ocr_override')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
