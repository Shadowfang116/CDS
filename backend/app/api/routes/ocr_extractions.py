"""OCR Extraction Candidates API endpoints for editable OCR extractions."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document, CaseDossierField
from app.models.ocr_extraction import OCRExtractionCandidate
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.extractors.validators import get_field_validator, is_probably_name_line, is_probably_name_line

router = APIRouter(tags=["ocr-extractions"])


class OCRExtractionItemResponse(BaseModel):
    id: str
    field_key: str
    proposed_value: str
    edited_value: Optional[str]
    final_value: Optional[str]
    status: str
    confidence: Optional[float]
    document_id: str
    document_name: str
    page_number: int
    snippet: Optional[str]
    updated_at: datetime
    # P10: Quality fields
    is_low_quality: Optional[bool] = False
    quality_level: Optional[str] = None
    warning_reason: Optional[str] = None
    # P15: Manual override fields
    is_overridden: Optional[bool] = False
    override_note: Optional[str] = None
    # P16: HF Extractor fields
    extraction_method: Optional[str] = None
    evidence_json: Optional[dict] = None
    
    class Config:
        from_attributes = True


class OCRExtractionsResponse(BaseModel):
    case_id: str
    counts: dict
    items: List[OCRExtractionItemResponse]


class OCRExtractionEditRequest(BaseModel):
    edited_value: Optional[str] = None


class OCRExtractionConfirmRequest(BaseModel):
    target: Optional[str] = "dossier"  # dossier | party | custom
    field_path: Optional[str] = None  # If provided, use this; else infer from field_key
    force_confirm: Optional[bool] = False  # P10: Required if is_low_quality is True
    force_format: Optional[bool] = False  # P14: Allow invalid format (Admin only)


class OCRExtractionRejectRequest(BaseModel):
    reason: str


class OCRExtractionOverrideRequest(BaseModel):
    value_override: str
    override_note: Optional[str] = None


@router.get("/cases/{case_id}/ocr-extractions", response_model=OCRExtractionsResponse)
async def list_ocr_extractions(
    case_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter by status: pending, confirmed, rejected"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List OCR extraction candidates for a case."""
    # Verify case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # RBAC: Admin and Reviewer can view
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Build query
    query = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.case_id == case_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    )
    
    if status:
        query = query.filter(OCRExtractionCandidate.status == status.capitalize())
    
    candidates = query.order_by(OCRExtractionCandidate.created_at.desc()).all()
    
    # Get document names
    doc_ids = {str(c.document_id) for c in candidates}
    documents = {str(d.id): d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
    
    # Build response
    items = []
    counts = {"pending": 0, "confirmed": 0, "rejected": 0}
    
    for c in candidates:
        doc = documents.get(str(c.document_id))
        doc_name = doc.original_filename if doc else "Unknown"
        
        status_lower = c.status.lower()
        if status_lower in counts:
            counts[status_lower] += 1
        
        items.append(OCRExtractionItemResponse(
            id=str(c.id),
            field_key=c.field_key,
            proposed_value=c.proposed_value,
            edited_value=c.edited_value,
            final_value=c.final_value,
            status=c.status,
            confidence=float(c.confidence) if c.confidence else None,
            document_id=str(c.document_id),
            document_name=doc_name,
            page_number=c.page_number,
            snippet=c.snippet,
            updated_at=c.updated_at,
            is_low_quality=c.is_low_quality if hasattr(c, 'is_low_quality') else False,
            quality_level=c.quality_level_at_create if hasattr(c, 'quality_level_at_create') else None,
            warning_reason=c.warning_reason if hasattr(c, 'warning_reason') else None,
            is_overridden=c.overridden_by_user_id is not None if hasattr(c, 'overridden_by_user_id') else False,
            override_note=c.override_note if hasattr(c, 'override_note') else None,
            extraction_method=c.extraction_method if hasattr(c, 'extraction_method') else None,
            evidence_json=c.evidence_json if hasattr(c, 'evidence_json') else None,
        ))
    
    # Audit
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr_extraction.list",
        entity_type="case",
        entity_id=case_id,
    )
    
    return OCRExtractionsResponse(
        case_id=str(case_id),
        counts=counts,
        items=items,
    )


