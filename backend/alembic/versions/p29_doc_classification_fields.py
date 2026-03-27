"""P29: Add classification fields to documents and create document_classification_logs

Revision ID: p29_doc_classification
Revises: p28_exception_waiver_category
Create Date: 2026-03-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p29_doc_classification'
down_revision = 'p28_exception_waiver_category'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        cols = [c.get('name') for c in inspector.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add missing columns to documents
    if _has_table(inspector, 'documents'):
        if not _has_column(inspector, 'documents', 'predicted_doc_type'):
            op.add_column('documents', sa.Column('predicted_doc_type', sa.String(), nullable=True))
        if not _has_column(inspector, 'documents', 'classification_confidence'):
            op.add_column('documents', sa.Column('classification_confidence', sa.Numeric(), nullable=True))
        if not _has_column(inspector, 'documents', 'corrected_doc_type'):
            op.add_column('documents', sa.Column('corrected_doc_type', sa.String(), nullable=True))
        if not _has_column(inspector, 'documents', 'classification_status'):
            op.add_column(
                'documents',
                sa.Column('classification_status', sa.String(), nullable=False, server_default='auto')
            )
        if not _has_column(inspector, 'documents', 'needs_review'):
            op.add_column(
                'documents',
                sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.text('false'))
            )

    # Create document_classification_logs if missing
    if not _has_table(inspector, 'document_classification_logs'):
        op.create_table(
            'document_classification_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False, index=True),
            sa.Column('predicted_doc_type', sa.String(), nullable=False),
            sa.Column('corrected_doc_type', sa.String(), nullable=True),
            sa.Column('confidence', sa.Numeric(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, 'document_classification_logs'):
        op.drop_table('document_classification_logs')

    if _has_table(inspector, 'documents'):
        # Drop newly added columns only if present
        for col in ['needs_review', 'classification_status', 'corrected_doc_type', 'classification_confidence', 'predicted_doc_type']:
            if _has_column(inspector, 'documents', col):
                try:
                    op.drop_column('documents', col)
                except Exception:
                    pass