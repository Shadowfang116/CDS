"""D7: Shared views and scheduled digests

Revision ID: e7f8g9h0i1j2
Revises: d6a1b2c3d4e5
Create Date: 2025-12-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'd6a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    # Add sharing columns to saved_views
    op.add_column('saved_views', sa.Column('visibility', sa.String(20), nullable=False, server_default='private'))
    op.add_column('saved_views', sa.Column('shared_with_roles', JSONB, nullable=False, server_default='[]'))
    op.add_column('saved_views', sa.Column('shared_with_user_ids', JSONB, nullable=False, server_default='[]'))
    op.add_column('saved_views', sa.Column('last_used_at', sa.DateTime(), nullable=True))
    op.create_index('idx_saved_views_org_visibility', 'saved_views', ['org_id', 'visibility'])
    
    # Make exports.case_id nullable for dashboard/digest exports
    op.alter_column('exports', 'case_id', nullable=True)
    
    # Create digest_schedules table
    op.create_table(
        'digest_schedules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('cadence', sa.String(20), nullable=False, server_default='weekly'),
        sa.Column('hour_local', sa.Integer(), nullable=False, server_default='9'),
        sa.Column('weekday', sa.Integer(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('filters_json', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_digest_schedules_org_enabled', 'digest_schedules', ['org_id', 'is_enabled'])
    
    # Create digest_runs table
    op.create_table(
        'digest_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('schedule_id', UUID(as_uuid=True), sa.ForeignKey('digest_schedules.id'), nullable=False),
        sa.Column('run_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('output_export_id', UUID(as_uuid=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_digest_runs_schedule_created', 'digest_runs', ['schedule_id', 'created_at'])


def downgrade():
    op.drop_table('digest_runs')
    op.drop_table('digest_schedules')
    op.alter_column('exports', 'case_id', nullable=False)
    op.drop_index('idx_saved_views_org_visibility', table_name='saved_views')
    op.drop_column('saved_views', 'last_used_at')
    op.drop_column('saved_views', 'shared_with_user_ids')
    op.drop_column('saved_views', 'shared_with_roles')
    op.drop_column('saved_views', 'visibility')

