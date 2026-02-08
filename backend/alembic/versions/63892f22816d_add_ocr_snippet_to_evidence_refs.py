"""add_ocr_snippet_to_evidence_refs

Revision ID: 63892f22816d
Revises: h0i1j2k3l4m5
Create Date: 2025-12-29 21:49:56.525916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '63892f22816d'
down_revision: Union[str, None] = 'h0i1j2k3l4m5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OCR snippet support to exception_evidence_refs
    op.add_column('exception_evidence_refs', sa.Column('evidence_type', sa.String(), nullable=True))
    op.add_column('exception_evidence_refs', sa.Column('snippet_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add OCR snippet support to cp_evidence_refs
    op.add_column('cp_evidence_refs', sa.Column('evidence_type', sa.String(), nullable=True))
    op.add_column('cp_evidence_refs', sa.Column('snippet_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('cp_evidence_refs', 'snippet_json')
    op.drop_column('cp_evidence_refs', 'evidence_type')
    op.drop_column('exception_evidence_refs', 'snippet_json')
    op.drop_column('exception_evidence_refs', 'evidence_type')

