"""p15_ocr_extraction_manual_override

Revision ID: p15ocrextractionmanualoverride
Revises: 5ec98b0fbc01
Create Date: 2025-01-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p15ocrextractionmanualoverride'
down_revision: Union[str, None] = '5ec98b0fbc01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add manual override fields to OCR extraction candidates
    op.add_column('ocr_extraction_candidates', sa.Column('overridden_by_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('ocr_extraction_candidates', sa.Column('overridden_at', sa.DateTime(), nullable=True))
    op.add_column('ocr_extraction_candidates', sa.Column('override_note', sa.Text(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_ocr_extraction_overridden_by_user',
        'ocr_extraction_candidates',
        'users',
        ['overridden_by_user_id'],
        ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_ocr_extraction_overridden_by_user', 'ocr_extraction_candidates', type_='foreignkey')
    op.drop_column('ocr_extraction_candidates', 'override_note')
    op.drop_column('ocr_extraction_candidates', 'overridden_at')
    op.drop_column('ocr_extraction_candidates', 'overridden_by_user_id')

