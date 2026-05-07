"""P32: Add quality score and quality level to OCR extraction candidates

Revision ID: p32_ocr_candidate_quality_fields
Revises: p31_ocr_review_status_default
Create Date: 2026-03-29 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "p32_ocr_candidate_quality_fields"
down_revision = "p31_ocr_review_status_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ocr_extraction_candidates", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("ocr_extraction_candidates", sa.Column("quality_level", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ocr_extraction_candidates", "quality_level")
    op.drop_column("ocr_extraction_candidates", "quality_score")
