"""P20: Add run_id to ocr_extraction_candidates for deterministic per-run tracking

Revision ID: p20_add_run_id
Revises: p16_add_hf_extractor_fields
Create Date: 2026-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p20_add_run_id'
down_revision = 'p16addhfextractorfields'
branch_labels = None
depends_on = None


def upgrade():
    # Add run_id column (nullable initially for backward compatibility)
    op.add_column('ocr_extraction_candidates', 
                  sa.Column('run_id', sa.String(32), nullable=True))
    
    # Add index for run_id queries
    op.create_index('ix_ocr_extraction_candidates_run_id', 
                    'ocr_extraction_candidates', 
                    ['run_id'])


def downgrade():
    # Drop index
    op.drop_index('ix_ocr_extraction_candidates_run_id', 
                  table_name='ocr_extraction_candidates')
    
    # Drop column
    op.drop_column('ocr_extraction_candidates', 'run_id')
