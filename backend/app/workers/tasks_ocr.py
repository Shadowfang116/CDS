"""Celery tasks for OCR processing (stable, minimal logic).

Restores a valid implementation after a truncated file caused the worker to crash.
Each page is processed independently; failures do not abort the batch.
"""

import uuid
import logging
from datetime import datetime

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document, DocumentPage
from app.models.audit_log import AuditLog
from app.services.ocr import ocr_page_pdf, OCRError

logger = logging.getLogger(__name__)


def write_audit_event_sync(
    db,
    org_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event_metadata: dict | None = None,
) -> None:
    """Synchronous audit log writer for Celery tasks."""
    audit_entry = AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=event_metadata or {},
    )
    db.add(audit_entry)
    db.commit()


@celery_app.task(name="ocr.process_document", bind=True, max_retries=3)
def process_document_ocr(
    self,
    document_id: str,
    org_id: str,
    user_id: str,
    force: bool = False,
):
    """
    Process OCR for all pages of a document.

    - Skips pages already marked Done unless force=True
    - Updates per-page status and timestamps
    - Stores OCR text and confidence
    """
    document_uuid = uuid.UUID(document_id)
    org_uuid = uuid.UUID(org_id)
    user_uuid = uuid.UUID(user_id)

    db = SessionLocal()
    try:
        # Load document and verify org
        document = (
            db.query(Document)
            .filter(Document.id == document_uuid, Document.org_id == org_uuid)
            .first()
        )

        if not document:
            logger.error("[OCR] Document %s not found for org %s", document_id, org_id)
            return {"status": "error", "error": "Document not found"}

        # Get all pages for the document
        pages = (
            db.query(DocumentPage)
            .filter(
                DocumentPage.document_id == document_uuid,
                DocumentPage.org_id == org_uuid,
            )
            .order_by(DocumentPage.page_number)
            .all()
        )

        if not pages:
            logger.warning("[OCR] No pages found for document %s", document_id)
            return {"status": "error", "error": "No pages found"}

        # Filter pages: skip Done pages unless force=True
        pages_to_process = [p for p in pages if force or p.ocr_status != "Done"]

        # Mark pages to process as Queued
        for page in pages_to_process:
            if page.ocr_status != "Processing":
                page.ocr_status = "Queued"
        db.commit()

        succeeded = 0
        failed = 0

        for page in pages_to_process:
            try:
                # Mark processing
                page.ocr_status = "Processing"
                page.ocr_started_at = datetime.utcnow()
                page.ocr_error = None
                db.commit()

                # Run OCR (minio key stored per page)
                text, confidence, _meta = ocr_page_pdf(page.minio_key_page_pdf)

                # Persist results
                page.ocr_text = text
                page.ocr_confidence = confidence
                page.ocr_status = "Done"
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                succeeded += 1
            except OCRError as e:
                page.ocr_status = "Failed"
                page.ocr_error = str(e)[:500]
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                failed += 1
                logger.exception("[OCR] Page %s failed", page.id)
            except Exception as e:  # noqa: BLE001
                page.ocr_status = "Failed"
                page.ocr_error = str(e)[:500]
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                failed += 1
                logger.exception("[OCR] Unexpected error for page %s", page.id)

        # Audit once per document
        try:
            write_audit_event_sync(
                db,
                org_id=org_uuid,
                actor_user_id=user_uuid,
                action="ocr.completed",
                entity_type="document",
                entity_id=document_uuid,
                event_metadata={"pages_total": len(pages), "succeeded": succeeded, "failed": failed},
            )
        except Exception:
            logger.exception("[OCR] Failed to write audit event for document %s", document_id)

        return {"status": "ok", "pages_total": len(pages), "succeeded": succeeded, "failed": failed}
    finally:
        db.close()