"""p10_dossier_field_history

Revision ID: p10dossierhistory
Revises: 63892f22816d
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'p10dossierhistory'
down_revision: Union[str, None] = '63892f22816d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create dossier_field_history table
    op.create_table(
        'dossier_field_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_key', sa.String(), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('edited_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_page_number', sa.Integer(), nullable=True),
        sa.Column('source_snippet', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['edited_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id']),
    )
    
    # Create indexes
    op.create_index('idx_dossier_field_history_org_case', 'dossier_field_history', ['org_id', 'case_id'])
    op.create_index('idx_dossier_field_history_case_field', 'dossier_field_history', ['case_id', 'field_key'])
    op.create_index('idx_dossier_field_history_edited_at', 'dossier_field_history', ['edited_at'])


def downgrade() -> None:
    op.drop_index('idx_dossier_field_history_edited_at', table_name='dossier_field_history')
    op.drop_index('idx_dossier_field_history_case_field', table_name='dossier_field_history')
    op.drop_index('idx_dossier_field_history_org_case', table_name='dossier_field_history')
    op.drop_table('dossier_field_history')

