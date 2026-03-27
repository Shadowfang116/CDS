"""P25: Add review_status and needs_review to OCRExtractionCandidate

Revision ID: p25_ocr_review_workflow
Revises: p21_query_j_output
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'p25_ocr_review_workflow'
down_revision = 'p26_exception_closing_evidence'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ocr_extraction_candidates', sa.Column('review_status', sa.String(), nullable=False, server_default='extracted'))
    op.add_column('ocr_extraction_candidates', sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('ocr_extraction_candidates', sa.Column('verified_by_user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('ocr_extraction_candidates', sa.Column('verified_at', sa.DateTime(), nullable=True))
    # Remove server defaults to avoid defaulting on future explicit inserts
    op.alter_column('ocr_extraction_candidates', 'review_status', server_default=None)
    op.alter_column('ocr_extraction_candidates', 'needs_review', server_default=None)


def downgrade():
    op.drop_column('ocr_extraction_candidates', 'verified_at')
    op.drop_column('ocr_extraction_candidates', 'verified_by_user_id')
    op.drop_column('ocr_extraction_candidates', 'needs_review')
    op.drop_column('ocr_extraction_candidates', 'review_status')

