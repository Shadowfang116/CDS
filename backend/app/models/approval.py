"""Approval workflow model for maker/checker controls."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class ApprovalRequest(Base):
    """Approval request for maker/checker workflow."""
    __tablename__ = "approval_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    
    # Requester (Maker)
    requested_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_by_role = Column(String(50), nullable=False)  # Reviewer, Admin
    
    # Request details
    request_type = Column(String(50), nullable=False)  # exception_waive, cp_waive, case_decision, export_release
    status = Column(String(20), nullable=False, default="Pending")  # Pending, Approved, Rejected, Cancelled
    payload_json = Column(JSONB, nullable=False)  # Type-specific payload
    
    # Decision (Checker)
    decided_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_approval_requests_org_status", "org_id", "status"),
        Index("idx_approval_requests_case", "case_id", "status"),
        Index("idx_approval_requests_requester", "requested_by_user_id", "status"),
        # Dual control: requester cannot be decider (enforced in service layer)
    )


# Request type constants
APPROVAL_REQUEST_TYPES = {
    "exception_waive": "Exception Waiver",
    "cp_waive": "Condition Precedent Waiver",
    "case_decision": "Case Decision",
    "export_release": "Export Release",
}

# Status constants
APPROVAL_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]

# Case decision values
CASE_DECISIONS = ["PASS", "CONDITIONAL_PASS", "FAIL"]

