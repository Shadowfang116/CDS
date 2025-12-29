from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class AuditLogResponse(BaseModel):
    id: UUID
    org_id: UUID
    actor_user_id: UUID
    action: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    event_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

