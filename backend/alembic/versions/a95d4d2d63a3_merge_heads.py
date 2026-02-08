"""merge heads

Revision ID: a95d4d2d63a3
Revises: 3f02d0d700a5, p14ocrtextcorrections
Create Date: 2025-12-30 05:47:06.047863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95d4d2d63a3'
down_revision: Union[str, None] = ('3f02d0d700a5', 'p14ocrtextcorrections')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

