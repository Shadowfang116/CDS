"""Digest schedule and run models for automated reports."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class DigestSchedule(Base):
    """Scheduled digest configuration."""
    __tablename__ = "digest_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    cadence = Column(String(20), nullable=False, default="weekly")  # "daily" | "weekly"
    hour_local = Column(Integer, nullable=False, default=9)  # Hour of day (0-23)
    weekday = Column(Integer, nullable=True)  # 0=Monday, 6=Sunday (for weekly)
    is_enabled = Column(Boolean, nullable=False, default=True)
    filters_json = Column(JSONB, nullable=False, default={})  # {days: 30, severity: null, status: null}
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_digest_schedules_org_enabled", "org_id", "is_enabled"),
    )


class DigestRun(Base):
    """Record of a digest generation run."""
    __tablename__ = "digest_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("digest_schedules.id"), nullable=False)
    run_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="pending")  # "pending" | "success" | "failed"
    output_export_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to Export if PDF generated
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_digest_runs_schedule_created", "schedule_id", "created_at"),
    )

