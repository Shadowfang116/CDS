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
def process_document_ocr(self, document_id: str, org_id: str, user_id: str, force: bool = False):
    """
    Process OCR for all pages of a document.
    
    Each page is processed independently - if one fails, others continue.
    
    Args:
        force: If True, re-process pages even if already Done.
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
        
        # Filter pages: skip Done pages unless force=True
        pages_to_process = [p for p in pages if force or p.ocr_status != "Done"]
        
        # Mark pages to process as Queued
        for page in pages_to_process:
            if page.ocr_status != "Processing":  # Don't override if already processing
                page.ocr_status = "Queued"
        db.commit()
        
        # Process each page
        success_count = 0
        failed_count = 0
        skipped_count = len(pages) - len(pages_to_process)
        
        for page in pages_to_process:
            try:
                # Idempotency check: skip if already Done (unless force)
                if not force and page.ocr_status == "Done":
                    skipped_count += 1
                    continue
                
                # Mark as Processing
                page.ocr_status = "Processing"
                page.ocr_started_at = datetime.utcnow()
                db.commit()
                
                # Audit: page started
                write_audit_event_sync(
                    db=db,
                    org_id=org_uuid,
                    actor_user_id=user_uuid,
                    action="ocr.page_started",
                    entity_type="document_page",
                    entity_id=page.id,
                    event_metadata={"page_number": page.page_number, "document_id": document_id},
                )
                
                # Run OCR (returns text, confidence, metadata)
                text, confidence, ocr_metadata = ocr_page_pdf(page.minio_key_page_pdf)
                
                # P17: Normalize text to UTF-8 safe format BEFORE persistence
                from app.services.ocr_text_quality import normalize_text_for_persistence
                text_normalized = normalize_text_for_persistence(text)
                
                # Ensure confidence is normalized (should already be from ocr_engine, but double-check)
                from app.services.ocr_engine import normalize_confidence
                confidence_normalized = normalize_confidence(confidence)
                
                # Extract observability fields from metadata
                lang_used = ocr_metadata.get("lang_used", "unknown")
                script_detection = ocr_metadata.get("script_detection", {})
                script = script_detection.get("script", "unknown") if isinstance(script_detection, dict) else "unknown"
                preprocess_method = ocr_metadata.get("preprocess_method", "unknown")
                dpi_used = ocr_metadata.get("dpi_used", "unknown")
                confidence_raw = ocr_metadata.get("confidence_raw", None)
                
                # Log per-page observability (required for proof)
                logger.info(
                    f"OCR_PAGE_OBSERVABILITY: document_id={document_id}, "
                    f"page_number={page.page_number}, "
                    f"lang_used={lang_used}, "
                    f"script={script}, "
                    f"preprocess_method={preprocess_method}, "
                    f"dpi_used={dpi_used}, "
                    f"confidence_raw={confidence_raw}, "
                    f"confidence_normalized={confidence_normalized}"
                )
                
                # P17: Update page with results (use normalized text)
                page.ocr_text = text_normalized
                page.ocr_confidence = confidence_normalized
                page.ocr_status = "Done"
                page.ocr_finished_at = datetime.utcnow()
                page.ocr_error = None
                db.commit()
                
                # Audit: page done
                write_audit_event_sync(
                    db=db,
                    org_id=org_uuid,
                    actor_user_id=user_uuid,
                    action="ocr.page_done",
                    entity_type="document_page",
                    entity_id=page.id,
                    event_metadata={
                        "page_number": page.page_number,
                        "document_id": document_id,
                        "confidence": float(confidence) if confidence else None,
                        **ocr_metadata,  # Include OCR metadata
                    },
                )
                
                success_count += 1
                logger.info(f"OCR completed for page {page.page_number} of document {document_id}")
                
            except OCRError as e:
                # Mark page as Failed but continue with others
                error_msg = str(e)[:500]  # Limit error message length
                page.ocr_status = "Failed"
                page.ocr_error = error_msg
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                
                # Audit: page failed
                write_audit_event_sync(
                    db=db,
                    org_id=org_uuid,
                    actor_user_id=user_uuid,
                    action="ocr.page_failed",
                    entity_type="document_page",
                    entity_id=page.id,
                    event_metadata={
                        "page_number": page.page_number,
                        "document_id": document_id,
                        "error": error_msg,
                    },
                )
                
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
            "processed_count": len(pages_to_process),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
        }
        
    except Exception as e:
        logger.error(f"Document OCR task failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

