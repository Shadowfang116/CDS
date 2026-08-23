"""P30: Golden Case Evaluation models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class GoldenCaseExpectation(Base):
    """Expected findings for a golden case used to benchmark evaluation recall."""
    __tablename__ = "golden_case_expectations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    finding_type = Column(String, nullable=False)          # "exception" | "cp"
    expected_rule_id = Column(String, nullable=True)
    expected_title = Column(String, nullable=False)
    expected_severity = Column(String, nullable=True)      # Low, Medium, High
    expected_text = Column(Text, nullable=True)
    is_critical = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_golden_expectations_org_case", "org_id", "case_id"),
    )


class EvaluationRun(Base):
    """A single evaluation run comparing actual outputs against golden expectations."""
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    critical_recall = Column(Float, nullable=True)         # matched critical / total critical
    overall_recall = Column(Float, nullable=True)          # matched / total expected
    precision = Column(Float, nullable=True)               # matched / total actual
    expected_count = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    missed_count = Column(Integer, nullable=False, default=0)
    extra_count = Column(Integer, nullable=False, default=0)
    decision = Column(String(30), nullable=True)
    status = Column(String, nullable=False, default="running")  # running | completed | failed
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_evaluation_runs_org_case", "org_id", "case_id"),
    )


class EvaluationFinding(Base):
    """Individual matched/missed/extra finding from one evaluation run."""
    __tablename__ = "evaluation_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False)
    expectation_id = Column(UUID(as_uuid=True), ForeignKey("golden_case_expectations.id"), nullable=True)
    finding_type = Column(String, nullable=False)          # "exception" | "cp"
    expected_rule_id = Column(String, nullable=True)
    actual_rule_id = Column(String, nullable=True)
    expected_title = Column(String, nullable=True)
    actual_title = Column(String, nullable=True)
    expected_text = Column(Text, nullable=True)
    actual_text = Column(Text, nullable=True)
    expected_severity = Column(String, nullable=True)
    actual_severity = Column(String, nullable=True)
    match_status = Column(String, nullable=False)          # matched | missed | extra
    similarity_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_evaluation_findings_run", "evaluation_run_id"),
    )
