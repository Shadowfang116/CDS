"""d3_ocr_and_dossier

Revision ID: a5d2e3f4g5h6
Revises: 9131c1974bd1
Create Date: 2025-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5d2e3f4g5h6'
down_revision: Union[str, None] = '9131c1974bd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OCR fields to document_pages
    op.add_column('document_pages', sa.Column('ocr_text', sa.Text(), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_error', sa.Text(), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_started_at', sa.DateTime(), nullable=True))
    op.add_column('document_pages', sa.Column('ocr_finished_at', sa.DateTime(), nullable=True))
    
    # Add doc_type fields to documents
    op.add_column('documents', sa.Column('doc_type', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('doc_type_source', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('doc_type_updated_at', sa.DateTime(), nullable=True))
    
    # Create case_dossier_fields table
    op.create_table('case_dossier_fields',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('field_key', sa.String(), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('source_document_id', sa.UUID(), nullable=True),
        sa.Column('source_page_number', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('needs_confirmation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('confirmed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['confirmed_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_case_dossier_fields_org_case_key', 'case_dossier_fields', ['org_id', 'case_id', 'field_key'], unique=False)
    op.create_index(op.f('ix_case_dossier_fields_org_id'), 'case_dossier_fields', ['org_id'], unique=False)


def downgrade() -> None:
    # Drop case_dossier_fields
    op.drop_index(op.f('ix_case_dossier_fields_org_id'), table_name='case_dossier_fields')
    op.drop_index('idx_case_dossier_fields_org_case_key', table_name='case_dossier_fields')
    op.drop_table('case_dossier_fields')
    
    # Remove doc_type fields from documents
    op.drop_column('documents', 'doc_type_updated_at')
    op.drop_column('documents', 'doc_type_source')
    op.drop_column('documents', 'doc_type')
    
    # Remove OCR fields from document_pages
    op.drop_column('document_pages', 'ocr_finished_at')
    op.drop_column('document_pages', 'ocr_started_at')
    op.drop_column('document_pages', 'ocr_error')
    op.drop_column('document_pages', 'ocr_text')

