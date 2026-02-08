"""add_satisfied_by_verification_type_to_cps

Revision ID: 28c206261b4e
Revises: 5235edc8a391
Create Date: 2025-12-30 07:50:20.954393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c206261b4e'
down_revision: Union[str, None] = '5235edc8a391'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add satisfied_by_verification_type, satisfied_at, and satisfied_by_user_id columns to cps table
    from sqlalchemy.dialects.postgresql import UUID
    op.add_column('cps', sa.Column('satisfied_by_verification_type', sa.String(), nullable=True))
    op.add_column('cps', sa.Column('satisfied_at', sa.DateTime(), nullable=True))
    op.add_column('cps', sa.Column('satisfied_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('cps', 'satisfied_by_user_id')
    op.drop_column('cps', 'satisfied_at')
    op.drop_column('cps', 'satisfied_by_verification_type')

