"""d5_exports

Revision ID: c7d8e9f0g1h2
Revises: b6c3d4e5f6g7
Create Date: 2025-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0g1h2'
down_revision: Union[str, None] = 'b6c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exports table
    op.create_table('exports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('export_type', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('minio_key', sa.String(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exports_org_case_created', 'exports', ['org_id', 'case_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_exports_org_id'), 'exports', ['org_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_exports_org_id'), table_name='exports')
    op.drop_index('idx_exports_org_case_created', table_name='exports')
    op.drop_table('exports')

