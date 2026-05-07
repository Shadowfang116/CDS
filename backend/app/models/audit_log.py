import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import synonym

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    before_json = Column(JSONB, nullable=True)
    after_json = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    request_id = Column(String, nullable=True, index=True)

    actor_user_id = synonym("actor_id")
    event_metadata = synonym("after_json")
    before_snapshot = synonym("before_json")
    after_snapshot = synonym("after_json")

    __table_args__ = (
        Index("idx_audit_log_org_created", "org_id", "created_at"),
        Index("idx_audit_log_org_case_created", "org_id", "case_id", "created_at"),
    )
