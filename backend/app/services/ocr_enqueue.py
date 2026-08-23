"""Enqueue OCR without going through the HTTP layer."""
from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentPage
from app.services.audit import write_audit_event
from app.workers.tasks_ocr import process_document_ocr

IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/tif"}


def enqueue_ocr_for_document(
    db: Session,
    *,
    document: Document,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    force: bool = False,
) -> str | None:
    if document.status not in {"Split", "Uploaded"}:
        return None
    page_count = (
        db.query(func.count(DocumentPage.id))
        .filter(DocumentPage.document_id == document.id, DocumentPage.org_id == org_id)
        .scalar()
        or 0
    )
    if page_count == 0:
        return None

    document.status = "Queued"
    db.query(DocumentPage).filter(
        DocumentPage.document_id == document.id,
        DocumentPage.org_id == org_id,
    ).update(
        {DocumentPage.ocr_status: "Queued", DocumentPage.ocr_error: None},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(document)

    task = process_document_ocr.apply_async(
        args=[str(document.id), str(org_id), str(user_id)],
        kwargs={"force": force},
    )
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=user_id,
        action="document.ocr_enqueued",
        entity_type="document",
        entity_id=document.id,
        case_id=document.case_id,
        event_metadata={
            "document_id": str(document.id),
            "task_id": task.id,
            "force": force,
            "auto": True,
            "page_count": page_count,
        },
    )
    return task.id
