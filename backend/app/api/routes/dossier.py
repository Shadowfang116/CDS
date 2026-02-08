"""Dossier API endpoints for extracted/confirmed fields."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document, DocumentPage, CaseDossierField
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.extraction import extract_from_case_pages, deduplicate_fields

router = APIRouter(tags=["dossier"])


class DossierFieldResponse(BaseModel):
    id: str
    field_key: str
    field_value: Optional[str]
    source_document_id: Optional[str]
    source_page_number: Optional[int]
    confidence: Optional[float]
    needs_confirmation: bool
    confirmed_by_user_id: Optional[str]
    confirmed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DossierResponse(BaseModel):
    case_id: str
    fields: List[DossierFieldResponse]
    field_count: int
    confirmed_count: int
    pending_count: int


class ExtractResponse(BaseModel):
    case_id: str
    extracted_count: int
    new_fields: int
    updated_fields: int


class DossierFieldUpdateRequest(BaseModel):
    field_key: str
    field_value: Optional[str] = None
    needs_confirmation: Optional[bool] = None
    confirm: Optional[bool] = None  # If true, mark as confirmed


class DossierFieldSourceRequest(BaseModel):
    field_key: str
    source_document_id: str
    source_page_number: int


@router.post("/cases/{case_id}/extract", response_model=ExtractResponse)
async def extract_dossier_fields(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract dossier fields from OCR text of all documents in a case.
    Upserts fields by field_key, keeping source info from highest confidence extraction.
    """
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get all documents for this case
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).all()
    
    # Collect all pages with Done OCR status
    pages_data = []
    for doc in documents:
        pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id,
            DocumentPage.org_id == current_user.org_id,
            DocumentPage.ocr_status == "Done",
        ).all()
        for page in pages:
            if page.ocr_text:
                pages_data.append((doc.id, page.page_number, page.ocr_text))
    
    # Run extraction
    extracted_fields = extract_from_case_pages(pages_data)
    extracted_fields = deduplicate_fields(extracted_fields)
    
    # Upsert fields into case_dossier_fields
    new_count = 0
    updated_count = 0
    
    for ef in extracted_fields:
        # Check if field already exists
        existing = db.query(CaseDossierField).filter(
            CaseDossierField.case_id == case_id,
            CaseDossierField.org_id == current_user.org_id,
            CaseDossierField.field_key == ef.field_key,
            CaseDossierField.field_value == ef.field_value,
        ).first()
        
        if existing:
            # Update if new confidence is higher
            if ef.confidence and (existing.confidence is None or ef.confidence > float(existing.confidence)):
                existing.source_document_id = ef.source_document_id
                existing.source_page_number = ef.source_page_number
                existing.confidence = ef.confidence
                existing.updated_at = datetime.utcnow()
                updated_count += 1
        else:
            # Create new field
            new_field = CaseDossierField(
                org_id=current_user.org_id,
                case_id=case_id,
                field_key=ef.field_key,
                field_value=ef.field_value,
                source_document_id=ef.source_document_id,
                source_page_number=ef.source_page_number,
                confidence=ef.confidence,
                needs_confirmation=True,
            )
            db.add(new_field)
            new_count += 1
    
    db.commit()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.extract",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "extracted_count": len(extracted_fields),
            "new_fields": new_count,
            "updated_fields": updated_count,
        },
    )
    
    return ExtractResponse(
        case_id=str(case_id),
        extracted_count=len(extracted_fields),
        new_fields=new_count,
        updated_fields=updated_count,
    )


