"""Add OCR quality signal to document pages.

Revision ID: p34_ocr_quality_signal
Revises: p33_production_pilot_hardening
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "p34_ocr_quality_signal"
down_revision = "p33_production_pilot_hardening"
branch_labels = None
depends_on = None


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "document_pages" in tables and "ocr_quality_signal" not in _columns(inspector, "document_pages"):
        op.add_column("document_pages", sa.Column("ocr_quality_signal", sa.String(20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "document_pages" in tables and "ocr_quality_signal" in _columns(inspector, "document_pages"):
        op.drop_column("document_pages", "ocr_quality_signal")