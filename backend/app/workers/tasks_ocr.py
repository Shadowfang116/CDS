"""Celery tasks for OCR processing."""

import asyncio
import base64
import io
import logging
import uuid
from datetime import datetime

from PIL import Image

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentPage
from app.services.audit import log_event
from app.services.ocr import OCRError, download_page_pdf, pdf_to_image
from app.services.ocr_pipeline import run_ocr_pipeline
from app.services.ocr_quality import compute_ocr_quality_signal
from app.services.rule_engine import run_rules
from app.services.storage import get_object_bytes
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/tif"}


def _render_page_pdf_to_base64_png(minio_key: str) -> str:
    pdf_bytes = download_page_pdf(minio_key)
    image, _dpi_used = pdf_to_image(pdf_bytes)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _render_image_to_base64_png(minio_key: str) -> str:
    raw_bytes = get_object_bytes(minio_key)
    image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _render_page_asset_to_base64_png(minio_key: str, content_type: str) -> str:
    if content_type in IMAGE_CONTENT_TYPES:
        return _render_image_to_base64_png(minio_key)
    return _render_page_pdf_to_base64_png(minio_key)


@celery_app.task(name="ocr.process_document", bind=True, max_retries=3)
def process_document_ocr(
    self,
    document_id: str,
    org_id: str,
    user_id: str,
    force: bool = False,
):
    document_uuid = uuid.UUID(document_id)
    org_uuid = uuid.UUID(org_id)
    user_uuid = uuid.UUID(user_id)

    db = SessionLocal()
    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_uuid, Document.org_id == org_uuid)
            .first()
        )
        if not document:
            logger.error("[OCR] Document %s not found for org %s", document_id, org_id)
            return {"status": "error", "error": "Document not found"}

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

        document.status = "Processing"
        document.error_message = None
        db.commit()

        pages_to_process = [page for page in pages if force or page.ocr_status != "Done"]
        for page in pages_to_process:
            if page.ocr_status != "Processing":
                page.ocr_status = "Queued"
        db.commit()

        succeeded = 0
        failed = 0
        pages_for_pipeline: list[tuple[int, DocumentPage, str]] = []

        for page in pages_to_process:
            try:
                page.ocr_status = "Processing"
                page.ocr_started_at = datetime.utcnow()
                page.ocr_error = None
                db.commit()

                page_image = _render_page_asset_to_base64_png(
                    page.minio_key_page_pdf,
                    document.content_type,
                )
                pages_for_pipeline.append((len(pages_for_pipeline) + 1, page, page_image))
            except OCRError as exc:
                page.ocr_status = "Failed"
                page.ocr_error = str(exc)[:500]
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                failed += 1
                logger.exception("[OCR] Page %s failed", page.id)
            except Exception as exc:  # noqa: BLE001
                page.ocr_status = "Failed"
                page.ocr_error = str(exc)[:500]
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                failed += 1
                logger.exception("[OCR] Unexpected error for page %s", page.id)

        if pages_for_pipeline:
            pipeline_result = asyncio.run(
                run_ocr_pipeline(
                    document_id=str(document_uuid),
                    page_images=[payload for _, _, payload in pages_for_pipeline],
                )
            )
            results_by_request_index = {
                result.page_num: result for result in pipeline_result.pages
            }

            for request_index, page, _payload in pages_for_pipeline:
                result = results_by_request_index.get(request_index)
                if result is None or (
                    result.quality_level == "unavailable" and not (result.text or "").strip()
                ):
                    page.ocr_status = "Failed"
                    page.ocr_error = (
                        result.warning_reason[:500]
                        if result and result.warning_reason
                        else "OCR service unavailable"
                    )
                    page.ocr_finished_at = datetime.utcnow()
                    db.commit()
                    failed += 1
                    continue

                page.ocr_text = result.text
                page.ocr_confidence = result.confidence
                if hasattr(page, "ocr_quality_signal"):
                    avg_confidence = result.confidence
                    if avg_confidence is not None and avg_confidence <= 1:
                        avg_confidence *= 100
                    page.ocr_quality_signal = compute_ocr_quality_signal(
                        result.text or "",
                        avg_confidence,
                        settings,
                    )
                page.ocr_status = "Done"
                page.ocr_error = None
                page.ocr_finished_at = datetime.utcnow()
                db.commit()
                succeeded += 1

        if succeeded == 0 and failed > 0:
            document.status = "Failed"
            document.error_message = "OCR processing failed for every page."
        elif failed > 0:
            document.status = "NeedsReview"
            document.error_message = "OCR completed with one or more failed pages."
        else:
            document.status = "Complete"
            document.error_message = None
            run_rules(db, org_uuid, document.case_id, user_uuid)
        db.commit()

        try:
            log_event(
                db,
                action="ocr.completed",
                org_id=org_uuid,
                actor_id=user_uuid,
                entity_type="document",
                entity_id=document_uuid,
                case_id=document.case_id,
                after_json={
                    "pages_total": len(pages),
                    "succeeded": succeeded,
                    "failed": failed,
                    "document_status": document.status,
                },
            )
        except Exception:
            logger.exception("[OCR] Failed to write audit event for document %s", document_id)

        return {"status": "ok", "pages_total": len(pages), "succeeded": succeeded, "failed": failed}
    finally:
        db.close()