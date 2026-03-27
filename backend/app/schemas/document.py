from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class DocumentResponse(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    page_count: Optional[int]
    status: str
    error_message: Optional[str]
    doc_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: UUID
    original_filename: str
    page_count: Optional[int]
    status: str
    doc_type: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentPageResponse(BaseModel):
    id: UUID
    page_number: int
    has_thumbnail: bool
    ocr_status: str
    ocr_confidence: Optional[float]
    
    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    page_count: Optional[int]
    status: str
    error_message: Optional[str]
    doc_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    pages: List[DocumentPageResponse]
    
    class Config:
        from_attributes = True


class PresignedUrlResponse(BaseModel):
    url: str
    expires_in_seconds: int


