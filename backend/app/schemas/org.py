from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class OrgResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

