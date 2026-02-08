"""OCR fallback for corrupted page text."""
import logging
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.document import DocumentPage
from app.services.ocr import ocr_page_pdf, OCRError
from app.services.ocr_text_quality import is_text_corrupted, is_arabic_char, detect_mojibake

logger = logging.getLogger(__name__)


def re_ocr_page_if_corrupted(
    db: Session,
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    current_text: Optional[str] = None,
) -> Tuple[str, bool, str]:
    """
    Re-OCR a page if its text is corrupted (mojibake).
    
    Args:
        db: Database session
        org_id: Organization ID
        document_id: Document ID
        page_number: Page number (1-based)
        current_text: Current OCR text (if None, fetched from DB)
        
    Returns:
        Tuple of (corrected_text, was_re_ocred, reason)
        - corrected_text: The corrected OCR text (or original if not corrupted)
        - was_re_ocred: True if re-OCR was performed
        - reason: Reason for re-OCR or "ok" if not needed
    """
    # Fetch page to get text (if not provided) and for re-OCR (if needed)
    page = db.query(DocumentPage).filter(
        DocumentPage.org_id == org_id,
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
    ).first()
    
    if not page:
        logger.warning(f"OCR_FALLBACK: Page {page_number} not found for document {document_id}")
        return current_text if current_text else "", False, "page_not_found"
    
    # Use provided text or fetch from page
    if current_text is None:
        current_text = page.ocr_text or ""
    
    # Check if text is corrupted
    is_corrupted, reason = is_text_corrupted(current_text)
    
    if not is_corrupted:
        return current_text, False, "ok"
    
    if not page:
        logger.warning(f"OCR_FALLBACK: Page {page_number} not found for document {document_id}")
        return current_text, False, "page_not_found"
    
    if not page.minio_key_page_pdf:
        logger.warning(f"OCR_FALLBACK: Page {page_number} has no minio_key_page_pdf")
        return current_text, False, "no_pdf_key"
    
    logger.info(
        f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
        f"action=RE_OCR reason={reason} prev_engine={page.ocr_engine or 'unknown'} "
        f"prev_conf={float(page.ocr_confidence) if page.ocr_confidence else 0.0:.2f}"
    )
    
    # Re-OCR with Urdu support
    try:
        lang_used = "urd+eng"  # Default for Urdu documents
        psm = 6  # Form mode
        
        # Use ocr_page_pdf which already uses ocr_engine with script detection
        # This will automatically use urd+eng if Urdu is detected
        text, confidence, metadata = ocr_page_pdf(page.minio_key_page_pdf)
        
        # Normalize Arabic-Indic digits to ASCII (optional, but helpful)
        # This is already handled by Tesseract, but we can do additional normalization
        text = text.strip()
        
        # P17: Normalize text to UTF-8 safe format BEFORE persistence
        from app.services.ocr_text_quality import normalize_text_for_persistence
        text_normalized = normalize_text_for_persistence(text)
        
        # Calculate stats after OCR (use normalized text)
        arabic_char_count_after = sum(1 for c in text_normalized if is_arabic_char(c))
        _, mojibake_ratio_after, _, _ = detect_mojibake(text_normalized)
        
        # Update page in DB with corrected normalized text
        page.ocr_text = text_normalized
        page.ocr_confidence = confidence
        # Mark that this was a fallback OCR (store in engine field)
        page.ocr_engine = metadata.get('lang_used', 'tesseract_urd_fallback')
        if page.ocr_error:
            page.ocr_error = None  # Clear any previous errors
        # Flush but let caller commit (or commit if this is a separate session)
        db.flush()
        
        logger.info(
            f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
            f"action=RE_OCR_DONE new_len={len(text_normalized)} new_conf={confidence} "
            f"engine={metadata.get('lang_used', 'tesseract_urd_fallback')} "
            f"arabic_char_count={arabic_char_count_after} mojibake_ratio={mojibake_ratio_after:.3f}"
        )
        
        return text_normalized, True, f"re_ocred_reason={reason}"
        
    except OCRError as e:
        logger.error(f"OCR_FALLBACK: Failed to re-OCR page {page_number}: {e}")
        # Return original text even if corrupted (better than empty)
        return current_text, False, f"re_ocr_failed: {str(e)[:100]}"
    except Exception as e:
        logger.error(f"OCR_FALLBACK: Unexpected error re-OCRing page {page_number}: {e}")
        return current_text, False, f"unexpected_error: {str(e)[:100]}"


