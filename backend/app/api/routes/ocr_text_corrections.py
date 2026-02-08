"""P14: OCR text corrections API."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentPage
from app.models.ocr_text_correction import OCRTextCorrection
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(tags=["ocr"])


class OCRTextCorrectionRequest(BaseModel):
    corrected_text: str = Field(..., min_length=1, description="Corrected OCR text")
    note: str = Field(..., min_length=5, description="Note explaining the correction (required, min 5 chars)")


class OCRTextCorrectionResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    corrected_text: str
    note: str | None
    created_by_user_id: str
    created_at: str
    updated_at: str


@router.get("/documents/{document_id}/pages/{page_number}/ocr-text/correction", response_model=OCRTextCorrectionResponse)
async def get_ocr_text_correction(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get OCR text correction for a page (if exists).
    RBAC: Any authenticated user can read corrections.
    """
    # Validate document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find correction
    correction = db.query(OCRTextCorrection).filter(
        OCRTextCorrection.org_id == current_user.org_id,
        OCRTextCorrection.document_id == document_id,
        OCRTextCorrection.page_number == page_number,
    ).first()
    
    if not correction:
        raise HTTPException(status_code=404, detail="OCR text correction not found")
    
    return OCRTextCorrectionResponse(
        id=str(correction.id),
        document_id=str(correction.document_id),
        page_number=correction.page_number,
        corrected_text=correction.corrected_text,
        note=correction.note,
        created_by_user_id=str(correction.created_by_user_id),
        created_at=correction.created_at.isoformat(),
        updated_at=correction.updated_at.isoformat(),
    )


@router.api_route("/documents/{document_id}/pages/{page_number}/ocr-text/correction", methods=["PUT", "POST"], response_model=OCRTextCorrectionResponse)
async def upsert_ocr_text_correction(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    body: OCRTextCorrectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create or update OCR text correction for a page.
    RBAC: Admin or Reviewer only.
    """
    # RBAC: Only Admin or Reviewer can correct OCR
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Reviewer can correct OCR text"
        )
    
    # Validate document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Validate page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
        DocumentPage.page_number == page_number,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Check if correction exists
    correction = db.query(OCRTextCorrection).filter(
        OCRTextCorrection.org_id == current_user.org_id,
        OCRTextCorrection.document_id == document_id,
        OCRTextCorrection.page_number == page_number,
    ).first()
    
    if correction:
        # Update existing
        correction.corrected_text = body.corrected_text
        correction.note = body.note
        correction.updated_at = datetime.utcnow()
    else:
        # Create new
        correction = OCRTextCorrection(
            org_id=current_user.org_id,
            document_id=document_id,
            page_number=page_number,
            corrected_text=body.corrected_text,
            note=body.note,
            created_by_user_id=current_user.user_id,
        )
        db.add(correction)
    
    db.commit()
    db.refresh(correction)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.text_corrected",
        entity_type="ocr_text_correction",
        entity_id=correction.id,
        event_metadata={
            "document_id": str(document_id),
            "page_number": page_number,
            "note_length": len(body.note),
            "corrected_text_length": len(body.corrected_text),
            "raw_text_length": len(page.ocr_text) if page.ocr_text else 0,
        },
    )
    
    return OCRTextCorrectionResponse(
        id=str(correction.id),
        document_id=str(correction.document_id),
        page_number=correction.page_number,
        corrected_text=correction.corrected_text,
        note=correction.note,
        created_by_user_id=str(correction.created_by_user_id),
        created_at=correction.created_at.isoformat(),
        updated_at=correction.updated_at.isoformat(),
    )


@router.delete("/documents/{document_id}/pages/{page_number}/ocr-text/correction")
async def delete_ocr_text_correction(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete OCR text correction for a page (revert to raw OCR).
    RBAC: Admin or Reviewer only.
    """
    # RBAC: Only Admin or Reviewer can delete corrections
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Reviewer can delete OCR text corrections"
        )
    
    # Validate document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find correction
    correction = db.query(OCRTextCorrection).filter(
        OCRTextCorrection.org_id == current_user.org_id,
        OCRTextCorrection.document_id == document_id,
        OCRTextCorrection.page_number == page_number,
    ).first()
    
    if not correction:
        raise HTTPException(status_code=404, detail="OCR text correction not found")
    
    correction_id = correction.id
    
    # Delete
    db.delete(correction)
    db.commit()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.text_correction_deleted",
        entity_type="ocr_text_correction",
        entity_id=str(correction_id),
        event_metadata={
            "document_id": str(document_id),
            "page_number": page_number,
        },
    )
    
    return {"message": "OCR text correction deleted"}

