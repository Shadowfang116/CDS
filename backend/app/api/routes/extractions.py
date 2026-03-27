"""Extraction review/verification endpoints (bank-ready)."""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.models.case import Case
from app.models.document import Document, CaseDossierField
from app.models.ocr_extraction import OCRExtractionCandidate
from app.services.extractions import compute_needs_review, get_field_value
from app.services.audit import write_audit_event

router = APIRouter(tags=["extractions"])


class ExtractionItem(BaseModel):
    id: str
    field_name: str
    value: Optional[str]
    extracted_value: Optional[str]
    corrected_value: Optional[str]
    confidence: Optional[float]
    document_id: str
    page_number: int
    status: str  # extracted | reviewed | verified
    needs_review: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class ExtractionListResponse(BaseModel):
    case_id: str
    items: List[ExtractionItem]


class ExtractionUpdateRequest(BaseModel):
    corrected_value: str


@router.get("/cases/{case_id}/extractions", response_model=ExtractionListResponse)
async def list_extractions(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify case
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == current_user.org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # RBAC
    if current_user.role not in ["Admin", "Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Load candidates
    candidates = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.case_id == case_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).order_by(OCRExtractionCandidate.updated_at.desc()).all()

    # Map document names/ids (if needed)
    doc_ids = {str(c.document_id) for c in candidates}
    docs = {str(d.id): d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    items: List[ExtractionItem] = []
    for c in candidates:
        # Compute needs_review if not set (for backward compatibility)
        needs = bool(c.needs_review)
        if needs is False:
            try:
                needs = compute_needs_review(float(c.confidence) if c.confidence is not None else None, getattr(c, 'is_low_quality', False))
            except Exception:
                needs = True
        value = get_field_value(c.proposed_value, c.edited_value, c.final_value)
        items.append(ExtractionItem(
            id=str(c.id),
            field_name=c.field_key,
            value=value,
            extracted_value=c.proposed_value,
            corrected_value=c.edited_value or c.final_value,
            confidence=float(c.confidence) if c.confidence is not None else None,
            document_id=str(c.document_id),
            page_number=c.page_number,
            status=c.review_status or "extracted",
            needs_review=needs,
            updated_at=c.updated_at,
        ))

    return ExtractionListResponse(case_id=str(case_id), items=items)


@router.patch("/extractions/{extraction_id}", response_model=ExtractionItem)
async def update_extraction(
    extraction_id: uuid.UUID,
    body: ExtractionUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    c = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Extraction not found")

    old_val = c.edited_value if c.edited_value else c.proposed_value
    c.edited_value = (body.corrected_value or "").strip()
    c.review_status = "reviewed"
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)

    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="extraction_corrected",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata={"field_key": c.field_key, "before": old_val, "after": c.edited_value, "case_id": str(c.case_id), "actor_role": current_user.role},
    )

    return ExtractionItem(
        id=str(c.id),
        field_name=c.field_key,
        value=get_field_value(c.proposed_value, c.edited_value, c.final_value),
        extracted_value=c.proposed_value,
        corrected_value=c.edited_value or c.final_value,
        confidence=float(c.confidence) if c.confidence is not None else None,
        document_id=str(c.document_id),
        page_number=c.page_number,
        status=c.review_status,
        needs_review=bool(c.needs_review),
        updated_at=c.updated_at,
    )


@router.patch("/extractions/{extraction_id}/verify", response_model=ExtractionItem)
async def verify_extraction(
    extraction_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["Admin", "Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    c = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.id == extraction_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Extraction not found")

    final_value = (c.edited_value or c.final_value or c.proposed_value or "").strip()
    if not final_value:
        raise HTTPException(status_code=400, detail="Final value cannot be empty")

    # Persist into dossier field
    field_path = c.field_key
    existing = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == c.case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == field_path,
    ).first()

    if existing:
        existing.field_value = final_value
        existing.source_document_id = c.document_id
        existing.source_page_number = c.page_number
        existing.confidence = c.confidence
        existing.needs_confirmation = False
        existing.confirmed_by_user_id = current_user.user_id
        existing.confirmed_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
    else:
        db.add(CaseDossierField(
            org_id=current_user.org_id,
            case_id=c.case_id,
            field_key=field_path,
            field_value=final_value,
            source_document_id=c.document_id,
            source_page_number=c.page_number,
            confidence=c.confidence,
            needs_confirmation=False,
            confirmed_by_user_id=current_user.user_id,
            confirmed_at=datetime.utcnow(),
        ))

    # Update candidate
    c.final_value = final_value
    c.status = "Confirmed"
    c.review_status = "verified"
    c.verified_by_user_id = current_user.user_id
    c.verified_at = datetime.utcnow()
    c.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(c)

    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="extraction_verified",
        entity_type="ocr_extraction",
        entity_id=extraction_id,
        event_metadata={"field_key": c.field_key, "final_value": final_value, "case_id": str(c.case_id), "actor_role": current_user.role},
    )

    return ExtractionItem(
        id=str(c.id),
        field_name=c.field_key,
        value=get_field_value(c.proposed_value, c.edited_value, c.final_value),
        extracted_value=c.proposed_value,
        corrected_value=c.edited_value or c.final_value,
        confidence=float(c.confidence) if c.confidence is not None else None,
        document_id=str(c.document_id),
        page_number=c.page_number,
        status=c.review_status,
        needs_review=bool(c.needs_review),
        updated_at=c.updated_at,
    )


@router.patch("/cases/{case_id}/extractions/verify")
async def bulk_verify_extractions(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["Admin", "Reviewer", "Approver"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    items = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.case_id == case_id,
        OCRExtractionCandidate.org_id == current_user.org_id,
        OCRExtractionCandidate.review_status.in_(["extracted", "reviewed"]),
    ).all()

    count = 0
    for c in items:
        final_value = (c.edited_value or c.final_value or c.proposed_value or "").strip()
        if not final_value:
            continue
        existing = db.query(CaseDossierField).filter(
            CaseDossierField.case_id == c.case_id,
            CaseDossierField.org_id == current_user.org_id,
            CaseDossierField.field_key == c.field_key,
        ).first()
        if existing:
            existing.field_value = final_value
            existing.source_document_id = c.document_id
            existing.source_page_number = c.page_number
            existing.confidence = c.confidence
            existing.needs_confirmation = False
            existing.confirmed_by_user_id = current_user.user_id
            existing.confirmed_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
        else:
            db.add(CaseDossierField(
                org_id=current_user.org_id,
                case_id=c.case_id,
                field_key=c.field_key,
                field_value=final_value,
                source_document_id=c.document_id,
                source_page_number=c.page_number,
                confidence=c.confidence,
                needs_confirmation=False,
                confirmed_by_user_id=current_user.user_id,
                confirmed_at=datetime.utcnow(),
            ))
        c.final_value = final_value
        c.status = "Confirmed"
        c.review_status = "verified"
        c.verified_by_user_id = current_user.user_id
        c.verified_at = datetime.utcnow()
        c.updated_at = datetime.utcnow()
        count += 1

    db.commit()

    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="extraction.bulk_verified",
        entity_type="case",
        entity_id=case_id,
        event_metadata={"verified_count": count},
    )

    return {"verified": count}