def get_page_text_with_fallback(
    db: Session,
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    use_corrections: bool = True,
) -> str:
    """
    Get page OCR text with automatic fallback to repair or re-OCR if corrupted.
    
    Repair flow:
    1. Load page OCR text (or correction if available)
    2. If corrupted: try encoding repair (latin1/cp1252 -> utf8)
    3. If repair succeeds: persist repaired text, return
    4. If repair fails: re-OCR with Urdu support, persist, return
    
    Args:
        db: Database session
        org_id: Organization ID
        document_id: Document ID
        page_number: Page number (1-indexed)
        use_corrections: If True, use OCRTextCorrection if available
        
    Returns:
        Corrected OCR text (or original if not corrupted)
    """
    # Fetch page
    page = db.query(DocumentPage).filter(
        DocumentPage.org_id == org_id,
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
    ).first()
    
    if not page:
        return ""
    
    # Get current text (use correction if available)
    current_text = page.ocr_text or ""
    
    if use_corrections:
        from app.models.ocr_text_correction import OCRTextCorrection
        correction = db.query(OCRTextCorrection).filter(
            OCRTextCorrection.org_id == org_id,
            OCRTextCorrection.document_id == document_id,
            OCRTextCorrection.page_number == page_number,
        ).first()
        
        if correction and correction.corrected_text:
            current_text = correction.corrected_text
    
    # Check if corrupted
    is_corrupted, reason = is_text_corrupted(current_text)
    
    if not is_corrupted:
        return current_text
    
    # STEP 1: Try repair first (encoding fix)
    from app.services.ocr_text_quality import try_repair_mojibake
    repaired_text, repair_method = try_repair_mojibake(current_text)
    
    if repaired_text:
        # P17: Normalize repaired text before persistence
        from app.services.ocr_text_quality import normalize_text_for_persistence
        repaired_text_normalized = normalize_text_for_persistence(repaired_text)
        
        # SUCCESS: Persist repaired text back to DB
        logger.info(
            f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
            f"action=REPAIR method={repair_method} "
            f"before_len={len(current_text)} after_len={len(repaired_text_normalized)} "
            f"reason={reason}"
        )
        
        # Update OCR page record (use normalized repaired text)
        page.ocr_text = repaired_text_normalized
        page.ocr_engine = (page.ocr_engine or "tesseract") + "+repaired"
        # Reduce confidence slightly to encourage manual review
        if page.ocr_confidence:
            page.ocr_confidence = min(page.ocr_confidence, 0.5)
        else:
            page.ocr_confidence = 0.5
        
        db.flush()  # Flush but let caller commit
        
        logger.info(
            f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
            f"action=REPAIR_PERSISTED engine={page.ocr_engine} confidence={page.ocr_confidence}"
        )
        
        return repaired_text_normalized
    
    # STEP 2: If repair failed, re-OCR with Urdu support
    logger.info(
        f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
        f"action=RE_OCR reason=repair_failed prev_engine={page.ocr_engine} "
        f"corruption_reason={reason}"
    )
    
    corrected_text, was_re_ocred, re_ocr_reason = re_ocr_page_if_corrupted(
        db=db,
        org_id=org_id,
        document_id=document_id,
        page_number=page_number,
        current_text=current_text,
    )
    
    if was_re_ocred:
        return corrected_text
    
    # If both repair and re-OCR failed, return original (corrupted) text
    # This is better than empty string for debugging
    logger.warning(
        f"OCR_FALLBACK: doc_id={document_id} page={page_number} "
        f"action=FALLBACK_FAILED returning_original_corrupted_text"
    )
    return current_text
