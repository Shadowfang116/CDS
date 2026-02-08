"""D6: Saved views for dashboard filters.

Revision ID: d6a1b2c3d4e5
Revises: c7d8e9f0g1h2
Create Date: 2025-12-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd6a1b2c3d4e5'
down_revision = 'c7d8e9f0g1h2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(60), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('config_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.UniqueConstraint('org_id', 'name', name='uq_saved_views_org_name'),
    )
    op.create_index('idx_saved_views_org_id', 'saved_views', ['org_id'])
    op.create_index('idx_saved_views_org_default', 'saved_views', ['org_id', 'is_default'])


def downgrade():
    op.drop_index('idx_saved_views_org_default', table_name='saved_views')
    op.drop_index('idx_saved_views_org_id', table_name='saved_views')
    op.drop_table('saved_views')

