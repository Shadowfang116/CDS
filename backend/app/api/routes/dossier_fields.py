"""Dossier field editing API endpoints with history tracking (P10)."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document, CaseDossierField
from app.models.dossier_field_history import DossierFieldHistory
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(prefix="/cases", tags=["dossier-fields"])


class DossierFieldItem(BaseModel):
    """Dossier field with evidence info."""
    field_key: str
    field_value: Optional[str]
    source_document_id: Optional[str]
    source_page_number: Optional[int]
    source_snippet: Optional[dict] = None
    last_edited_by: Optional[str] = None  # User email
    last_edited_at: Optional[datetime] = None
    needs_confirmation: bool
    
    class Config:
        from_attributes = True


class DossierFieldsResponse(BaseModel):
    """Response for listing dossier fields."""
    case_id: str
    fields: List[DossierFieldItem]


class DossierFieldEditRequest(BaseModel):
    """Request to edit a dossier field. P14: Note required, evidence required for critical fields."""
    value: Optional[str] = None
    evidence: Optional[dict] = None  # {document_id, page_number} OR {snippet_json}
    note: str  # P14: Required for all manual edits (min 5 chars)
    force: bool = False  # P14: Allow edit without evidence for critical fields (Admin only)


class DossierFieldHistoryItem(BaseModel):
    """History entry for a dossier field."""
    id: str
    old_value: Optional[str]
    new_value: Optional[str]
    edited_by: str  # User email
    edited_at: datetime
    source_type: str
    source_document_id: Optional[str] = None
    source_page_number: Optional[int] = None
    note: Optional[str] = None
    
    class Config:
        from_attributes = True


class DossierFieldHistoryResponse(BaseModel):
    """Response for field history."""
    field_key: str
    history: List[DossierFieldHistoryItem]


@router.get("/{case_id}/dossier/fields", response_model=DossierFieldsResponse)
async def get_dossier_fields(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all dossier fields for a case with evidence and edit info."""
    # Verify case exists and belongs to org
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
    ).order_by(CaseDossierField.field_key).all()
    
    # Get last edit info from history
    from app.models.user import User
    field_items = []
    for field in fields:
        # Get last history entry
        last_history = db.query(DossierFieldHistory).filter(
            DossierFieldHistory.case_id == case_id,
            DossierFieldHistory.org_id == current_user.org_id,
            DossierFieldHistory.field_key == field.field_key,
        ).order_by(DossierFieldHistory.edited_at.desc()).first()
        
        last_edited_by = None
        last_edited_at = None
        if last_history:
            user = db.query(User).filter(User.id == last_history.edited_by_user_id).first()
            last_edited_by = user.email if user else None
            last_edited_at = last_history.edited_at
        
        # Get source snippet if available (from history)
        source_snippet = None
        if last_history and last_history.source_snippet:
            source_snippet = last_history.source_snippet
        
        field_items.append(DossierFieldItem(
            field_key=field.field_key,
            field_value=field.field_value,
            source_document_id=str(field.source_document_id) if field.source_document_id else None,
            source_page_number=field.source_page_number,
            source_snippet=source_snippet,
            last_edited_by=last_edited_by,
            last_edited_at=last_edited_at,
            needs_confirmation=field.needs_confirmation,
        ))
    
    return DossierFieldsResponse(
        case_id=str(case_id),
        fields=field_items,
    )


# P14: Critical fields that require evidence (unless force=true)
CRITICAL_FIELDS = {
    "property.plot_number",
    "property.khasra_numbers",
    "registration.registry_number",
    "stamp.estamp_id_or_number",
}


