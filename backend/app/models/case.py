import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)  # New, Processing, Review, Pending Docs, Ready for Approval, Approved, Rejected, Closed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Decision fields (Phase 8)
    decision = Column(String(30), nullable=True)  # PASS, CONDITIONAL_PASS, FAIL
    decided_at = Column(DateTime, nullable=True)
    decided_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decision_notes = Column(JSONB, nullable=True)  # {rationale, conditions[], effective_date}
    
    __table_args__ = (
        Index("idx_cases_org_created", "org_id", "created_at"),
        Index("idx_cases_org_status", "org_id", "status"),
    )

