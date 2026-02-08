"""p7_ocr_extraction_candidates

Revision ID: 3f02d0d700a5
Revises: 63892f22816d
Create Date: 2025-12-29 22:10:13.466168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3f02d0d700a5'
down_revision: Union[str, None] = '63892f22816d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ocr_extraction_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('field_key', sa.String(), nullable=False),
        sa.Column('proposed_value', sa.Text(), nullable=False),
        sa.Column('edited_value', sa.Text(), nullable=True),
        sa.Column('final_value', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='Pending'),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('confirmed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('amendment_of', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['confirmed_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['amendment_of'], ['ocr_extraction_candidates.id'], ),
    )
    op.create_index('idx_ocr_extractions_org_case_status', 'ocr_extraction_candidates', ['org_id', 'case_id', 'status'])
    op.create_index('idx_ocr_extractions_org_field', 'ocr_extraction_candidates', ['org_id', 'field_key'])
    op.create_index(op.f('ix_ocr_extraction_candidates_org_id'), 'ocr_extraction_candidates', ['org_id'], unique=False)
    op.create_index(op.f('ix_ocr_extraction_candidates_case_id'), 'ocr_extraction_candidates', ['case_id'], unique=False)
    op.create_index(op.f('ix_ocr_extraction_candidates_document_id'), 'ocr_extraction_candidates', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ocr_extraction_candidates_document_id'), table_name='ocr_extraction_candidates')
    op.drop_index(op.f('ix_ocr_extraction_candidates_case_id'), table_name='ocr_extraction_candidates')
    op.drop_index(op.f('ix_ocr_extraction_candidates_org_id'), table_name='ocr_extraction_candidates')
    op.drop_index('idx_ocr_extractions_org_field', table_name='ocr_extraction_candidates')
    op.drop_index('idx_ocr_extractions_org_case_status', table_name='ocr_extraction_candidates')
    op.drop_table('ocr_extraction_candidates')

