"""p10_ocr_extraction_quality

Revision ID: p10ocrextractionquality
Revises: p10dossierhistory
Create Date: 2025-01-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p10ocrextractionquality'
down_revision: Union[str, None] = 'p10dossierhistory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = '3f02d0d700a5'


def upgrade() -> None:
    # Add quality fields to OCR extraction candidates
    op.add_column('ocr_extraction_candidates', sa.Column('quality_level_at_create', sa.String(), nullable=True))
    op.add_column('ocr_extraction_candidates', sa.Column('is_low_quality', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('ocr_extraction_candidates', sa.Column('warning_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ocr_extraction_candidates', 'warning_reason')
    op.drop_column('ocr_extraction_candidates', 'is_low_quality')
    op.drop_column('ocr_extraction_candidates', 'quality_level_at_create')

