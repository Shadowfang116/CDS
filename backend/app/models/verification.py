"""Verification models for e-Stamp and Registry/ROD assisted verification."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Verification(Base):
    """Verification records for e-Stamp and Registry/ROD."""
    __tablename__ = "verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    verification_type = Column(String, nullable=False)  # e_stamp, registry_rod
    status = Column(String, nullable=False, default="Pending")  # Pending, Verified, Failed
    keys_json = Column(JSONB, nullable=True)  # {stamp_number: "...", date: "...", amount: "..."}
    notes = Column(Text, nullable=True)
    verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_verifications_org_case_type", "org_id", "case_id", "verification_type"),
    )


class VerificationEvidenceRef(Base):
    """Evidence references linking verifications to documents."""
    __tablename__ = "verification_evidence_refs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    verification_id = Column(UUID(as_uuid=True), ForeignKey("verifications.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_verification_evidence_refs_org_verification", "org_id", "verification_id"),
    )

