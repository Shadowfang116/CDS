"""add_satisfied_by_user_id_to_cps

NOTE:
The column `cps.satisfied_by_user_id` is already introduced in down_revision
`28c206261b4e...`. This migration must therefore be idempotent and must NOT
drop the column on downgrade (downgrading to 28c must preserve 28c schema).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5ec98b0fbc01"
down_revision = "28c206261b4e"
branch_labels = None
depends_on = None

TABLE = "cps"
COL = "satisfied_by_user_id"
REF_TABLE = "users"
REF_COL = "id"

# Use a stable name for constraints we create.
FK_NAME = "fk_cps_satisfied_by_user_id_users"


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    cols = insp.get_columns(table_name)
    return any(c.get("name") == column_name for c in cols)


def _fk_for_column_exists(conn, table_name: str, column_name: str, referred_table: str) -> bool:
    insp = inspect(conn)
    fks = insp.get_foreign_keys(table_name) or []
    for fk in fks:
        if fk.get("referred_table") != referred_table:
            continue
        constrained = fk.get("constrained_columns") or []
        if constrained == [column_name]:
            return True
    return False


def _constraint_name_exists(conn, constraint_name: str) -> bool:
    # Best-effort, Postgres-specific. Prevents create/drop noise.
    row = conn.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
        {"name": constraint_name},
    ).first()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Column may already exist from down_revision (28c...). Only add if missing.
    if not _column_exists(conn, TABLE, COL):
        op.add_column(TABLE, sa.Column(COL, postgresql.UUID(as_uuid=True), nullable=True))

    # Ensure FK exists. Do not assume a specific name might already exist.
    if _column_exists(conn, TABLE, COL) and not _fk_for_column_exists(conn, TABLE, COL, REF_TABLE):
        op.create_foreign_key(
            FK_NAME,
            TABLE,
            REF_TABLE,
            [COL],
            [REF_COL],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Downgrading from 5ec -> 28c must keep the column (28c already has it).
    # Only drop the FK we created (or skip if it does not exist).
    if _constraint_name_exists(conn, FK_NAME):
        op.drop_constraint(FK_NAME, TABLE, type_="foreignkey")
