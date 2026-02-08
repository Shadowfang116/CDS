"""D10: Pilot readiness - CP evidence, thumbnails, OCR enhancements

Revision ID: h0i1j2k3l4m5
Revises: g9h0i1j2k3l4
Create Date: 2025-12-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'h0i1j2k3l4m5'
down_revision = 'g9h0i1j2k3l4'
branch_labels = None
depends_on = None


def upgrade():
    # Create cp_evidence_refs table
    op.create_table(
        'cp_evidence_refs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('cp_id', UUID(as_uuid=True), sa.ForeignKey('cps.id'), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_cp_evidence_refs_org_cp', 'cp_evidence_refs', ['org_id', 'cp_id'])
    
    # Add thumbnail key to document_pages
    # Check if column exists using raw SQL (Alembic-safe)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='document_pages' AND column_name='minio_key_thumbnail'
    """))
    if result.fetchone() is None:
        op.add_column('document_pages', sa.Column('minio_key_thumbnail', sa.String(), nullable=True))


def downgrade():
    op.drop_table('cp_evidence_refs')
    # Note: Don't drop minio_key_thumbnail as it may be used