@router.patch("/ocr-extractions/{extraction_id}", response_model=OCRExtractionItemResponse)
async def edit_ocr_extraction(
    extraction_id: uuid.UUID,
    body: OCRExtractionEditRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit an OCR extraction candidate (only if status is Pending)."""
    # RBAC: Admin and Reviewer can edit
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    candidate = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Extraction candidate not found")
    
    if candidate.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending extractions can be edited")
    
    # Update edited_value (trim and normalize whitespace)
    if body.edited_value is not None:
        candidate.edited_value = body.edited_value.strip() if body.edited_value else None
    else:
        candidate.edited_value = None
    
    candidate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(candidate)
    
    # Get document name
    doc = db.query(Document).filter(Document.id == candidate.document_id).first()
    doc_name = doc.original_filename if doc else "Unknown"
    
    # Audit
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr_extraction.edited",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata={"field_key": candidate.field_key, "edited_value": candidate.edited_value},
    )
    
    return OCRExtractionItemResponse(
        id=str(candidate.id),
        field_key=candidate.field_key,
        proposed_value=candidate.proposed_value,
        edited_value=candidate.edited_value,
        final_value=candidate.final_value,
        status=candidate.status,
        confidence=float(candidate.confidence) if candidate.confidence else None,
        document_id=str(candidate.document_id),
        document_name=doc_name,
        page_number=candidate.page_number,
        snippet=candidate.snippet,
        updated_at=candidate.updated_at,
        is_low_quality=candidate.is_low_quality if hasattr(candidate, 'is_low_quality') else False,
        quality_level=candidate.quality_level_at_create if hasattr(candidate, 'quality_level_at_create') else None,
        warning_reason=candidate.warning_reason if hasattr(candidate, 'warning_reason') else None,
        is_overridden=candidate.overridden_by_user_id is not None if hasattr(candidate, 'overridden_by_user_id') else False,
        override_note=candidate.override_note if hasattr(candidate, 'override_note') else None,
        extraction_method=candidate.extraction_method if hasattr(candidate, 'extraction_method') else None,
        evidence_json=candidate.evidence_json if hasattr(candidate, 'evidence_json') else None,
    )


@router.post("/ocr-extractions/{extraction_id}/confirm", response_model=OCRExtractionItemResponse)
async def confirm_ocr_extraction(
    extraction_id: uuid.UUID,
    body: OCRExtractionConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm an OCR extraction candidate and write to dossier/party."""
    # RBAC: Admin and Reviewer can confirm
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    candidate = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Extraction candidate not found")
    
    if candidate.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending extractions can be confirmed")
    
    # P10: Quality gate enforcement
    if candidate.is_low_quality and not body.force_confirm:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm low-quality extraction without force_confirm flag. Quality: {candidate.quality_level_at_create or 'Low'}. Reason: {candidate.warning_reason or 'Low OCR quality detected'}"
        )
    
    # Compute final_value
    final_value = candidate.edited_value if candidate.edited_value else candidate.proposed_value
    final_value = final_value.strip() if final_value else None
    
    if not final_value:
        raise HTTPException(status_code=400, detail="Final value cannot be empty")
    
    # P14: Validate field format (unless force_format=true and Admin)
    validator = get_field_validator(candidate.field_key)
    if validator:
        validation_passed = True
        validation_error = None
        
        if validator == is_probably_name_line:
            is_valid, warning = validator(final_value)
            validation_passed = is_valid
            validation_error = warning if not is_valid else None
        else:
            is_valid, normalized, warning = validator(final_value)
            validation_passed = is_valid
            if is_valid and normalized:
                final_value = normalized  # Use normalized value
            validation_error = warning if not is_valid else None
        
        if not validation_passed:
            if not body.force_format:
                raise HTTPException(
                    status_code=400,
                    detail=f"Value does not match expected format for field '{candidate.field_key}': {validation_error}. Set force_format=true to override (Admin only)."
                )
            
            # P14: force_format only allowed for Admin
            if current_user.role != "Admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin can use force_format to confirm invalid field format"
                )
    
    candidate.final_value = final_value
    candidate.status = "Confirmed"
    candidate.confirmed_by_user_id = current_user.user_id
    candidate.confirmed_at = datetime.utcnow()
    candidate.updated_at = datetime.utcnow()
    
    # Determine target field path
    field_path = body.field_path if body.field_path else candidate.field_key
    
    # Write to CaseDossierField
    existing_field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == candidate.case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == field_path,
    ).first()
    
    if existing_field:
        existing_field.field_value = final_value
        existing_field.source_document_id = candidate.document_id
        existing_field.source_page_number = candidate.page_number
        existing_field.confidence = candidate.confidence
        existing_field.needs_confirmation = False
        existing_field.confirmed_by_user_id = current_user.user_id
        existing_field.confirmed_at = datetime.utcnow()
        existing_field.updated_at = datetime.utcnow()
    else:
        new_field = CaseDossierField(
            org_id=current_user.org_id,
            case_id=candidate.case_id,
            field_key=field_path,
            field_value=final_value,
            source_document_id=candidate.document_id,
            source_page_number=candidate.page_number,
            confidence=candidate.confidence,
            needs_confirmation=False,
            confirmed_by_user_id=current_user.user_id,
            confirmed_at=datetime.utcnow(),
        )
        db.add(new_field)
    
    db.commit()
    db.refresh(candidate)
    
    # Get document name
    doc = db.query(Document).filter(Document.id == candidate.document_id).first()
    doc_name = doc.original_filename if doc else "Unknown"
    
    # Audit
    audit_metadata = {
        "field_key": candidate.field_key,
        "field_path": field_path,
        "final_value": final_value,
        "target": body.target,
    }
    
    # P10: Log force_confirm if used
    if candidate.is_low_quality and body.force_confirm:
        audit_metadata["force_confirm"] = True
        audit_metadata["quality_level"] = candidate.quality_level_at_create
        audit_metadata["warning_reason"] = candidate.warning_reason
        write_audit_event(
            db=db,
            org_id=current_user.org_id,
            actor_user_id=current_user.user_id,
            action="ocr.extraction_force_confirm",
            entity_type="ocr_extraction",
            entity_id=extraction_id,
            event_metadata=audit_metadata,
        )
    
    # P14: Log force_format if used
    if body.force_format:
        write_audit_event(
            db=db,
            org_id=current_user.org_id,
            actor_user_id=current_user.user_id,
            action="ocr.extraction_force_format",
            entity_type="ocr_extraction",
            entity_id=extraction_id,
            event_metadata={
                "field_key": candidate.field_key,
                "final_value": final_value,
                "force_format": True,
            },
        )
    
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr_extraction.confirmed",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata=audit_metadata,
    )
    
    # Also emit dossier field source audit
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.field_source_set",
        entity_type="case",
        entity_id=candidate.case_id,
        event_metadata={"field_key": field_path, "document_id": str(candidate.document_id), "page_number": candidate.page_number},
    )
    
    return OCRExtractionItemResponse(
        id=str(candidate.id),
        field_key=candidate.field_key,
        proposed_value=candidate.proposed_value,
        edited_value=candidate.edited_value,
        final_value=candidate.final_value,
        status=candidate.status,
        confidence=float(candidate.confidence) if candidate.confidence else None,
        document_id=str(candidate.document_id),
        document_name=doc_name,
        page_number=candidate.page_number,
        snippet=candidate.snippet,
        updated_at=candidate.updated_at,
        is_low_quality=candidate.is_low_quality if hasattr(candidate, 'is_low_quality') else False,
        quality_level=candidate.quality_level_at_create if hasattr(candidate, 'quality_level_at_create') else None,
        warning_reason=candidate.warning_reason if hasattr(candidate, 'warning_reason') else None,
        is_overridden=candidate.overridden_by_user_id is not None if hasattr(candidate, 'overridden_by_user_id') else False,
        override_note=candidate.override_note if hasattr(candidate, 'override_note') else None,
        extraction_method=candidate.extraction_method if hasattr(candidate, 'extraction_method') else None,
        evidence_json=candidate.evidence_json if hasattr(candidate, 'evidence_json') else None,
    )


