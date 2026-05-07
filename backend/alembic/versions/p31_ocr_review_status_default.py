"""P31: Restore server default for OCR extraction review_status

Revision ID: p31_ocr_review_status_default
Revises: p30_golden_case_evaluation
Create Date: 2026-03-29 00:00:00.000000
"""
from alembic import op


revision = "p31_ocr_review_status_default"
down_revision = "p30_golden_case_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ocr_extraction_candidates "
        "ALTER COLUMN review_status SET DEFAULT 'extracted'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ocr_extraction_candidates "
        "ALTER COLUMN review_status DROP DEFAULT"
    )
