from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    temporary_password: str
    role: str


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str | None = None
    org_id: UUID
    org_name: str
    role: str
    must_change_password: bool = False
    last_login_at: datetime | None = None
    
    class Config:
        from_attributes = True

