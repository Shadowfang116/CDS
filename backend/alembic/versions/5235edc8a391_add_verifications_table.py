"""add_verifications_table

Revision ID: 5235edc8a391
Revises: 5522cccb0f37
Create Date: 2025-12-30 07:24:32.559272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5235edc8a391'
down_revision: Union[str, None] = 'a95d4d2d63a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create verifications table
    op.create_table(
        'verifications',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('case_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('verification_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='Pending'),
        sa.Column('keys_json', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('verified_by_user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_verifications_org_case_type', 'verifications', ['org_id', 'case_id', 'verification_type'])
    
    # Create verification_evidence_refs table
    op.create_table(
        'verification_evidence_refs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('verification_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('verifications.id'), nullable=False),
        sa.Column('document_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_verification_evidence_refs_org_verification', 'verification_evidence_refs', ['org_id', 'verification_id'])


def downgrade() -> None:
    op.drop_index('idx_verification_evidence_refs_org_verification', table_name='verification_evidence_refs')
    op.drop_table('verification_evidence_refs')
    op.drop_index('idx_verifications_org_case_type', table_name='verifications')
    op.drop_table('verifications')

