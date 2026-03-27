"""Phase 10: Add OCR override fields to document_pages

Revision ID: p24_ocr_override
Revises: p23_exports_phase8_status_error
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p24_ocr_override'
down_revision = 'p20_add_run_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add OCR override columns
    op.add_column('document_pages', sa.Column('ocr_text_override', sa.Text(), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_override_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_override_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_override_reason', sa.String(length=500), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_document_pages_ocr_override_user',
        'document_pages', 'users',
        ['ocr_override_user_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index on override_updated_at
    op.create_index(
        'idx_document_pages_override_updated',
        'document_pages',
        ['ocr_override_updated_at']
    )


def downgrade():
    # Drop index
    op.drop_index('idx_document_pages_override_updated', table_name='document_pages')
    
    # Drop foreign key
    op.drop_constraint('fk_document_pages_ocr_override_user', 'document_pages', type_='foreignkey')
    
    # Drop columns
    op.drop_column('document_pages', 'ocr_override_reason')
    op.drop_column('document_pages', 'ocr_override_user_id')
    op.drop_column('document_pages', 'ocr_override_updated_at')
    op.drop_column('document_pages', 'ocr_text_override')
