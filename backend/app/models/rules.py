"""D4: Rule engine models - Exceptions, CPs, Evidence Refs, Rule Runs."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Exception_(Base):
    """Rule evaluation exceptions requiring attention."""
    __tablename__ = "exceptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    module = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # Low, Medium, High
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cp_text = Column(Text, nullable=True)  # Condition Precedent text
    resolution_conditions = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="Open")  # Open, Resolved, Waived
    waiver_reason = Column(Text, nullable=True)
    resolved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    waived_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    waived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_exceptions_org_case_severity_status", "org_id", "case_id", "severity", "status"),
    )


class ConditionPrecedent(Base):
    """Conditions Precedent generated from rule evaluation."""
    __tablename__ = "cps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # Low, Medium, High
    text = Column(Text, nullable=False)
    evidence_required = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="Open")  # Open, Satisfied, Waived
    # Verification satisfaction linkage
    satisfied_by_verification_type = Column(String, nullable=True)  # e_stamp, registry_rod
    satisfied_at = Column(DateTime, nullable=True)
    satisfied_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_cps_org_case_severity_status", "org_id", "case_id", "severity", "status"),
    )


class ExceptionEvidenceRef(Base):
    """Evidence references linking exceptions to documents/pages."""
    __tablename__ = "exception_evidence_refs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    exception_id = Column(UUID(as_uuid=True), ForeignKey("exceptions.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    page_number = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_exception_evidence_refs_org_exception", "org_id", "exception_id"),
    )


class RuleRun(Base):
    """Rule evaluation run tracking for tuning."""
    __tablename__ = "rule_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    summary = Column(JSONB, nullable=True)  # {high: N, medium: N, low: N, total: N, cps_total: N}
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_rule_runs_org_case", "org_id", "case_id"),
    )

