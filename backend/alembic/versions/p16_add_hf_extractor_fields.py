"""add_hf_extractor_fields

Revision ID: p16addhfextractorfields
Revises: p15ocrextractionmanualoverride
Create Date: 2025-01-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p16addhfextractorfields'
down_revision: Union[str, None] = 'p15ocrextractionmanualoverride'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add extraction_method column (for tracking which extractor created this candidate)
    op.add_column('ocr_extraction_candidates', sa.Column('extraction_method', sa.String(), nullable=True))
    
    # Add evidence_json column (JSONB for storing structured evidence from AI extractors)
    op.add_column('ocr_extraction_candidates', sa.Column('evidence_json', postgresql.JSONB, nullable=True))
    
    # Create index on extraction_method for filtering
    op.create_index('idx_ocr_extractions_extraction_method', 'ocr_extraction_candidates', ['extraction_method'])


def downgrade() -> None:
    op.drop_index('idx_ocr_extractions_extraction_method', table_name='ocr_extraction_candidates')
    op.drop_column('ocr_extraction_candidates', 'evidence_json')
    op.drop_column('ocr_extraction_candidates', 'extraction_method')