@router.patch("/{case_id}/dossier/fields/{field_key}", response_model=DossierFieldItem)
async def edit_dossier_field(
    request: Request,
    case_id: uuid.UUID,
    field_key: str,
    body: DossierFieldEditRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit a dossier field value. P14: Note required, evidence required for critical fields."""
    # P14: Validate note (required, min 5 chars)
    if not body.note or len(body.note.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Note is required and must be at least 5 characters long"
        )
    
    # Verify case exists
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # P14: Check if field is critical and requires evidence
    is_critical = field_key in CRITICAL_FIELDS
    has_evidence = body.evidence and (
        ("document_id" in body.evidence and "page_number" in body.evidence) or
        "snippet_json" in body.evidence
    )
    
    if is_critical and not has_evidence and not body.force:
        raise HTTPException(
            status_code=400,
            detail=f"Evidence required for critical field '{field_key}'. Provide evidence or set force=true (Admin only)"
        )
    
    # P14: Force flag only allowed for Admin
    if body.force and current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Only Admin can use force flag to edit critical fields without evidence"
        )
    
    # Get or create field
    field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == field_key,
    ).first()
    
    old_value = field.field_value if field else None
    
    if not field:
        field = CaseDossierField(
            org_id=current_user.org_id,
            case_id=case_id,
            field_key=field_key,
            field_value=body.value,
            needs_confirmation=False,  # Manual edit = confirmed
        )
        db.add(field)
    else:
        # Update value
        if body.value is not None:
            field.field_value = body.value
            field.needs_confirmation = False  # Manual edit = confirmed
            field.updated_at = datetime.utcnow()
    
    # Handle evidence linking
    if body.evidence:
        if "document_id" in body.evidence and "page_number" in body.evidence:
            field.source_document_id = uuid.UUID(body.evidence["document_id"])
            field.source_page_number = body.evidence["page_number"]
        elif "snippet_json" in body.evidence:
            # Store snippet in history, not directly in field
            pass  # Will be stored in history entry
    
    db.flush()
    
    # Write history entry
    history_entry = DossierFieldHistory(
        org_id=current_user.org_id,
        case_id=case_id,
        field_key=field_key,
        old_value=old_value,
        new_value=body.value,
        edited_by_user_id=current_user.user_id,
        edited_at=datetime.utcnow(),
        source_type="manual",
        source_document_id=field.source_document_id,
        source_page_number=field.source_page_number,
        source_snippet=body.evidence.get("snippet_json") if body.evidence else None,
        note=body.note,
    )
    db.add(history_entry)
    db.commit()
    db.refresh(field)
    
    # P14: Audit log (include force flag if used)
    audit_action = "dossier.field_edit"
    audit_metadata = {
        "field_key": field_key,
        "old_value": old_value,
        "new_value": body.value,
        "source_type": "manual",
        "note_length": len(body.note),
    }
    
    if is_critical and not has_evidence and body.force:
        audit_action = "dossier.field_edit_force_no_evidence"
        audit_metadata["force_no_evidence"] = True
        audit_metadata["is_critical_field"] = True
    
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action=audit_action,
        entity_type="case",
        entity_id=case_id,
        event_metadata=audit_metadata,
    )
    
    # Return updated field
    from app.models.user import User
    user = db.query(User).filter(User.id == current_user.user_id).first()
    
    return DossierFieldItem(
        field_key=field.field_key,
        field_value=field.field_value,
        source_document_id=str(field.source_document_id) if field.source_document_id else None,
        source_page_number=field.source_page_number,
        source_snippet=body.evidence.get("snippet_json") if body.evidence else None,
        last_edited_by=user.email if user else None,
        last_edited_at=datetime.utcnow(),
        needs_confirmation=field.needs_confirmation,
    )


@router.post("/{case_id}/dossier/fields/{field_key}/link-evidence")
async def link_dossier_field_evidence(
    request: Request,
    case_id: uuid.UUID,
    field_key: str,
    body: dict,  # {document_id, page_number} OR {snippet_json}
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link evidence to a dossier field (document+page or snippet)."""
    # Verify case exists
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get field
    field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == field_key,
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    old_value = field.field_value
    
    # Update evidence pointers
    if "document_id" in body and "page_number" in body:
        field.source_document_id = uuid.UUID(body["document_id"])
        field.source_page_number = body["page_number"]
    
    db.commit()
    db.refresh(field)
    
    # Write history entry
    history_entry = DossierFieldHistory(
        org_id=current_user.org_id,
        case_id=case_id,
        field_key=field_key,
        old_value=old_value,
        new_value=field.field_value,  # Value unchanged, only evidence
        edited_by_user_id=current_user.user_id,
        edited_at=datetime.utcnow(),
        source_type="manual",
        source_document_id=field.source_document_id,
        source_page_number=field.source_page_number,
        source_snippet=body.get("snippet_json"),
    )
    db.add(history_entry)
    db.commit()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.field_source_set",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "field_key": field_key,
            "document_id": str(field.source_document_id) if field.source_document_id else None,
            "page_number": field.source_page_number,
        },
    )
    
    return {"status": "success", "message": "Evidence linked"}


@router.get("/{case_id}/dossier/fields/{field_key}/history", response_model=DossierFieldHistoryResponse)
async def get_dossier_field_history(
    request: Request,
    case_id: uuid.UUID,
    field_key: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get edit history for a dossier field."""
    # Verify case exists
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get history entries
    history_entries = db.query(DossierFieldHistory).filter(
        DossierFieldHistory.case_id == case_id,
        DossierFieldHistory.org_id == current_user.org_id,
        DossierFieldHistory.field_key == field_key,
    ).order_by(DossierFieldHistory.edited_at.desc()).all()
    
    # Get user emails
    from app.models.user import User
    user_ids = {h.edited_by_user_id for h in history_entries}
    users = {str(u.id): u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    
    history_items = []
    for entry in history_entries:
        history_items.append(DossierFieldHistoryItem(
            id=str(entry.id),
            old_value=entry.old_value,
            new_value=entry.new_value,
            edited_by=users.get(str(entry.edited_by_user_id), "Unknown"),
            edited_at=entry.edited_at,
            source_type=entry.source_type,
            source_document_id=str(entry.source_document_id) if entry.source_document_id else None,
            source_page_number=entry.source_page_number,
            note=entry.note,
        ))
    
    return DossierFieldHistoryResponse(
        field_key=field_key,
        history=history_items,
    )

