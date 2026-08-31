"""Link generated CPs to exceptions for atomic resolution."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "p38_exception_cp_resolution_link"
down_revision = "p37_rule_engine_hard_stops"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes("cps"))


def upgrade() -> None:
    if not _has_column("cps", "source_exception_id"):
        op.add_column("cps", sa.Column("source_exception_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column("cps", "auto_satisfied_from_exception"):
        op.add_column(
            "cps",
            sa.Column(
                "auto_satisfied_from_exception",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        op.alter_column("cps", "auto_satisfied_from_exception", server_default=None)

    inspector = inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys("cps")
    if not any(
        fk.get("referred_table") == "exceptions"
        and fk.get("constrained_columns") == ["source_exception_id"]
        for fk in foreign_keys
    ):
        op.create_foreign_key(
            "cps_source_exception_id_fkey",
            "cps",
            "exceptions",
            ["source_exception_id"],
            ["id"],
        )

    if not _has_index("idx_cps_source_exception"):
        op.create_index("idx_cps_source_exception", "cps", ["org_id", "source_exception_id"], unique=False)

    # Existing rule-generated rows have a stable rule key. Only backfill
    # unambiguous pairs so manual or duplicate rows remain untouched.
    op.execute(
        sa.text(
            """
            UPDATE cps AS cp
            SET source_exception_id = ex.id
            FROM exceptions AS ex
            WHERE cp.source_exception_id IS NULL
              AND cp.org_id = ex.org_id
              AND cp.case_id = ex.case_id
              AND cp.rule_id = ex.rule_id
              AND (
                SELECT count(*)
                FROM exceptions AS ex2
                WHERE ex2.org_id = cp.org_id
                  AND ex2.case_id = cp.case_id
                  AND ex2.rule_id = cp.rule_id
              ) = 1
              AND (
                SELECT count(*)
                FROM cps AS cp2
                WHERE cp2.org_id = cp.org_id
                  AND cp2.case_id = cp.case_id
                  AND cp2.rule_id = cp.rule_id
              ) = 1
            """
        )
    )


def downgrade() -> None:
    if _has_index("idx_cps_source_exception"):
        op.drop_index("idx_cps_source_exception", table_name="cps")
    inspector = inspect(op.get_bind())
    if any(fk.get("name") == "cps_source_exception_id_fkey" for fk in inspector.get_foreign_keys("cps")):
        op.drop_constraint("cps_source_exception_id_fkey", "cps", type_="foreignkey")
    if _has_column("cps", "auto_satisfied_from_exception"):
        op.drop_column("cps", "auto_satisfied_from_exception")
    if _has_column("cps", "source_exception_id"):
        op.drop_column("cps", "source_exception_id")