@router.post("/ocr-extractions/{extraction_id}/reject", response_model=OCRExtractionItemResponse)
async def reject_ocr_extraction(
    extraction_id: uuid.UUID,
    body: OCRExtractionRejectRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject an OCR extraction candidate."""
    # RBAC: Admin and Reviewer can reject
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    candidate = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Extraction candidate not found")
    
    if candidate.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending extractions can be rejected")
    
    candidate.status = "Rejected"
    candidate.rejected_by_user_id = current_user.user_id
    candidate.rejected_at = datetime.utcnow()
    candidate.rejection_reason = body.reason.strip()
    candidate.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(candidate)
    
    # Get document name
    doc = db.query(Document).filter(Document.id == candidate.document_id).first()
    doc_name = doc.original_filename if doc else "Unknown"
    
    # Audit
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr_extraction.rejected",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata={"field_key": candidate.field_key, "reason": body.reason},
    )
    
    return OCRExtractionItemResponse(
        id=str(candidate.id),
        field_key=candidate.field_key,
        proposed_value=candidate.proposed_value,
        edited_value=candidate.edited_value,
        final_value=candidate.final_value,
        status=candidate.status,
        confidence=float(candidate.confidence) if candidate.confidence else None,
        document_id=str(candidate.document_id),
        document_name=doc_name,
        page_number=candidate.page_number,
        snippet=candidate.snippet,
        updated_at=candidate.updated_at,
        is_low_quality=candidate.is_low_quality if hasattr(candidate, 'is_low_quality') else False,
        quality_level=candidate.quality_level_at_create if hasattr(candidate, 'quality_level_at_create') else None,
        warning_reason=candidate.warning_reason if hasattr(candidate, 'warning_reason') else None,
        is_overridden=candidate.overridden_by_user_id is not None if hasattr(candidate, 'overridden_by_user_id') else False,
        override_note=candidate.override_note if hasattr(candidate, 'override_note') else None,
        extraction_method=candidate.extraction_method if hasattr(candidate, 'extraction_method') else None,
        evidence_json=candidate.evidence_json if hasattr(candidate, 'evidence_json') else None,
    )


@router.patch("/ocr-extractions/{extraction_id}/override", response_model=OCRExtractionItemResponse)
async def override_ocr_extraction(
    extraction_id: uuid.UUID,
    body: OCRExtractionOverrideRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually override an OCR extraction value (bank-ready audit trail)."""
    # RBAC: Admin and Reviewer can override
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    candidate = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Extraction candidate not found")
    
    if candidate.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending extractions can be overridden")
    
    # Store old value for audit
    old_value = candidate.edited_value if candidate.edited_value else candidate.proposed_value
    
    # Set override values
    candidate.edited_value = body.value_override.strip() if body.value_override else None
    candidate.overridden_by_user_id = current_user.user_id
    candidate.overridden_at = datetime.utcnow()
    candidate.override_note = body.override_note.strip() if body.override_note else None
    candidate.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(candidate)
    
    # Get document name
    doc = db.query(Document).filter(Document.id == candidate.document_id).first()
    doc_name = doc.original_filename if doc else "Unknown"
    
    # Audit: Record override with full metadata
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr_extraction.manual_override",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata={
            "field_key": candidate.field_key,
            "old_value": old_value,
            "new_value": body.value_override,
            "override_note": body.override_note,
            "proposed_value": candidate.proposed_value,
        },
    )
    
    return OCRExtractionItemResponse(
        id=str(candidate.id),
        field_key=candidate.field_key,
        proposed_value=candidate.proposed_value,
        edited_value=candidate.edited_value,
        final_value=candidate.final_value,
        status=candidate.status,
        confidence=float(candidate.confidence) if candidate.confidence else None,
        document_id=str(candidate.document_id),
        document_name=doc_name,
        page_number=candidate.page_number,
        snippet=candidate.snippet,
        updated_at=candidate.updated_at,
        is_low_quality=candidate.is_low_quality if hasattr(candidate, 'is_low_quality') else False,
        quality_level=candidate.quality_level_at_create if hasattr(candidate, 'quality_level_at_create') else None,
        warning_reason=candidate.warning_reason if hasattr(candidate, 'warning_reason') else None,
        is_overridden=candidate.overridden_by_user_id is not None if hasattr(candidate, 'overridden_by_user_id') else False,
        override_note=candidate.override_note if hasattr(candidate, 'override_note') else None,
        extraction_method=candidate.extraction_method if hasattr(candidate, 'extraction_method') else None,
        evidence_json=candidate.evidence_json if hasattr(candidate, 'evidence_json') else None,
    )

