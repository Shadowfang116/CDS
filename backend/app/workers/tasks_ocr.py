"""Celery tasks for OCR processing."""
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
    entity_type: str = None,
    entity_id: uuid.UUID = None,
    event_metadata: dict = None,
):
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
def process_document_ocr(self, document_id: str, org_id: str, user_id: str):
    """
    Process OCR for all pages of a document.
    
    Each page is processed independently - if one fails, others continue.
    """
    document_uuid = uuid.UUID(document_id)
    org_uuid = uuid.UUID(org_id)
    user_uuid = uuid.UUID(user_id)
    
    db = SessionLocal()
    try:
        # Load document and verify org
        document = db.query(Document).filter(
            Document.id == document_uuid,
            Document.org_id == org_uuid,
        ).first()
        
        if not document:
            logger.error(f"Document {document_id} not found for org {org_id}")
            return {"status": "error", "error": "Document not found"}
        
        # Get all pages for the document
        pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == document_uuid,
            DocumentPage.org_id == org_uuid,
        ).order_by(DocumentPage.page_number).all()
        
        if not pages:
            logger.warning(f"No pages found for document {document_id}")
            return {"status": "error", "error": "No pages found"}
        
        # Mark all pages as Queued
        for page in pages:
            page.ocr_status = "Queued"
        db.commit()
        
        # Process each page
        success_count = 0
        failed_count = 0
        
        for page in pages:
            try:
                # Mark as Processing
                page.ocr_status = "Processing"
                page.ocr_started_at = datetime.utcnow()
                db.commit()
                
                # Run OCR
                text, confidence = ocr_page_pdf(page.minio_key_page_pdf)
                
                # Update page with results
                page.ocr_text = text
                page.ocr_confidence = confidence
                page.ocr_status = "Done"
                page.ocr_finished_at = datetime.utcnow()
                page.ocr_error = None
                db.commit()
                
                success_count += 1
                logger.info(f"OCR completed for page {page.page_number} of document {document_id}")
                
            except OCRError as e:
                # Mark page as Failed but continue with others
                page.ocr_status = "Failed"
                page.ocr_error = str(e)
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                
                failed_count += 1
                logger.error(f"OCR failed for page {page.page_number} of document {document_id}: {e}")
                
            except Exception as e:
                # Unexpected error - mark as Failed
                page.ocr_status = "Failed"
                page.ocr_error = f"Unexpected error: {str(e)}"
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                
                failed_count += 1
                logger.error(f"Unexpected OCR error for page {page.page_number} of document {document_id}: {e}")
        
        # Write audit event
        write_audit_event_sync(
            db=db,
            org_id=org_uuid,
            actor_user_id=user_uuid,
            action="ocr.document_complete",
            entity_type="document",
            entity_id=document_uuid,
            event_metadata={
                "document_id": document_id,
                "case_id": str(document.case_id),
                "total_pages": len(pages),
                "success_count": success_count,
                "failed_count": failed_count,
            },
        )
        
        return {
            "status": "completed",
            "document_id": document_id,
            "total_pages": len(pages),
            "success_count": success_count,
            "failed_count": failed_count,
        }
        
    except Exception as e:
        logger.error(f"Document OCR task failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

