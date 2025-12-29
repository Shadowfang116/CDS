"""d4_rules_engine

Revision ID: b6c3d4e5f6g7
Revises: a5d2e3f4g5h6
Create Date: 2025-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b6c3d4e5f6g7'
down_revision: Union[str, None] = 'a5d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exceptions table
    op.create_table('exceptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('module', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cp_text', sa.Text(), nullable=True),
        sa.Column('resolution_conditions', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('waiver_reason', sa.Text(), nullable=True),
        sa.Column('resolved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('waived_by_user_id', sa.UUID(), nullable=True),
        sa.Column('waived_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['waived_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exceptions_org_case_severity_status', 'exceptions', ['org_id', 'case_id', 'severity', 'status'], unique=False)
    op.create_index(op.f('ix_exceptions_org_id'), 'exceptions', ['org_id'], unique=False)
    
    # Create cps table
    op.create_table('cps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('evidence_required', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cps_org_case_severity_status', 'cps', ['org_id', 'case_id', 'severity', 'status'], unique=False)
    op.create_index(op.f('ix_cps_org_id'), 'cps', ['org_id'], unique=False)
    
    # Create exception_evidence_refs table
    op.create_table('exception_evidence_refs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('exception_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['exception_id'], ['exceptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exception_evidence_refs_org_exception', 'exception_evidence_refs', ['org_id', 'exception_id'], unique=False)
    op.create_index(op.f('ix_exception_evidence_refs_org_id'), 'exception_evidence_refs', ['org_id'], unique=False)
    
    # Create rule_runs table
    op.create_table('rule_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rule_runs_org_case', 'rule_runs', ['org_id', 'case_id'], unique=False)
    op.create_index(op.f('ix_rule_runs_org_id'), 'rule_runs', ['org_id'], unique=False)


def downgrade() -> None:
    # Drop rule_runs
    op.drop_index(op.f('ix_rule_runs_org_id'), table_name='rule_runs')
    op.drop_index('idx_rule_runs_org_case', table_name='rule_runs')
    op.drop_table('rule_runs')
    
    # Drop exception_evidence_refs
    op.drop_index(op.f('ix_exception_evidence_refs_org_id'), table_name='exception_evidence_refs')
    op.drop_index('idx_exception_evidence_refs_org_exception', table_name='exception_evidence_refs')
    op.drop_table('exception_evidence_refs')
    
    # Drop cps
    op.drop_index(op.f('ix_cps_org_id'), table_name='cps')
    op.drop_index('idx_cps_org_case_severity_status', table_name='cps')
    op.drop_table('cps')
    
    # Drop exceptions
    op.drop_index(op.f('ix_exceptions_org_id'), table_name='exceptions')
    op.drop_index('idx_exceptions_org_case_severity_status', table_name='exceptions')
    op.drop_table('exceptions')

