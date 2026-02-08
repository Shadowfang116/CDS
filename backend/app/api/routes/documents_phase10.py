"""Phase 10: Additional document endpoints for thumbnails and OCR text."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentPage
from app.models.ocr_text_correction import OCRTextCorrection
from app.api.deps import get_current_user, CurrentUser
from app.services.storage import get_presigned_get_url
from app.services.thumbnails import ensure_thumbnail_exists
from app.services.audit import write_audit_event
from app.schemas.document import PresignedUrlResponse

router = APIRouter(tags=["documents"])

DOWNLOAD_URL_EXPIRES_SECONDS = 3600


@router.get("/documents/{document_id}/pages/{page_number}/thumbnail", response_model=PresignedUrlResponse)
async def get_page_thumbnail(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download a page thumbnail. Generates thumbnail if missing."""
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
    
    # Generate thumbnail key if not set
    if not page.minio_key_thumbnail:
        thumbnail_key = f"org/{current_user.org_id}/cases/{document.case_id}/docs/{document_id}/pages/{page_number}/thumbnail.png"
        try:
            ensure_thumbnail_exists(page.minio_key_page_pdf, thumbnail_key)
            page.minio_key_thumbnail = thumbnail_key
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {str(e)}")
    
    url = get_presigned_get_url(page.minio_key_thumbnail, DOWNLOAD_URL_EXPIRES_SECONDS)
    return PresignedUrlResponse(url=url, expires_in_seconds=DOWNLOAD_URL_EXPIRES_SECONDS)


@router.get("/documents/{document_id}/pages/{page_number}/ocr-text")
async def get_page_ocr_text(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    mode: str = Query("effective", regex="^(effective|raw|corrected)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get OCR text for a page. P14: Supports corrections overlay."""
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
    
    # P14: Get correction if exists
    correction = db.query(OCRTextCorrection).filter(
        OCRTextCorrection.org_id == current_user.org_id,
        OCRTextCorrection.document_id == document_id,
        OCRTextCorrection.page_number == page_number,
    ).first()
    
    raw_text = page.ocr_text or ""
    corrected_text = correction.corrected_text if correction else None
    has_correction = correction is not None
    
    # Determine effective text based on mode
    if mode == "raw":
        effective_text = raw_text
    elif mode == "corrected":
        effective_text = corrected_text if corrected_text is not None else raw_text
    else:  # effective (default)
        effective_text = corrected_text if corrected_text is not None else raw_text
    
    result = {
        "page_number": page.page_number,
        "raw_text": raw_text,
        "effective_text": effective_text,
        "ocr_status": page.ocr_status,
        "ocr_confidence": float(page.ocr_confidence) if page.ocr_confidence else None,
        "has_correction": has_correction,
    }
    
    if has_correction:
        result["corrected_text"] = corrected_text
        result["correction_note"] = correction.note
        result["corrected_at"] = correction.created_at.isoformat() if correction.created_at else None
        # Get user email if available
        from app.models.user import User
        user = db.query(User).filter(User.id == correction.created_by_user_id).first()
        result["corrected_by_email"] = user.email if user else None
    else:
        result["corrected_text"] = None
        result["correction_note"] = None
        result["corrected_at"] = None
        result["corrected_by_email"] = None
    
    return result

