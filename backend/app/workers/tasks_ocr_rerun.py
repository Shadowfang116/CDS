"""Phase 10: Celery task for re-running OCR on a single page."""
import uuid
import logging
import tempfile
import os
from datetime import datetime

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document, DocumentPage
from app.models.audit_log import AuditLog
from app.services.ocr_engine import ocr_page_pdf
from app.services.storage import get_object_bytes
from app.core.config import settings

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


@celery_app.task(name="ocr.rerun_page", bind=True, max_retries=3)
def rerun_page_ocr_task(
    self,
    org_id: str,
    case_id: str,
    document_id: str,
    page_number: int,
    request_id: str,
    options: dict,
):
    """
    Re-run OCR for a single page with optional forced settings.
    
    Args:
        org_id: Organization ID
        case_id: Case ID
        document_id: Document ID
        page_number: Page number (1-based)
        request_id: Request ID for audit correlation
        options: Dict with force_* options (force_profile, force_detect, etc.)
    
    Updates page.ocr_text, page.ocr_confidence, page.ocr_meta.
    Does NOT overwrite manual override (ocr_text_override).
    """
    org_uuid = uuid.UUID(org_id)
    case_uuid = uuid.UUID(case_id)
    document_uuid = uuid.UUID(document_id)
    request_uuid = uuid.UUID(request_id)
    
    db = SessionLocal()
    pdf_temp_path = None
    
    try:
        # Load Document and Page (tenant-safe)
        document = db.query(Document).filter(
            Document.id == document_uuid,
            Document.case_id == case_uuid,
            Document.org_id == org_uuid,
        ).first()
        
        if not document:
            logger.error(f"Document {document_id} not found for org {org_id}")
            return {"status": "error", "error": "Document not found"}
        
        page = db.query(DocumentPage).filter(
            DocumentPage.document_id == document_uuid,
            DocumentPage.page_number == page_number,
            DocumentPage.org_id == org_uuid,
        ).first()
        
        if not page:
            logger.error(f"Page {page_number} not found for document {document_id}")
            return {"status": "error", "error": "Page not found"}
        
        # Download document PDF to temp file
        if document.minio_key_original:
            try:
                pdf_bytes = get_object_bytes(document.minio_key_original)
                temp_fd, pdf_temp_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"Downloaded document PDF to temp file: {pdf_temp_path}")
            except Exception as e:
                logger.error(f"Failed to download document PDF: {e}")
                return {"status": "error", "error": f"Failed to download PDF: {e}"}
        else:
            return {"status": "error", "error": "Document has no PDF key"}
        
        # Temporarily override settings based on options
        original_settings = {}
        
        if options.get("force_profile"):
            original_settings["OCR_PREPROCESS_PROFILE"] = settings.OCR_PREPROCESS_PROFILE
            original_settings["OCR_ENABLE_ENHANCED_PREPROCESS"] = settings.OCR_ENABLE_ENHANCED_PREPROCESS
            settings.OCR_PREPROCESS_PROFILE = options["force_profile"]
            settings.OCR_ENABLE_ENHANCED_PREPROCESS = (options["force_profile"] == "enhanced")
        
        if options.get("force_detect") is not None:
            original_settings["OCR_ENABLE_SCRIPT_DETECTION"] = settings.OCR_ENABLE_SCRIPT_DETECTION
            settings.OCR_ENABLE_SCRIPT_DETECTION = options["force_detect"]
        
        if options.get("force_layout") is not None:
            original_settings["OCR_ENABLE_LAYOUT_SEGMENTATION"] = settings.OCR_ENABLE_LAYOUT_SEGMENTATION
            settings.OCR_ENABLE_LAYOUT_SEGMENTATION = options["force_layout"]
        
        if options.get("force_pdf_text_layer") is not None:
            original_settings["OCR_ENABLE_PDF_TEXT_LAYER"] = settings.OCR_ENABLE_PDF_TEXT_LAYER
            settings.OCR_ENABLE_PDF_TEXT_LAYER = options["force_pdf_text_layer"]
        
        if options.get("engine_mode"):
            original_settings["OCR_ENGINE_MODE"] = settings.OCR_ENGINE_MODE
            settings.OCR_ENGINE_MODE = options["engine_mode"]
        
        lang_hint = options.get("force_lang")
        
        try:
            # Run OCR
            t_start = datetime.utcnow()
            result = ocr_page_pdf(
                page.minio_key_page_pdf,
                lang_hint=lang_hint,
                pdf_path=pdf_temp_path,
                page_number=page_number - 1  # Convert to 0-based
            )
            t_end = datetime.utcnow()
            
            # Update page OCR fields (but NOT override)
            page.ocr_text = result.text
            page.ocr_confidence = result.confidence
            
            # Update ocr_meta with rerun history
            if not hasattr(page, 'ocr_meta') or not page.ocr_meta:
                page.ocr_meta = {}
            
            if "rerun_history" not in page.ocr_meta:
                page.ocr_meta["rerun_history"] = []
            
            # Append rerun entry (cap at last 10)
            rerun_entry = {
                "when": datetime.utcnow().isoformat(),
                "options": options,
                "timings": {
                    "start": t_start.isoformat(),
                    "end": t_end.isoformat(),
                    "duration_ms": (t_end - t_start).total_seconds() * 1000,
                },
                "used_pdf_text_layer": result.metadata.get("pdf_text_layer", {}).get("used", False),
                "layout_used": result.metadata.get("layout_ocr", {}).get("used", False),
                "ensemble_winner": result.metadata.get("ensemble", {}).get("winner", "tesseract"),
            }
            
            page.ocr_meta["rerun_history"].append(rerun_entry)
            if len(page.ocr_meta["rerun_history"]) > 10:
                page.ocr_meta["rerun_history"] = page.ocr_meta["rerun_history"][-10:]
            
            # Merge other metadata
            page.ocr_meta.update(result.metadata)
            
            db.commit()
            
            # Audit log
            write_audit_event_sync(
                db=db,
                org_id=org_uuid,
                actor_user_id=None,  # System-initiated rerun
                action="ocr.page_rerun_succeeded",
                entity_type="document_page",
                entity_id=page.id,
                event_metadata={
                    "request_id": str(request_uuid),
                    "case_id": str(case_id),
                    "document_id": str(document_id),
                    "page_number": page_number,
                    "page_id": str(page.id),
                    "options": options,
                    "confidence": float(result.confidence) if result.confidence else None,
                },
            )
            
            logger.info(f"OCR rerun completed for page {page_number} of document {document_id}")
            return {"status": "success", "page_id": str(page.id)}
            
        except Exception as e:
            logger.error(f"OCR rerun failed for page {page_number}: {e}")
            
            # Audit log failure
            write_audit_event_sync(
                db=db,
                org_id=org_uuid,
                actor_user_id=None,
                action="ocr.page_rerun_failed",
                entity_type="document_page",
                entity_id=page.id,
                event_metadata={
                    "request_id": str(request_uuid),
                    "case_id": str(case_id),
                    "document_id": str(document_id),
                    "page_number": page_number,
                    "page_id": str(page.id),
                    "error": str(e)[:500],
                },
            )
            
            raise self.retry(exc=e, countdown=60)
        
        finally:
            # Restore original settings
            for key, value in original_settings.items():
                setattr(settings, key, value)
    
    except Exception as e:
        logger.error(f"OCR rerun task failed: {e}")
        raise self.retry(exc=e, countdown=60)
    
    finally:
        # Clean up temp PDF file
        if pdf_temp_path and os.path.exists(pdf_temp_path):
            try:
                os.remove(pdf_temp_path)
                logger.debug(f"Cleaned up temp PDF file: {pdf_temp_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp PDF file {pdf_temp_path}: {e}")
        
        db.close()

