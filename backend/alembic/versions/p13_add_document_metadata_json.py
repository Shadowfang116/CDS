"""p13_add_document_metadata_json

Revision ID: p13documentmetadata
Revises: p10ocrextractionquality
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p13documentmetadata'
down_revision: Union[str, None] = 'p10ocrextractionquality'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata JSONB column to documents table
    op.add_column('documents', sa.Column('meta_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'meta_json')

