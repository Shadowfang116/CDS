"""P30: Golden Case Evaluation tables

Revision ID: p30_golden_case_evaluation
Revises: p29_doc_classification
Create Date: 2026-03-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'p30_golden_case_evaluation'
down_revision = 'p29_doc_classification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'golden_case_expectations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('finding_type', sa.String(), nullable=False),
        sa.Column('expected_rule_id', sa.String(), nullable=True),
        sa.Column('expected_title', sa.String(), nullable=False),
        sa.Column('expected_severity', sa.String(), nullable=True),
        sa.Column('expected_text', sa.Text(), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_golden_expectations_org_case', 'golden_case_expectations', ['org_id', 'case_id'])

    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('critical_recall', sa.Float(), nullable=True),
        sa.Column('overall_recall', sa.Float(), nullable=True),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('expected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('missed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extra_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_evaluation_runs_org_case', 'evaluation_runs', ['org_id', 'case_id'])

    op.create_table(
        'evaluation_findings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('evaluation_run_id', sa.UUID(), nullable=False),
        sa.Column('expectation_id', sa.UUID(), nullable=True),
        sa.Column('finding_type', sa.String(), nullable=False),
        sa.Column('expected_rule_id', sa.String(), nullable=True),
        sa.Column('actual_rule_id', sa.String(), nullable=True),
        sa.Column('expected_title', sa.String(), nullable=True),
        sa.Column('actual_title', sa.String(), nullable=True),
        sa.Column('expected_text', sa.Text(), nullable=True),
        sa.Column('actual_text', sa.Text(), nullable=True),
        sa.Column('expected_severity', sa.String(), nullable=True),
        sa.Column('actual_severity', sa.String(), nullable=True),
        sa.Column('match_status', sa.String(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id']),
        sa.ForeignKeyConstraint(['expectation_id'], ['golden_case_expectations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_evaluation_findings_run', 'evaluation_findings', ['evaluation_run_id'])


def downgrade() -> None:
    op.drop_index('idx_evaluation_findings_run', table_name='evaluation_findings')
    op.drop_table('evaluation_findings')
    op.drop_index('idx_evaluation_runs_org_case', table_name='evaluation_runs')
    op.drop_table('evaluation_runs')
    op.drop_index('idx_golden_expectations_org_case', table_name='golden_case_expectations')
    op.drop_table('golden_case_expectations')
