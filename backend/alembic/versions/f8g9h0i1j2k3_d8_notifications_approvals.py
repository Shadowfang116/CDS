"""D8: Notifications and approval workflow

Revision ID: f8g9h0i1j2k3
Revises: e7f8g9h0i1j2
Create Date: 2025-12-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'f8g9h0i1j2k3'
down_revision = 'e7f8g9h0i1j2'
branch_labels = None
depends_on = None


def upgrade():
    # Add decision fields to cases
    op.add_column('cases', sa.Column('decision', sa.String(30), nullable=True))
    op.add_column('cases', sa.Column('decided_at', sa.DateTime(), nullable=True))
    op.add_column('cases', sa.Column('decided_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('cases', sa.Column('decision_notes', JSONB, nullable=True))
    op.create_index('idx_cases_org_status', 'cases', ['org_id', 'status'])
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', 'is_read', 'created_at'])
    op.create_index('idx_notifications_org_created', 'notifications', ['org_id', 'created_at'])
    
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('digest_opt_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_high_risk', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_case_update', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('requested_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('requested_by_role', sa.String(50), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending'),
        sa.Column('payload_json', JSONB, nullable=False),
        sa.Column('decided_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_approval_requests_org_status', 'approval_requests', ['org_id', 'status'])
    op.create_index('idx_approval_requests_case', 'approval_requests', ['case_id', 'status'])
    op.create_index('idx_approval_requests_requester', 'approval_requests', ['requested_by_user_id', 'status'])


def downgrade():
    op.drop_table('approval_requests')
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.drop_index('idx_cases_org_status', table_name='cases')
    op.drop_column('cases', 'decision_notes')
    op.drop_column('cases', 'decided_by_user_id')
    op.drop_column('cases', 'decided_at')
    op.drop_column('cases', 'decision')

