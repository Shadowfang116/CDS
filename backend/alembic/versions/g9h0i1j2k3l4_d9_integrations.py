"""D9: Email notifications and webhooks integrations

Revision ID: g9h0i1j2k3l4
Revises: f8g9h0i1j2k3
Create Date: 2025-12-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'g9h0i1j2k3l4'
down_revision = 'f8g9h0i1j2k3'
branch_labels = None
depends_on = None


def upgrade():
    # Create integration_events table (outbox)
    op.create_table(
        'integration_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('payload_json', JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending', index=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('locked_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    op.create_index('idx_integration_events_org_status', 'integration_events', ['org_id', 'status'])
    op.create_index('idx_integration_events_next_attempt', 'integration_events', ['status', 'next_attempt_at'])
    
    # Create webhook_endpoints table
    op.create_table(
        'webhook_endpoints',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('secret_ciphertext', sa.Text(), nullable=False),
        sa.Column('secret_preview', sa.String(10), nullable=False),
        sa.Column('subscribed_events', JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_webhook_endpoints_org_enabled', 'webhook_endpoints', ['org_id', 'is_enabled'])
    
    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('endpoint_id', UUID(as_uuid=True), sa.ForeignKey('webhook_endpoints.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload_json', JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending', index=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('response_body_snippet', sa.Text(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_webhook_deliveries_org_endpoint', 'webhook_deliveries', ['org_id', 'endpoint_id', 'created_at'])
    op.create_index('idx_webhook_deliveries_status', 'webhook_deliveries', ['status', 'created_at'])
    
    # Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('template_key', sa.String(50), nullable=False, index=True),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('body_md', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_email_templates_org_key', 'email_templates', ['org_id', 'template_key'], unique=True)
    
    # Create email_deliveries table
    op.create_table(
        'email_deliveries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('to_email', sa.String(200), nullable=False, index=True),
        sa.Column('template_key', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='Pending', index=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_email_deliveries_org_email', 'email_deliveries', ['org_id', 'to_email', 'created_at'])
    op.create_index('idx_email_deliveries_status', 'email_deliveries', ['status', 'created_at'])


def downgrade():
    op.drop_table('email_deliveries')
    op.drop_table('email_templates')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_endpoints')
    op.drop_table('integration_events')

