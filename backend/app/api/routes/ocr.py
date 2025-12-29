"""OCR API endpoints."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.document import Document, DocumentPage
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.workers.tasks_ocr import process_document_ocr

router = APIRouter(tags=["ocr"])


class OCREnqueueResponse(BaseModel):
    status: str
    document_id: str
    task_id: Optional[str] = None


class OCRPageStatus(BaseModel):
    page_number: int
    status: str
    error: Optional[str] = None
    has_text: bool = False
    
    class Config:
        from_attributes = True


class OCRStatusResponse(BaseModel):
    document_id: str
    total_pages: int
    status_counts: dict
    pages: list[OCRPageStatus]


class DocTypeUpdateRequest(BaseModel):
    doc_type: str


class DocTypeResponse(BaseModel):
    id: str
    doc_type: Optional[str]
    doc_type_source: Optional[str]
    doc_type_updated_at: Optional[datetime]


@router.post("/documents/{document_id}/ocr", response_model=OCREnqueueResponse)
async def enqueue_document_ocr(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enqueue OCR processing for a document's pages."""
    # Validate document exists and belongs to org
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check document is in Split status
    if document.status != "Split":
        raise HTTPException(
            status_code=400, 
            detail=f"Document must be in 'Split' status to run OCR. Current status: {document.status}"
        )
    
    # Enqueue Celery task
    task = process_document_ocr.delay(
        str(document_id),
        str(current_user.org_id),
        str(current_user.user_id),
    )
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.enqueue",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(document.case_id),
            "task_id": task.id,
        },
    )
    
    return OCREnqueueResponse(
        status="queued",
        document_id=str(document_id),
        task_id=task.id,
    )


@router.get("/documents/{document_id}/ocr-status", response_model=OCRStatusResponse)
async def get_ocr_status(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get OCR processing status for a document."""
    # Validate document exists and belongs to org
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get pages with OCR status
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).order_by(DocumentPage.page_number).all()
    
    # Calculate status counts
    status_counts = {}
    for page in pages:
        status_counts[page.ocr_status] = status_counts.get(page.ocr_status, 0) + 1
    
    # Build page status list
    page_statuses = [
        OCRPageStatus(
            page_number=p.page_number,
            status=p.ocr_status,
            error=p.ocr_error,
            has_text=bool(p.ocr_text),
        )
        for p in pages
    ]
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.status_check",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
        },
    )
    
    return OCRStatusResponse(
        document_id=str(document_id),
        total_pages=len(pages),
        status_counts=status_counts,
        pages=page_statuses,
    )


@router.patch("/documents/{document_id}/doc-type", response_model=DocTypeResponse)
async def update_doc_type(
    request: Request,
    document_id: uuid.UUID,
    body: DocTypeUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually set/override document type."""
    # Validate document exists and belongs to org
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update doc_type fields
    document.doc_type = body.doc_type
    document.doc_type_source = "manual"
    document.doc_type_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.doc_type_update",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(document.case_id),
            "doc_type": body.doc_type,
        },
    )
    
    return DocTypeResponse(
        id=str(document.id),
        doc_type=document.doc_type,
        doc_type_source=document.doc_type_source,
        doc_type_updated_at=document.doc_type_updated_at,
    )

