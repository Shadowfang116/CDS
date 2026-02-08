"""p14_ocr_text_corrections

Revision ID: p14ocrtextcorrections
Revises: p13documentmetadata
Create Date: 2025-01-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p14ocrtextcorrections'
down_revision: Union[str, None] = 'p13documentmetadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ocr_text_corrections table
    op.create_table(
        'ocr_text_corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('corrected_text', sa.Text(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
    )
    
    # Create indexes
    op.create_index('idx_ocr_corrections_org_doc', 'ocr_text_corrections', ['org_id', 'document_id'])
    op.create_index('idx_ocr_corrections_org', 'ocr_text_corrections', ['org_id'])
    op.create_index('idx_ocr_corrections_doc', 'ocr_text_corrections', ['document_id'])
    op.create_index('idx_ocr_corrections_page', 'ocr_text_corrections', ['page_number'])
    
    # Create unique constraint
    op.create_unique_constraint(
        'uq_ocr_correction_org_doc_page',
        'ocr_text_corrections',
        ['org_id', 'document_id', 'page_number']
    )


def downgrade() -> None:
    op.drop_constraint('uq_ocr_correction_org_doc_page', 'ocr_text_corrections', type_='unique')
    op.drop_index('idx_ocr_corrections_page', table_name='ocr_text_corrections')
    op.drop_index('idx_ocr_corrections_doc', table_name='ocr_text_corrections')
    op.drop_index('idx_ocr_corrections_org', table_name='ocr_text_corrections')
    op.drop_index('idx_ocr_corrections_org_doc', table_name='ocr_text_corrections')
    op.drop_table('ocr_text_corrections')

