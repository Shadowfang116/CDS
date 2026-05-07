"""Per-page OCR correction endpoints."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_reviewer, require_viewer
from app.db.session import get_db
from app.models.document import Document, DocumentPage
from app.services.audit import log_request_event

router = APIRouter(tags=["ocr"])


class OCRTextCorrectionRequest(BaseModel):
    corrected_text: str = Field(..., min_length=1)
    note: str = Field(..., min_length=5)


class OCRTextCorrectionResponse(BaseModel):
    document_id: str
    page_number: int
    corrected_text: str | None
    note: str | None = None
    corrected_by_user_id: str | None
    corrected_at: str | None


def _get_page_or_404(
    db: Session,
    *,
    document_id: uuid.UUID,
    page_number: int,
    org_id: uuid.UUID,
) -> tuple[Document, DocumentPage]:
    document = db.query(Document).filter(Document.id == document_id, Document.org_id == org_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    page = (
        db.query(DocumentPage)
        .filter(
            DocumentPage.document_id == document_id,
            DocumentPage.org_id == org_id,
            DocumentPage.page_number == page_number,
        )
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return document, page


@router.get("/documents/{document_id}/pages/{page_number}/ocr-text/correction", response_model=OCRTextCorrectionResponse)
async def get_ocr_text_correction(
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _document, page = _get_page_or_404(
        db,
        document_id=document_id,
        page_number=page_number,
        org_id=current_user.org_id,
    )
    if not page.corrected_text:
        raise HTTPException(status_code=404, detail="OCR text correction not found")
    return OCRTextCorrectionResponse(
        document_id=str(document_id),
        page_number=page_number,
        corrected_text=page.corrected_text,
        corrected_by_user_id=str(page.corrected_by_user_id) if page.corrected_by_user_id else None,
        corrected_at=page.corrected_at.isoformat() if page.corrected_at else None,
    )


@router.put("/documents/{document_id}/pages/{page_number}/correction", response_model=OCRTextCorrectionResponse)
@router.api_route("/documents/{document_id}/pages/{page_number}/ocr-text/correction", methods=["PUT", "POST"], response_model=OCRTextCorrectionResponse)
async def upsert_ocr_text_correction(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    body: OCRTextCorrectionRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    document, page = _get_page_or_404(
        db,
        document_id=document_id,
        page_number=page_number,
        org_id=current_user.org_id,
    )
    before_json = {
        "corrected_text": page.corrected_text,
        "corrected_by_user_id": str(page.corrected_by_user_id) if page.corrected_by_user_id else None,
        "corrected_at": page.corrected_at.isoformat() if page.corrected_at else None,
    }
    page.corrected_text = body.corrected_text
    page.corrected_by_user_id = current_user.user_id
    page.corrected_at = datetime.utcnow()
    db.commit()
    db.refresh(page)

    log_request_event(
        db,
        request=request,
        action="ocr.text_corrected",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="document_page",
        entity_id=page.id,
        case_id=document.case_id,
        before_json=before_json,
        after_json={
            "document_id": str(document_id),
            "page_number": page_number,
            "corrected_text_length": len(body.corrected_text),
            "note": body.note,
        },
    )

    return OCRTextCorrectionResponse(
        document_id=str(document_id),
        page_number=page_number,
        corrected_text=page.corrected_text,
        note=body.note,
        corrected_by_user_id=str(page.corrected_by_user_id) if page.corrected_by_user_id else None,
        corrected_at=page.corrected_at.isoformat() if page.corrected_at else None,
    )


@router.delete("/documents/{document_id}/pages/{page_number}/ocr-text/correction")
async def delete_ocr_text_correction(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    document, page = _get_page_or_404(
        db,
        document_id=document_id,
        page_number=page_number,
        org_id=current_user.org_id,
    )
    if not page.corrected_text:
        raise HTTPException(status_code=404, detail="OCR text correction not found")

    before_json = {
        "corrected_text": page.corrected_text,
        "corrected_by_user_id": str(page.corrected_by_user_id) if page.corrected_by_user_id else None,
        "corrected_at": page.corrected_at.isoformat() if page.corrected_at else None,
    }
    page.corrected_text = None
    page.corrected_by_user_id = None
    page.corrected_at = None
    db.commit()

    log_request_event(
        db,
        request=request,
        action="ocr.text_correction_deleted",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="document_page",
        entity_id=page.id,
        case_id=document.case_id,
        before_json=before_json,
        after_json={"document_id": str(document_id), "page_number": page_number},
    )
    return {"message": "OCR text correction deleted"}
