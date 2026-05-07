from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class AuditLogResponse(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID | None = None
    actor_user_id: UUID
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    event_metadata: Optional[Dict[str, Any]]
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

