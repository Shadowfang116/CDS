from pydantic import BaseModel, EmailStr
from uuid import UUID


class DevLoginRequest(BaseModel):
    email: EmailStr
    org_name: str
    role: str  # Admin, Reviewer, Approver, Viewer


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    org_id: UUID
    org_name: str
    role: str
    
    class Config:
        from_attributes = True

