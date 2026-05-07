"""Phase 10: Celery task for re-running OCR on a single page."""
import logging
import uuid
from datetime import datetime

from celery.exceptions import MaxRetriesExceededError, Retry

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentPage
from app.services.audit import write_audit_event
from app.services.ocr import ocr_page_pdf
from app.services.ocr_quality import compute_ocr_quality_signal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _retry_countdown(task, base_seconds: int = 60, max_seconds: int = 300) -> int:
    retries = max(0, int(getattr(getattr(task, "request", None), "retries", 0) or 0))
    return min(base_seconds * (2 ** retries), max_seconds)


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
    try:
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

        original_settings = {}

        if options.get("force_profile"):
            if hasattr(settings, "OCR_PREPROCESS_PROFILE"):
                original_settings["OCR_PREPROCESS_PROFILE"] = settings.OCR_PREPROCESS_PROFILE
                settings.OCR_PREPROCESS_PROFILE = options["force_profile"]
            original_settings["OCR_ENABLE_ENHANCED_PREPROCESS"] = settings.OCR_ENABLE_ENHANCED_PREPROCESS
            settings.OCR_ENABLE_ENHANCED_PREPROCESS = options["force_profile"] == "enhanced"

        if options.get("force_detect") is not None:
            original_settings["OCR_ENABLE_SCRIPT_DETECTION"] = settings.OCR_ENABLE_SCRIPT_DETECTION
            settings.OCR_ENABLE_SCRIPT_DETECTION = options["force_detect"]

        if options.get("force_layout") is not None and hasattr(settings, "OCR_ENABLE_LAYOUT_SEGMENTATION"):
            original_settings["OCR_ENABLE_LAYOUT_SEGMENTATION"] = settings.OCR_ENABLE_LAYOUT_SEGMENTATION
            settings.OCR_ENABLE_LAYOUT_SEGMENTATION = options["force_layout"]

        if options.get("force_pdf_text_layer") is not None and hasattr(settings, "OCR_ENABLE_PDF_TEXT_LAYER"):
            original_settings["OCR_ENABLE_PDF_TEXT_LAYER"] = settings.OCR_ENABLE_PDF_TEXT_LAYER
            settings.OCR_ENABLE_PDF_TEXT_LAYER = options["force_pdf_text_layer"]

        if options.get("engine_mode") and hasattr(settings, "OCR_ENGINE_MODE"):
            original_settings["OCR_ENGINE_MODE"] = settings.OCR_ENGINE_MODE
            settings.OCR_ENGINE_MODE = options["engine_mode"]

        lang_hint = options.get("force_lang")
        if lang_hint:
            original_settings["OCR_LANG"] = settings.OCR_LANG
            settings.OCR_LANG = lang_hint

        try:
            t_start = datetime.utcnow()
            text, confidence, metadata = ocr_page_pdf(page.minio_key_page_pdf)
            t_end = datetime.utcnow()

            page.ocr_text = text
            page.ocr_confidence = confidence
            if hasattr(page, "ocr_quality_signal"):
                avg_confidence = metadata.get("confidence_raw") if isinstance(metadata, dict) else None
                if avg_confidence is None:
                    avg_confidence = confidence
                if avg_confidence is not None and avg_confidence <= 1:
                    avg_confidence *= 100
                page.ocr_quality_signal = compute_ocr_quality_signal(
                    text or "",
                    avg_confidence,
                    settings,
                )

            if not hasattr(page, "ocr_meta") or not page.ocr_meta:
                page.ocr_meta = {}

            if "rerun_history" not in page.ocr_meta:
                page.ocr_meta["rerun_history"] = []

            rerun_entry = {
                "when": datetime.utcnow().isoformat(),
                "options": options,
                "timings": {
                    "start": t_start.isoformat(),
                    "end": t_end.isoformat(),
                    "duration_ms": (t_end - t_start).total_seconds() * 1000,
                },
                "used_pdf_text_layer": metadata.get("pdf_text_layer", {}).get("used", False),
                "layout_used": metadata.get("layout_ocr", {}).get("used", False),
                "ensemble_winner": metadata.get("ensemble", {}).get("winner", "tesseract"),
            }

            page.ocr_meta["rerun_history"].append(rerun_entry)
            if len(page.ocr_meta["rerun_history"]) > 10:
                page.ocr_meta["rerun_history"] = page.ocr_meta["rerun_history"][-10:]

            page.ocr_meta.update(metadata)
            db.commit()

            write_audit_event(
                db=db,
                org_id=org_uuid,
                actor_user_id=None,
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
                    "confidence": float(confidence) if confidence is not None else None,
                },
            )

            logger.info(f"OCR rerun completed for page {page_number} of document {document_id}")
            return {"status": "success", "page_id": str(page.id)}

        except Retry:
            raise
        except MaxRetriesExceededError:
            raise
        except Exception as e:
            countdown = _retry_countdown(self)
            logger.error(f"OCR rerun failed for page {page_number}: {e}")
            write_audit_event(
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
            raise self.retry(exc=e, countdown=countdown)
        finally:
            for key, value in original_settings.items():
                setattr(settings, key, value)

    except Retry:
        raise
    except MaxRetriesExceededError:
        raise
    except Exception as e:
        countdown = _retry_countdown(self)
        logger.error(f"OCR rerun task failed: {e}")
        raise self.retry(exc=e, countdown=countdown)

    finally:
        db.close()
