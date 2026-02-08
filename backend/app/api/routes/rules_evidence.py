"""Evidence attachment endpoints for exceptions and CPs."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef
from app.models.cp_evidence import CPEvidenceRef
from app.models.document import Document
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(tags=["rules"])


class EvidenceAttachRequest(BaseModel):
    document_id: str
    page_number: int
    note: Optional[str] = None


class EvidenceSnippetRequest(BaseModel):
    document_id: str
    page_number: int
    snippet: str  # OCR text snippet


class EvidenceRefResponse(BaseModel):
    id: str
    document_id: Optional[str]
    page_number: Optional[int]
    note: Optional[str]


@router.post("/exceptions/{exception_id}/evidence", response_model=EvidenceRefResponse)
async def attach_exception_evidence(
    request: Request,
    exception_id: uuid.UUID,
    body: EvidenceAttachRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach evidence (document+page) to an exception."""
    # Validate exception
    exc = db.query(Exception_).filter(
        Exception_.id == exception_id,
        Exception_.org_id == current_user.org_id,
    ).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    # Validate document belongs to same case and org
    doc = db.query(Document).filter(
        Document.id == uuid.UUID(body.document_id),
        Document.org_id == current_user.org_id,
        Document.case_id == exc.case_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Create evidence ref
    evidence_ref = ExceptionEvidenceRef(
        org_id=current_user.org_id,
        exception_id=exception_id,
        document_id=uuid.UUID(body.document_id),
        page_number=body.page_number,
        note=body.note,
    )
    db.add(evidence_ref)
    db.commit()
    db.refresh(evidence_ref)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="exception.evidence_attach",
        entity_type="exception_evidence_ref",
        entity_id=evidence_ref.id,
        event_metadata={
            "exception_id": str(exception_id),
            "document_id": body.document_id,
            "page_number": body.page_number,
        },
    )
    
    return EvidenceRefResponse(
        id=str(evidence_ref.id),
        document_id=body.document_id,
        page_number=body.page_number,
        note=body.note,
    )


@router.post("/cps/{cp_id}/evidence", response_model=EvidenceRefResponse)
async def attach_cp_evidence(
    request: Request,
    cp_id: uuid.UUID,
    body: EvidenceAttachRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach evidence (document+page) to a CP."""
    # Validate CP
    cp = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.id == cp_id,
        ConditionPrecedent.org_id == current_user.org_id,
    ).first()
    if not cp:
        raise HTTPException(status_code=404, detail="CP not found")
    
    # Validate document belongs to same case and org
    doc = db.query(Document).filter(
        Document.id == uuid.UUID(body.document_id),
        Document.org_id == current_user.org_id,
        Document.case_id == cp.case_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Create evidence ref
    evidence_ref = CPEvidenceRef(
        org_id=current_user.org_id,
        cp_id=cp_id,
        document_id=uuid.UUID(body.document_id),
        page_number=body.page_number,
        note=body.note,
        created_by_user_id=current_user.user_id,
    )
    db.add(evidence_ref)
    db.commit()
    db.refresh(evidence_ref)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="cp.evidence_attach",
        entity_type="cp_evidence_ref",
        entity_id=evidence_ref.id,
        event_metadata={
            "cp_id": str(cp_id),
            "document_id": body.document_id,
            "page_number": body.page_number,
        },
    )
    
    return EvidenceRefResponse(
        id=str(evidence_ref.id),
        document_id=body.document_id,
        page_number=body.page_number,
        note=body.note,
    )