@router.get("/cases/{case_id}/dossier", response_model=DossierResponse)
async def get_dossier(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all dossier fields for a case."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get all dossier fields
    fields = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
    ).order_by(CaseDossierField.field_key, CaseDossierField.created_at).all()
    
    # Count stats
    confirmed_count = sum(1 for f in fields if not f.needs_confirmation)
    pending_count = sum(1 for f in fields if f.needs_confirmation)
    
    # Build response
    field_responses = [
        DossierFieldResponse(
            id=str(f.id),
            field_key=f.field_key,
            field_value=f.field_value,
            source_document_id=str(f.source_document_id) if f.source_document_id else None,
            source_page_number=f.source_page_number,
            confidence=float(f.confidence) if f.confidence else None,
            needs_confirmation=f.needs_confirmation,
            confirmed_by_user_id=str(f.confirmed_by_user_id) if f.confirmed_by_user_id else None,
            confirmed_at=f.confirmed_at,
        )
        for f in fields
    ]
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.view",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "field_count": len(fields),
        },
    )
    
    return DossierResponse(
        case_id=str(case_id),
        fields=field_responses,
        field_count=len(fields),
        confirmed_count=confirmed_count,
        pending_count=pending_count,
    )


@router.patch("/cases/{case_id}/dossier", response_model=DossierFieldResponse)
async def update_dossier_field(
    request: Request,
    case_id: uuid.UUID,
    body: DossierFieldUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a dossier field value and/or confirmation status.
    If confirm=true, marks the field as confirmed by the current user.
    """
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Find the field by key (we update by field_key, not ID)
    # If multiple fields with same key, we update the first one or create if not exists
    field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == body.field_key,
    ).first()
    
    if not field:
        # Create new field if it doesn't exist
        field = CaseDossierField(
            org_id=current_user.org_id,
            case_id=case_id,
            field_key=body.field_key,
            field_value=body.field_value,
            needs_confirmation=True,
        )
        db.add(field)
    
    # Update value if provided
    if body.field_value is not None:
        field.field_value = body.field_value
        field.updated_at = datetime.utcnow()
    
    # Update needs_confirmation if provided
    if body.needs_confirmation is not None:
        field.needs_confirmation = body.needs_confirmation
    
    # Handle confirmation
    if body.confirm:
        field.needs_confirmation = False
        field.confirmed_by_user_id = current_user.user_id
        field.confirmed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(field)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.update",
        entity_type="case_dossier_field",
        entity_id=field.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "field_key": body.field_key,
            "field_value": body.field_value,
            "confirmed": body.confirm,
        },
    )
    
    return DossierFieldResponse(
        id=str(field.id),
        field_key=field.field_key,
        field_value=field.field_value,
        source_document_id=str(field.source_document_id) if field.source_document_id else None,
        source_page_number=field.source_page_number,
        confidence=float(field.confidence) if field.confidence else None,
        needs_confirmation=field.needs_confirmation,
        confirmed_by_user_id=str(field.confirmed_by_user_id) if field.confirmed_by_user_id else None,
        confirmed_at=field.confirmed_at,
    )


@router.patch("/cases/{case_id}/dossier/source", response_model=DossierFieldResponse)
async def set_dossier_field_source(
    request: Request,
    case_id: uuid.UUID,
    body: DossierFieldSourceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set source evidence (document+page) for a dossier field."""
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate document belongs to case
    doc = db.query(Document).filter(
        Document.id == uuid.UUID(body.source_document_id),
        Document.org_id == current_user.org_id,
        Document.case_id == case_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find field
    field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == body.field_key,
    ).first()
    
    if not field:
        raise HTTPException(status_code=404, detail="Dossier field not found")
    
    # Update source
    field.source_document_id = uuid.UUID(body.source_document_id)
    field.source_page_number = body.source_page_number
    field.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(field)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.field_source_set",
        entity_type="case_dossier_field",
        entity_id=field.id,
        event_metadata={
            "field_key": body.field_key,
            "source_document_id": body.source_document_id,
            "source_page_number": body.source_page_number,
        },
    )
    
    return DossierFieldResponse(
        id=str(field.id),
        field_key=field.field_key,
        field_value=field.field_value,
        source_document_id=str(field.source_document_id) if field.source_document_id else None,
        source_page_number=field.source_page_number,
        confidence=float(field.confidence) if field.confidence else None,
        needs_confirmation=field.needs_confirmation,
        confirmed_by_user_id=str(field.confirmed_by_user_id) if field.confirmed_by_user_id else None,
        confirmed_at=field.confirmed_at,
    )

