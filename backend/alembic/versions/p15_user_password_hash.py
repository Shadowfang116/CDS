"""Add password hash to users

Revision ID: p15_user_password_hash
Revises: p32_ocr_candidate_quality_fields
Create Date: 2026-04-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "p15_user_password_hash"
down_revision = "p32_ocr_candidate_quality_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
