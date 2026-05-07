from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class CaseCreate(BaseModel):
    title: str


class CaseResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    status: str
    assigned_to_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CaseStatusUpdate(BaseModel):
    status: str


class CaseAssignmentUpdate(BaseModel):
    action: str  # "claim" | "unassign"


class CaseListResponse(BaseModel):
    """Paginated list response for GET /cases."""
    items: list[CaseResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

