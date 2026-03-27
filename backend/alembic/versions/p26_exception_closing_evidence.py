"""P26: Add is_closing to exception_evidence_refs

Revision ID: p26_exception_closing_evidence
Revises: p25_merge_heads
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "p26_exception_closing_evidence"
down_revision = "p25_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exception_evidence_refs",
        sa.Column("is_closing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE exception_evidence_refs SET is_closing = FALSE")
    op.alter_column("exception_evidence_refs", "is_closing", server_default=None)


def downgrade() -> None:
    op.drop_column("exception_evidence_refs", "is_closing")

