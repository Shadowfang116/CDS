from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

