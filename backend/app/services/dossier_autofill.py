"""Dossier Autofill v1 - Extract key fields from OCR text with evidence snippets."""
import uuid
import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.ocr_extraction import OCRExtractionCandidate
from app.models.ocr_text_correction import OCRTextCorrection
from app.services.extractors.name_lines import extract_name_lines, is_name_like_field, normalize_whitespace
from app.services.extractors.validators import get_field_validator, is_probably_name_line
from app.services.extractors.candidate_gate import normalize_and_validate_candidate
from sqlalchemy import func

logger = logging.getLogger(__name__)

# Debug flag for dossier autofill write-path observability
DOSSIER_AUTOFILL_DEBUG = os.getenv("DOSSIER_AUTOFILL_DEBUG", "true").lower() == "true"
PARTY_ROLES_DEBUG = os.getenv("PARTY_ROLES_DEBUG", "true").lower() == "true"


@dataclass
class ExtractedField:
    """Extracted field with evidence."""
    field_path: str
    value: str
    confidence: float
    evidence: Dict[str, Any]  # {document_id, page_number, snippet, snippet_start_idx?, snippet_end_idx?}


def extract_snippet(ocr_text: str, match_start: int, match_end: int, context_chars: int = 40) -> str:
    """Extract snippet with context around matched text."""
    snippet_start = max(0, match_start - context_chars)
    snippet_end = min(len(ocr_text), match_end + context_chars)
    snippet = ocr_text[snippet_start:snippet_end]
    # Clean up snippet (remove extra whitespace, normalize)
    snippet = re.sub(r'\s+', ' ', snippet).strip()
    return snippet


def normalize_text(text: str) -> str:
    """Normalize text for matching (Urdu/English punctuation tolerant)."""
    # Remove common punctuation variations
    text = re.sub(r'[.,;:\-_\s]+', ' ', text)
    text = text.strip().lower()
    return text


def extract_plot_number(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract plot number patterns. Returns (value, confidence, start_idx, end_idx)."""
    patterns = [
        (r'(?:plot|plot\s*no\.?|plot\s*#|plot\s*number)\s*[:]?\s*(\d+)', 0.95),
        (r'plot\s*(\d+)', 0.85),
        (r'no\.?\s*(\d+)', 0.70),  # Generic "No. X" - lower confidence
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for pattern, base_confidence in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            # Validate it's a reasonable plot number (1-9999)
            if value.isdigit() and 1 <= int(value) <= 9999:
                results.append((value, base_confidence, match.start(), match.end()))
    
    # Deduplicate by value, keep highest confidence
    if results:
        best = max(results, key=lambda x: x[1])
        return [best]
    return []


def extract_block(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract block (e.g., "Block E", "Block-E")."""
    patterns = [
        (r'block\s*([A-Z])', 0.95),
        (r'block\s*-\s*([A-Z])', 0.95),
        (r'block\s*([a-z])', 0.90),
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for pattern, confidence in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1).upper()
            results.append((value, confidence, match.start(), match.end()))
    
    if results:
        best = max(results, key=lambda x: x[1])
        return [best]
    return []


def extract_phase(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract phase (e.g., "Phase 8", "Phase-VIII", "Phase 5")."""
    patterns = [
        (r'phase\s*(\d+)', 0.95),
        (r'phase\s*-\s*(\d+)', 0.95),
        (r'phase\s*([IVX]+)', 0.90),  # Roman numerals
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for pattern, confidence in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            results.append((value, confidence, match.start(), match.end()))
    
    if results:
        best = max(results, key=lambda x: x[1])
        return [best]
    return []


def extract_scheme_name(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract scheme/society name (e.g., "Faisal Town", "Union Town", "DHA")."""
    # Common scheme names (can be extended)
    scheme_keywords = [
        'faisal town', 'union town', 'dha', 'defence', 'bahria town',
        'model town', 'gulberg', 'johar town', 'wapda town'
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for scheme in scheme_keywords:
        pattern = rf'\b{re.escape(scheme)}\b'
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            # Extract full phrase (try to get 2-3 words around it)
            start = max(0, match.start() - 20)
            end = min(len(ocr_text), match.end() + 20)
            context = ocr_text[start:end]
            # Try to extract a proper name (capitalized words)
            name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', context)
            if name_match:
                value = name_match.group(1)
            else:
                value = match.group(0).title()
            results.append((value, 0.85, match.start(), match.end()))
            break  # Only first occurrence per scheme
    
    if results:
        best = max(results, key=lambda x: x[1])
        return [best]
    return []


def extract_location_fields(ocr_text: str) -> Dict[str, List[Tuple[str, float, int, int]]]:
    """Extract mouza, tehsil, district."""
    results = {}
    
    patterns = {
        'mouza': [
            (r'mouza\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 0.90),
            (r'mouza\s*[:]?\s*([A-Z][a-z]+)', 0.85),
        ],
        'tehsil': [
            (r'tehsil\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 0.90),
            (r'tehsil\s*[:]?\s*([A-Z][a-z]+)', 0.85),
        ],
        'district': [
            (r'district\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 0.90),
            (r'district\s*[:]?\s*([A-Z][a-z]+)', 0.85),
        ],
    }
    
    text_lower = ocr_text.lower()
    
    for field, field_patterns in patterns.items():
        field_results = []
        for pattern, confidence in field_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                value = match.group(1).strip()
                field_results.append((value, confidence, match.start(), match.end()))
        
        if field_results:
            best = max(field_results, key=lambda x: x[1])
            results[field] = [best]
    
    return results


def extract_khasra_numbers(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract khasra numbers (e.g., "Khasra No. 123/4", "Khasra 123-4")."""
    patterns = [
        (r'khasra\s*no\.?\s*[:]?\s*(\d+(?:[/-]\d+)?)', 0.95),
        (r'khasra\s*(\d+(?:[/-]\d+)?)', 0.90),
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for pattern, confidence in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            results.append((value, confidence, match.start(), match.end()))
    
    # Return all unique khasra numbers (not just best)
    unique_results = {}
    for value, conf, start, end in results:
        if value not in unique_results or conf > unique_results[value][1]:
            unique_results[value] = (value, conf, start, end)
    
    return list(unique_results.values())


def extract_registry_fields(ocr_text: str) -> Dict[str, List[Tuple[str, float, int, int]]]:
    """Extract registry number and date."""
    results = {}
    
    # Registry number
    registry_patterns = [
        (r'registry\s*no\.?\s*[:]?\s*(\d+)', 0.90),
        (r'registration\s*no\.?\s*[:]?\s*(\d+)', 0.85),
    ]
    
    text_lower = ocr_text.lower()
    
    registry_results = []
    for pattern, confidence in registry_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            registry_results.append((value, confidence, match.start(), match.end()))
    
    if registry_results:
        best = max(registry_results, key=lambda x: x[1])
        results['registry_number'] = [best]
    
    # Registry date (simple patterns)
    date_patterns = [
        (r'registry\s*date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', 0.85),
        (r'registration\s*date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', 0.85),
    ]
    
    date_results = []
    for pattern, confidence in date_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            date_results.append((value, confidence, match.start(), match.end()))
    
    if date_results:
        best = max(date_results, key=lambda x: x[1])
        results['registry_date'] = [best]
    
    return results


def extract_estamp_id(ocr_text: str) -> List[Tuple[str, float, int, int]]:
    """Extract e-stamp ID or number."""
    patterns = [
        (r'e[-\s]?stamp\s*(?:id|no\.?|number)\s*[:]?\s*([A-Z0-9\-]+)', 0.95),
        (r'estamp\s*[:]?\s*([A-Z0-9\-]+)', 0.90),
        (r'stamp\s*paper\s*(?:id|no\.?)\s*[:]?\s*([A-Z0-9\-]+)', 0.85),
    ]
    
    results = []
    text_lower = ocr_text.lower()
    
    for pattern, confidence in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value = match.group(1).strip()
            if len(value) >= 5:  # Reasonable length for ID
                results.append((value, confidence, match.start(), match.end()))
    
    if results:
        best = max(results, key=lambda x: x[1])
        return [best]
    return []


def get_document_ocr_quality(
    db: Session,
    org_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Tuple[str, List[str]]:
    """
    Get OCR quality level for a document.
    Returns: (quality_level, reasons)
    """
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == org_id,
    ).all()
    
    if not pages:
        return "Low", ["No pages found"]
    
    done_pages = [p for p in pages if p.ocr_status == "Done"]
    failed_pages = [p for p in pages if p.ocr_status == "Failed"]
    
    if not done_pages:
        return "Low", ["No pages with completed OCR"]
    
    # Calculate average chars per page
    total_chars = sum(len(p.ocr_text or "") for p in done_pages)
    avg_chars = total_chars / len(done_pages) if done_pages else 0
    
    quality_level = "Good"
    reasons = []
    
    if avg_chars < 80:
        quality_level = "Low"
        reasons.append(f"Low average characters per page ({avg_chars:.0f} < 80)")
    
    failed_pct = (len(failed_pages) / len(pages)) * 100 if pages else 0
    if len(failed_pages) > 0:
        if failed_pct > 20:
            quality_level = "Critical"
            reasons.append(f"High failure rate ({failed_pct:.0f}% pages failed)")
        else:
            if quality_level == "Good":
                quality_level = "Low"
            reasons.append(f"{len(failed_pages)} page(s) failed OCR")
    
    return quality_level, reasons


def autofill_dossier(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    document_ids: Optional[List[uuid.UUID]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Autofill dossier fields from OCR text.
    
    Returns:
    {
        "extracted": [ExtractedField],
        "updated_fields": [field_path],
        "skipped_fields": [field_path],
        "errors": [str]
    }
    """
    # P19: Generate request_id for traceability
    request_id = str(uuid.uuid4())[:8]
    
    errors = []
    extracted_fields: List[ExtractedField] = []
    
    # A. At start of autofill
    if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
        logger.info(
            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] START autofill case_id={case_id} overwrite={overwrite} "
            f"document_ids={document_ids}"
        )
    
    # Get documents (filtered by document_ids if provided)
    query = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    )
    if document_ids:
        query = query.filter(Document.id.in_(document_ids))
    
    documents = query.all()
    
    if not documents:
        errors.append("No documents found for case")
        return {
            "extracted": [],
            "updated_fields": [],
            "skipped_fields": [],
            "errors": errors,
        }
    
    # P14: Collect OCR text from all Done pages (use corrected text if available, with OCR fallback)
    # Group by document for party role extraction
    pages_data: List[Tuple[uuid.UUID, int, str]] = []  # (doc_id, page_num, effective_ocr_text)
    pages_by_document: Dict[uuid.UUID, List[Tuple[int, str]]] = {}  # doc_id -> [(page_num, text)]
    
    from app.services.ocr_fallback import get_page_text_with_fallback
    
    for doc in documents:
        pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id,
            DocumentPage.org_id == org_id,
            DocumentPage.ocr_status == "Done",
        ).order_by(DocumentPage.page_number).all()
        
        doc_pages = []
        for page in pages:
            # Use get_page_text_with_fallback which automatically re-OCRs corrupted pages
            effective_text = get_page_text_with_fallback(
                db=db,
                org_id=org_id,
                document_id=doc.id,
                page_number=page.page_number,
                use_corrections=True,
            )
            
            if effective_text:
                pages_data.append((doc.id, page.page_number, effective_text))
                doc_pages.append((page.page_number, effective_text))
        
        if doc_pages:
            pages_by_document[doc.id] = doc_pages
    
    if not pages_data:
        errors.append("No OCR text found (pages may not be processed yet)")
        return {
            "extracted": [],
            "updated_fields": [],
            "skipped_fields": [],
            "errors": errors,
        }
    
    # P16: Call HF Extractor for each page to get AI-extracted entities (CNIC, etc.)
    from app.services.extractors.hf_extractor_client import extract_entities_page
    hf_entities_by_page: Dict[Tuple[uuid.UUID, int], List] = {}  # (doc_id, page_num) -> entities
    hf_pages_called = 0
    hf_entities_received = 0
    
    try:
        for doc in documents:
            pages = db.query(DocumentPage).filter(
                DocumentPage.document_id == doc.id,
                DocumentPage.org_id == org_id,
                DocumentPage.ocr_status == "Done",
            ).order_by(DocumentPage.page_number).all()
            
            for page in pages:
                # Get OCR text and metadata for this page
                effective_text = get_page_text_with_fallback(
                    db=db,
                    org_id=org_id,
                    document_id=doc.id,
                    page_number=page.page_number,
                    use_corrections=True,
                )
                
                if not effective_text:
                    continue
                
                # Get page image bytes for HF Extractor
                from app.services.documents.pdf_render import get_page_image_bytes
                page_image_bytes = get_page_image_bytes(page.minio_key_page_pdf)
                
                # Call HF Extractor (with image - hf-extractor will run OCR if needed)
                hf_pages_called += 1
                entities = extract_entities_page(
                    doc_id=str(doc.id),
                    page_no=page.page_number,
                    ocr_text=effective_text,  # Optional - pass if available
                    ocr_engine="tesseract",  # DocumentPage doesn't have ocr_engine field
                    ocr_confidence=float(page.ocr_confidence) if page.ocr_confidence else 0.0,
                    labels=["CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT"],
                    image_bytes=page_image_bytes,  # P17: Pass image bytes so hf-extractor can run OCR
                )
                
                if entities:
                    hf_entities_received += len(entities)
                    hf_entities_by_page[(doc.id, page.page_number)] = entities
                    
                    if DOSSIER_AUTOFILL_DEBUG:
                        logger.info(
                            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor doc_id={doc.id} page_no={page.page_number} "
                            f"entities_received={len(entities)}"
                        )
        
        if DOSSIER_AUTOFILL_DEBUG:
            logger.info(
                f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor summary pages_called={hf_pages_called} "
                f"entities_received={hf_entities_received}"
            )
    except Exception as e:
        logger.exception(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor error: {repr(e)}")
        # Continue with other extractions even if HF extractor fails
    
    # Extract fields from all OCR text
    all_extractions: Dict[str, List[Tuple[str, float, uuid.UUID, int, int, int]]] = {}
    # Format: field_path -> [(value, confidence, doc_id, page_num, start_idx, end_idx)]
    
    for doc_id, page_num, ocr_text in pages_data:
        # Extract plot number
        for value, conf, start, end in extract_plot_number(ocr_text):
            if 'property.plot_number' not in all_extractions:
                all_extractions['property.plot_number'] = []
            all_extractions['property.plot_number'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract block
        for value, conf, start, end in extract_block(ocr_text):
            if 'property.block' not in all_extractions:
                all_extractions['property.block'] = []
            all_extractions['property.block'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract phase
        for value, conf, start, end in extract_phase(ocr_text):
            if 'property.phase' not in all_extractions:
                all_extractions['property.phase'] = []
            all_extractions['property.phase'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract scheme name
        for value, conf, start, end in extract_scheme_name(ocr_text):
            if 'property.scheme_name' not in all_extractions:
                all_extractions['property.scheme_name'] = []
            all_extractions['property.scheme_name'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract location fields
        location_fields = extract_location_fields(ocr_text)
        for field_name, field_results in location_fields.items():
            field_path = f'property.{field_name}'
            if field_path not in all_extractions:
                all_extractions[field_path] = []
            for value, conf, start, end in field_results:
                all_extractions[field_path].append((value, conf, doc_id, page_num, start, end))
        
        # Extract khasra numbers
        for value, conf, start, end in extract_khasra_numbers(ocr_text):
            if 'property.khasra_numbers' not in all_extractions:
                all_extractions['property.khasra_numbers'] = []
            all_extractions['property.khasra_numbers'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract registry fields
        registry_fields = extract_registry_fields(ocr_text)
        for field_name, field_results in registry_fields.items():
            field_path = f'registry.{field_name}'
            if field_path not in all_extractions:
                all_extractions[field_path] = []
            for value, conf, start, end in field_results:
                all_extractions[field_path].append((value, conf, doc_id, page_num, start, end))
        
        # Extract estamp ID
        for value, conf, start, end in extract_estamp_id(ocr_text):
            if 'stamp.estamp_id_or_number' not in all_extractions:
                all_extractions['stamp.estamp_id_or_number'] = []
            all_extractions['stamp.estamp_id_or_number'].append((value, conf, doc_id, page_num, start, end))
        
        # Extract party name (using name-lines extractor for filtering)
        name_lines, _ = extract_name_lines(ocr_text)
        for name_result in name_lines:
            field_path = 'party.name.raw'
            if field_path not in all_extractions:
                all_extractions[field_path] = []
            # Find the line in OCR text for snippet
            snippet_start = ocr_text.find(name_result.value)
            snippet_end = snippet_start + len(name_result.value) if snippet_start >= 0 else len(ocr_text)
            all_extractions[field_path].append((
                name_result.value,
                name_result.score,  # Use score as confidence
                doc_id,
                page_num,
                snippet_start if snippet_start >= 0 else 0,
                snippet_end,
            ))
    
    # Extract party roles (seller, buyer, witness) per document
    from app.services.extractors.party_roles import extract_party_roles_from_document, PageOCR
    
    # Wrap party roles extraction in try/except for observability
    try:
        for doc in documents:
            if doc.id not in pages_by_document:
                continue
            
            # Build PageOCR list for this document
            doc_pages_ocr = []
            for page_num, text in pages_by_document[doc.id]:
                doc_pages_ocr.append(PageOCR(
                    document_id=str(doc.id),
                    document_name=doc.original_filename or "",
                    page_number=page_num,
                    text=text
                ))
            
            # Extract party roles
            roles = extract_party_roles_from_document(doc_pages_ocr)
            
            # P16: Only write party roles for sale deed documents (hard rule)
            from app.services.extractors.party_roles import detect_sale_deed
            combined_text = '\n'.join([p.text for p in doc_pages_ocr])
            is_sale_deed_result = detect_sale_deed(combined_text)
            
            # Write-path observability: log raw extraction results
            if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                logger.info(
                    f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] doc_id={doc.id} filename=\"{doc.original_filename}\" "
                    f"is_sale_deed={is_sale_deed_result} "
                    f"raw_seller=\"{roles.get('seller_names', '')}\" "
                    f"raw_buyer=\"{roles.get('buyer_names', '')}\" "
                    f"raw_witness=\"{roles.get('witness_names', '')}\""
                )
            
            # P16: SKIP writing party roles if NOT a sale deed
            if not is_sale_deed_result:
                if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] doc_id={doc.id} filename=\"{doc.original_filename}\" "
                        f"SKIP party roles reason=not_sale_deed"
                    )
                continue  # Skip to next document
            
            # P20: Overwrite cleanup for party roles BEFORE writing new ones
            if overwrite:
                deleted_rows = db.query(OCRExtractionCandidate).filter(
                    OCRExtractionCandidate.case_id == case_id,
                    OCRExtractionCandidate.document_id == doc.id,
                    OCRExtractionCandidate.field_key.in_(['party.seller.names', 'party.buyer.names', 'party.witness.names'])
                ).delete(synchronize_session=False)
                db.flush()  # Flush to ensure delete happens before inserts
                logger.info(
                    f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] overwrite_party_roles_delete doc_id={doc.id} deleted_rows={deleted_rows}"
                )
            
            # P20: Normalize roles into structured format for deterministic processing
            # Extract all roles with their metadata
            normalized_roles = {
                "seller": {
                    "value": roles.get("seller_names", ""),
                    "page": roles.get("evidence", {}).get("page_number", doc_pages_ocr[0].page_number if doc_pages_ocr else 1),
                    "method": roles.get("evidence", {}).get("role_method", {}).get("seller", "cnic_fallback"),
                },
                "buyer": {
                    "value": roles.get("buyer_names", ""),
                    "page": roles.get("evidence", {}).get("page_number", doc_pages_ocr[0].page_number if doc_pages_ocr else 1),
                    "method": roles.get("evidence", {}).get("role_method", {}).get("buyer", "cnic_fallback"),
                },
                "witness": {
                    "value": roles.get("witness_names", ""),
                    "page": roles.get("evidence", {}).get("page_number", doc_pages_ocr[0].page_number if doc_pages_ocr else 1),
                    "method": roles.get("evidence", {}).get("role_method", {}).get("witness", "cnic_fallback"),
                },
            }
            
            # P20: Track roles present/missing with reasons
            roles_present = []
            roles_missing = []
            missing_reasons = {}
            
            # P20: Process ALL roles (seller, buyer, witness) in deterministic order
            for role in ["seller", "buyer", "witness"]:
                role_data = normalized_roles[role]
                val = role_data["value"]
                # P23: Normalize party role value at source (already normalized in extractor, but ensure it's clean)
                from app.services.extractors.party_roles import normalize_party_role_value
                val = normalize_party_role_value(val)
                
                # Determine field path and confidence based on role
                if role == "seller":
                    field_path = 'party.seller.names'
                    if role_data["method"] == "label_urdu":
                        confidence = 0.92
                    elif role_data["method"] == "anchor":
                        confidence = 0.90
                    elif role_data["method"] == "section_cnic":
                        confidence = 0.85
                    else:
                        confidence = 0.70
                elif role == "buyer":
                    field_path = 'party.buyer.names'
                    if role_data["method"] == "label_urdu":
                        confidence = 0.92
                    elif role_data["method"] == "anchor":
                        confidence = 0.90
                    elif role_data["method"] == "section_cnic":
                        confidence = 0.85
                    else:
                        confidence = 0.70
                else:  # witness
                    field_path = 'party.witness.names'
                    if role_data["method"] == "label_urdu":
                        confidence = 0.88
                    elif role_data["method"] == "anchor":
                        confidence = 0.85
                    elif role_data["method"] == "section_cnic":
                        confidence = 0.80
                    else:
                        confidence = 0.65
                
                # Check if role value is empty
                if not val or not val.strip():
                    missing_reasons[role] = "empty_extraction"
                    roles_missing.append(role)
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] party_role_candidate role={role} doc_id={doc.id} "
                        f"ok=False reason=empty_extraction value_preview=\"\""
                    )
                    continue  # Skip empty roles
                
                # Validate with is_plausible_party_name
                from app.services.extractors.validators import is_plausible_party_name
                is_valid, validation_reason = is_plausible_party_name(val, role=role)
                
                logger.info(
                    f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] party_role_candidate role={role} doc_id={doc.id} "
                    f"ok={is_valid} reason={validation_reason or 'none'} value_preview=\"{val[:40]}\""
                )
                
                if not is_valid:
                    missing_reasons[role] = validation_reason or "validation_failed"
                    roles_missing.append(role)
                    continue  # Skip invalid roles
                
                # Add to all_extractions
                roles_present.append(role)
                if field_path not in all_extractions:
                    all_extractions[field_path] = []
                
                # Find snippet in OCR text for start/end indices
                combined_text = '\n'.join([p.text for p in doc_pages_ocr])
                snippet = roles.get("evidence", {}).get("snippet", "") or val
                snippet_start = combined_text.find(snippet) if snippet else 0
                snippet_end = snippet_start + len(snippet) if snippet_start >= 0 else len(combined_text)
                
                all_extractions[field_path].append((
                    val,
                    confidence,
                    doc.id,
                    role_data["page"],
                    snippet_start if snippet_start >= 0 else 0,
                    snippet_end,
                ))
            
            # P20: Log summary of roles collected
            logger.info(
                f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] party_roles_collected doc_id={doc.id} count={len(roles_present)} "
                f"roles_present={roles_present} roles_missing={roles_missing} missing_reasons={missing_reasons}"
            )
            
            # P20: All roles (seller, buyer, witness) now processed above in deterministic loop
            # Legacy code removed
    except Exception as e:
        logger.exception(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] EXCEPTION stage=party_roles {repr(e)}")
        raise
    
    # B. Immediately after party roles extraction
    party_role_extractions = []
    party_role_items = []  # P19: Detailed list for logging
    for field_key in ['party.seller.names', 'party.buyer.names', 'party.witness.names']:
        if field_key in all_extractions:
            for value, confidence, doc_id, page_num, start_idx, end_idx in all_extractions[field_key]:
                party_role_extractions.append((field_key, doc_id, page_num, value[:80]))
                # P19: Track detailed info for logging
                role_method = "unknown"
                if field_key == 'party.seller.names':
                    role_method = "seller"
                elif field_key == 'party.buyer.names':
                    role_method = "buyer"
                elif field_key == 'party.witness.names':
                    role_method = "witness"
                party_role_items.append({
                    "field_key": field_key,
                    "doc_id": str(doc_id),
                    "page_no": page_num,
                    "value_preview": value[:40] if value else "",
                    "method": role_method
                })
    
    # P19: Log detailed party role items count
    party_role_items_count = len(party_role_items)
    docs_with_party_roles = set()
    for item in party_role_items:
        docs_with_party_roles.add(item["doc_id"])
    
    # ALWAYS log (forced observability)
    total_party_extractions = len(party_role_extractions)
    logger.info(
        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] EXIT party roles loop total_party_extractions={total_party_extractions} "
        f"party_role_items_count={party_role_items_count} "
        f"all_extractions_keys={list(all_extractions.keys())}"
    )
    
    # P19: Log detailed party role items
    if party_role_items_count > 0:
        logger.info(
            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] party_role_items_detail: "
            f"{[(item['field_key'], item['doc_id'], item['page_no'], item['value_preview'], item['method']) for item in party_role_items]}"
        )
    
    if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
        logger.info(
            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] Before processing loop, all_extractions has {len(all_extractions)} fields: {list(all_extractions.keys())}"
        )
    
    # C. Immediately before the DB processing loop
    # P19: ALWAYS log (forced observability) - ENTER write loop with accurate counts
    party_fields = [k for k in all_extractions.keys() if k.startswith('party.')]
    total_candidates_overall = sum(len(v) for v in all_extractions.values())
    party_field_keys_present = [k for k in party_fields if k in ['party.seller.names', 'party.buyer.names', 'party.witness.names']]
    logger.info(
        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] ENTER write loop total_candidates_overall={total_candidates_overall} "
        f"party_role_items_count={party_role_items_count} "
        f"party_field_keys_present={party_field_keys_present} "
        f"docs_with_party_roles_count={len(docs_with_party_roles)} "
        f"total_fields={len(all_extractions)}"
    )
    for field_path, extractions in all_extractions.items():
        if not extractions:
            if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                logger.info(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={field_path} skipped (empty extractions)")
            continue
        
        # Party role fields: keep all (one per document, already consolidated)
        # Other fields: pick best extraction
        is_party_role_field = field_path in ['party.seller.names', 'party.buyer.names', 'party.witness.names']
        
        if is_party_role_field:
            # For party role fields, process each extraction (one per document)
            for value, confidence, doc_id, page_num, start_idx, end_idx in extractions:
                # P23: Keep original raw value and normalize (belt+suspenders)
                original_raw_value = value
                # Normalize: strip + replace newlines + collapse spaces
                cleaned_raw = (value or "").replace("\r", " ").replace("\n", " ")
                import re
                cleaned_raw = re.sub(r"[ \t\f\v]+", " ", cleaned_raw).strip()
                
                # Write-path observability: log before validation
                if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={field_path} doc_id={doc_id} "
                        f"raw_value=\"{value}\" cleaned_raw=\"{cleaned_raw}\" confidence={confidence} page={page_num}"
                    )
                # Get OCR text for snippet
                ocr_text_for_snippet = None
                for d_id, p_num, ocr in pages_data:
                    if d_id == doc_id and p_num == page_num:
                        ocr_text_for_snippet = ocr
                        break
                
                if not ocr_text_for_snippet:
                    if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                        logger.warning(
                            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={field_path} doc_id={doc_id} page={page_num} "
                            f"SKIPPED: OCR text not found in pages_data"
                        )
                    continue
                
                snippet = extract_snippet(ocr_text_for_snippet, start_idx, end_idx)
                
                # Normalize confidence
                from app.services.ocr_engine import normalize_confidence
                confidence_normalized = normalize_confidence(confidence)
                
                # Include names_list in evidence metadata if available
                evidence_metadata = {
                    "document_id": str(doc_id),
                    "page_number": page_num,
                    "snippet": snippet,
                    "snippet_start_idx": start_idx,
                    "snippet_end_idx": end_idx,
                    # P23: Store original and cleaned values for audit
                    "raw_value_original": original_raw_value,
                    "raw_value": cleaned_raw,
                }
                
                # Get names_list from roles extraction
                for doc in documents:
                    if doc.id == doc_id and doc.id in pages_by_document:
                        from app.services.extractors.party_roles import extract_party_roles_from_document, PageOCR
                        doc_pages_ocr = []
                        for p_num, text in pages_by_document[doc.id]:
                            doc_pages_ocr.append(PageOCR(
                                document_id=str(doc.id),
                                document_name=doc.original_filename or "",
                                page_number=p_num,
                                text=text
                            ))
                        roles = extract_party_roles_from_document(doc_pages_ocr)
                        if roles.get("names_list"):
                            role_key = "seller" if field_path == "party.seller.names" else ("buyer" if field_path == "party.buyer.names" else "witness")
                            if role_key in roles["names_list"]:
                                evidence_metadata["names_list"] = roles["names_list"][role_key]
                        break
                
                # P23: Use cleaned_raw as the value (will be normalized again by gate)
                extracted_fields.append(ExtractedField(
                    field_path=field_path,
                    value=cleaned_raw,
                    confidence=confidence_normalized,
                    evidence=evidence_metadata
                ))
        else:
            # For other fields, pick best extraction (highest confidence)
            best = max(extractions, key=lambda x: x[1])  # x[1] is confidence
            value, confidence, doc_id, page_num, start_idx, end_idx = best
            
            # Normalize confidence to 0.0-1.0 before creating ExtractedField
            from app.services.ocr_engine import normalize_confidence
            confidence_normalized = normalize_confidence(confidence)
            
            # Get OCR text for snippet
            ocr_text_for_snippet = None
            for d_id, p_num, ocr in pages_data:
                if d_id == doc_id and p_num == page_num:
                    ocr_text_for_snippet = ocr
                    break
            
            if not ocr_text_for_snippet:
                continue
            
            snippet = extract_snippet(ocr_text_for_snippet, start_idx, end_idx)
            
            extracted_fields.append(ExtractedField(
                field_path=field_path,
                value=value,
                confidence=confidence_normalized,
                evidence={
                    "document_id": str(doc_id),
                    "page_number": page_num,
                    "snippet": snippet,
                    "snippet_start_idx": start_idx,
                    "snippet_end_idx": end_idx,
                }
            ))
    
    # P16: Write HF Extractor entities to ocr_extraction_candidates
    hf_entities_written = 0
    hf_entities_deduped = 0
    hf_entities_by_label: Dict[str, int] = {}  # Track counts by label
    
    # Map entity labels to field keys
    LABEL_TO_FIELD_KEY = {
        "CNIC": "party.cnic",
        "PLOT_NO": "property.plot_number",
        "SCHEME_NAME": "property.scheme_name",
        "REGISTRY_NO": "registry.registry_number",  # Or document.registry_number if preferred
        "DATE": "document.execution_date",  # Or closest existing date field
        "AMOUNT": "consideration.amount",  # Or closest existing amount field
    }
    
    for (doc_id, page_num), entities in hf_entities_by_page.items():
        for entity in entities:
            # Track entity by label
            label = entity.label
            hf_entities_by_label[label] = hf_entities_by_label.get(label, 0) + 1
            
            # Map label to field_key
            field_key = LABEL_TO_FIELD_KEY.get(label)
            if not field_key:
                if DOSSIER_AUTOFILL_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor SKIPPED unmapped label={label} "
                        f"doc_id={doc_id} page_no={page_num}"
                    )
                continue  # Skip unmapped labels
            
            # P16: Apply candidate gate (validate and normalize)
            raw_value = entity.value
            gate_ok, normalized_value, gate_reason = normalize_and_validate_candidate(field_key, raw_value)
            
            if not gate_ok:
                if DOSSIER_AUTOFILL_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] gate_skip field_key={field_key} reason={gate_reason} "
                        f"raw_preview={raw_value[:40]} doc_id={doc_id} page_no={page_num} label={label}"
                    )
                continue  # Skip invalid candidates
            
            # Build evidence_json with extractor version, normalization info, and OCR metadata
            # P17/P19: OCR and quality metadata from entity.ocr_metadata and entity.quality_metadata
            extractor_version_used = getattr(entity, 'quality_metadata', {}).get("extractor_version_used") or "rules-v1"
            model_name_or_path = getattr(entity, 'quality_metadata', {}).get("model_name_or_path")
            
            # P19: Check for low_confidence flag (LayoutXLM entities may have this attribute)
            low_confidence = getattr(entity, 'low_confidence', None)
            
            evidence_json = {
                "extractor": "hf-extractor",
                "model": "microsoft/layoutxlm-base" if extractor_version_used == "layoutxlm-v1" else "rules-v1",
                "label": label,
                "token_indices": entity.source.get("token_indices", []),
                "bbox": entity.source.get("bbox"),  # P12: Can be None for text-only OCR
                "bbox_norm_1000": entity.source.get("bbox_norm_1000"),  # P12: Can be None
                "span_start": entity.source.get("span_start"),  # P12: Character offset start (for text-only OCR)
                "span_end": entity.source.get("span_end"),  # P12: Character offset end (for text-only OCR)
                "snippet": entity.evidence.get("snippet", ""),
                "ocr_engine": entity.source.get("ocr_engine", "unknown"),
                "extractor_version": extractor_version_used,  # P19: Dynamic version (rules-v1 or layoutxlm-v1)
                "raw_value": raw_value,  # P16: Store raw value before normalization
                "normalized_value": normalized_value,  # P16: Store normalized value
                # P17: OCR routing metadata
                "ocr_page_confidence": getattr(entity, 'ocr_metadata', {}).get("ocr_page_confidence"),
                "ocr_used_fallback": getattr(entity, 'ocr_metadata', {}).get("ocr_used_fallback"),
                "ocr_engine_params": getattr(entity, 'ocr_metadata', {}).get("ocr_engine_params"),
                # P19: Quality and model metadata
                "extractor_version_used": extractor_version_used,
                "model_name_or_path": model_name_or_path,
                # P12: Qaari OCR metadata
                "qaari_used": getattr(entity, 'quality_metadata', {}).get("qaari_used"),
                "ocr_text_only": getattr(entity, 'quality_metadata', {}).get("ocr_text_only"),
                "qaari_model_name_or_path": getattr(entity, 'quality_metadata', {}).get("qaari_model_name_or_path"),
            }
            
            # P19: Add low_confidence flag if present
            if low_confidence is not None:
                evidence_json["low_confidence"] = low_confidence
            
            # Check for duplicate: same (document_id, field_key, proposed_value, page_number, extraction_method)
            # Use normalized_value for deduplication
            existing_hf = db.query(OCRExtractionCandidate).filter(
                OCRExtractionCandidate.document_id == doc_id,
                OCRExtractionCandidate.org_id == org_id,
                OCRExtractionCandidate.field_key == field_key,
                OCRExtractionCandidate.proposed_value == normalized_value,  # P16: Use normalized value for dedup
                OCRExtractionCandidate.page_number == page_num,
                OCRExtractionCandidate.extraction_method == "hf_extractor",
            ).first()
            
            if existing_hf:
                hf_entities_deduped += 1
                if DOSSIER_AUTOFILL_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor DEDUPED doc_id={doc_id} "
                        f"page_no={page_num} field_key={field_key} label={label} "
                        f"value={normalized_value[:40]}"
                    )
                continue
            
            # Create new candidate with normalized value
            new_candidate = OCRExtractionCandidate(
                org_id=org_id,
                case_id=case_id,
                document_id=doc_id,
                page_number=page_num,
                field_key=field_key,
                proposed_value=normalized_value,  # P16: Use normalized value
                confidence=float(entity.confidence),
                snippet=entity.evidence.get("snippet", ""),
                status="Pending",
                extraction_method="hf_extractor",
                evidence_json=evidence_json,
            )
            db.add(new_candidate)
            hf_entities_written += 1
            
            if DOSSIER_AUTOFILL_DEBUG:
                logger.info(
                    f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor WRITTEN doc_id={doc_id} "
                    f"page_no={page_num} field_key={field_key} label={label} "
                    f"value={normalized_value[:40]} confidence={entity.confidence} "
                    f"raw_value={raw_value[:40] if raw_value != normalized_value else 'same'}"
                )
    
    # Enhanced logging with breakdown by label
    if DOSSIER_AUTOFILL_DEBUG or True:  # Always log summary
        logger.info(
            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] hf_extractor summary "
            f"entities_received_total={hf_entities_received} "
            f"entities_written_total={hf_entities_written} "
            f"entities_deduped_total={hf_entities_deduped} "
            f"breakdown_by_label={hf_entities_by_label}"
        )
    
    # Create OCR extraction candidates (respect overwrite flag, with deduplication)
    updated_fields = []
    skipped_fields = []
    
    # Counters for party role fields
    attempted_party = 0
    skipped_party = 0
    written_party = 0
    
    # Dedupe: track normalized values per field_key
    seen_normalized: Dict[str, set] = {}  # field_key -> set of normalized values
    
    # Wrap persistence in try/except for exception tracking
    try:
        # Write loop starts here
        for ef in extracted_fields:
            # Normalize value for deduplication (whitespace + casefold)
            normalized_value = normalize_whitespace(ef.value).lower()
            
            # Check for duplicate (same field_key + normalized_value)
            if ef.field_path not in seen_normalized:
                seen_normalized[ef.field_path] = set()
            
            if normalized_value in seen_normalized[ef.field_path]:
                # Skip duplicate
                continue
            
            seen_normalized[ef.field_path].add(normalized_value)
            
            # Check if there's already a pending candidate for this field (by normalized value)
            existing_candidate = db.query(OCRExtractionCandidate).filter(
                OCRExtractionCandidate.case_id == case_id,
                OCRExtractionCandidate.org_id == org_id,
                OCRExtractionCandidate.field_key == ef.field_path,
                OCRExtractionCandidate.status == "Pending",
            ).first()
            
            # Also check for duplicate by normalized value in existing candidates
            if not existing_candidate:
                all_candidates = db.query(OCRExtractionCandidate).filter(
                    OCRExtractionCandidate.case_id == case_id,
                    OCRExtractionCandidate.org_id == org_id,
                    OCRExtractionCandidate.field_key == ef.field_path,
                ).all()
                for cand in all_candidates:
                    cand_normalized = normalize_whitespace(cand.proposed_value or "").lower()
                    if cand_normalized == normalized_value:
                        existing_candidate = cand
                        break
            
            # Check if dossier field already exists and has value
            existing_dossier_field = db.query(CaseDossierField).filter(
                CaseDossierField.case_id == case_id,
                CaseDossierField.org_id == org_id,
                CaseDossierField.field_key == ef.field_path,
            ).first()
            
            if existing_dossier_field and existing_dossier_field.field_value and not overwrite:
                skipped_fields.append(ef.field_path)
                continue
            
            # P16: Apply candidate gate first (validate and normalize)
            raw_value = ef.value
            gate_ok, normalized_value, gate_reason = normalize_and_validate_candidate(ef.field_path, raw_value)
            
            if not gate_ok:
                if DOSSIER_AUTOFILL_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] gate_skip field_key={ef.field_path} reason={gate_reason} "
                        f"raw_preview={raw_value[:40]} cleaned_preview={raw_value[:40]} "
                        f"doc_id={ef.evidence.get('document_id')} page={ef.evidence.get('page_number')}"
                    )
                continue  # Skip invalid candidates
            
            # P14: Validate field value before creating candidate (continue with existing validator logic)
            validator = get_field_validator(ef.field_path)
            validation_passed = True
            validation_warning = None
            validated_value = normalized_value  # Start with gate-normalized value
            
            if validator:
                if validator == is_probably_name_line:
                    # Name validator returns (bool, warning)
                    # For party role fields, use role-aware validation
                    is_party_role_field = ef.field_path in ['party.seller.names', 'party.buyer.names', 'party.witness.names']
                    if is_party_role_field:
                        from app.services.extractors.validators import is_plausible_party_name
                        role = "seller" if "seller" in ef.field_path else ("buyer" if "buyer" in ef.field_path else "witness")
                        is_valid, warning = is_plausible_party_name(normalized_value, role=role)  # Use gate-normalized value
                    else:
                        is_valid, warning = validator(normalized_value)  # Use gate-normalized value
                    validation_passed = is_valid
                    validation_warning = warning
                else:
                    # Other validators return (bool, normalized_value, warning)
                    is_valid, normalized, warning = validator(ef.value)
                    validation_passed = is_valid
                    if is_valid and normalized:
                        validated_value = normalized
                    validation_warning = warning
            
            # D. Inside the loop, for each party role extraction
            is_party_role_field = ef.field_path in ['party.seller.names', 'party.buyer.names', 'party.witness.names']
            if is_party_role_field:
                attempted_party += 1
            
            if is_party_role_field:
                skip_reason = None
                if not validation_passed:
                    skip_reason = f"validation_failed: {validation_warning or 'unknown'}"
                elif not validated_value or not validated_value.strip():
                    skip_reason = "empty_after_clean"
                # ALWAYS log for party role fields (forced observability)
                logger.info(
                    f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] write_loop field_key={ef.field_path} doc_id={ef.evidence.get('document_id')} "
                    f"raw_value_preview=\"{ef.value[:60]}\" cleaned_value_preview=\"{validated_value[:60] if validated_value else ''}\" "
                    f"is_plausible_party_name={validation_passed} skip_reason={skip_reason or 'none'}"
                )
            
            # P14: If validation fails, skip creating candidate (zero garbage)
            if not validation_passed:
                if is_party_role_field:
                    skipped_party += 1
                    role = "seller" if "seller" in ef.field_path else ("buyer" if "buyer" in ef.field_path else "witness")
                    # P16: Enhanced SKIP logging with role
                    if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                        logger.info(
                            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] SKIP role={role} field={ef.field_path} doc_id={ef.evidence.get('document_id')} "
                            f"reason={validation_warning or 'validation_failed'} raw_value_preview=\"{ef.value[:60]}\""
                        )
                continue
            
            # P10: Check OCR quality for this document
            doc_id_uuid = uuid.UUID(ef.evidence["document_id"])
            quality_level, quality_reasons = get_document_ocr_quality(db, org_id, doc_id_uuid)
            is_low_quality = quality_level != "Good"
            warning_reason = "; ".join(quality_reasons) if quality_reasons else None
            
            # P14: Combine validation warning with quality warning
            if validation_warning:
                if warning_reason:
                    warning_reason = f"{warning_reason}; Field validation weak: {validation_warning}"
                else:
                    warning_reason = f"Field validation weak: {validation_warning}"
            
            # Normalize confidence one more time before persisting (safety check)
            from app.services.ocr_engine import normalize_confidence
            final_confidence = normalize_confidence(ef.confidence)
            
            # If candidate exists, update it; otherwise create new
            if existing_candidate:
                # Write-path observability: log update
                if (DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG) and is_party_role_field:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={ef.field_path} doc_id={doc_id_uuid} "
                        f"action=UPDATE existing_id={existing_candidate.id} overwrite={overwrite} "
                        f"value=\"{validated_value[:80]}\""
                    )
                existing_candidate.proposed_value = validated_value  # P14: Use validated/normalized value
                existing_candidate.confidence = final_confidence
                existing_candidate.snippet = ef.evidence.get("snippet")
                existing_candidate.document_id = doc_id_uuid
                existing_candidate.page_number = ef.evidence["page_number"]
                existing_candidate.quality_level_at_create = quality_level
                existing_candidate.is_low_quality = is_low_quality
                existing_candidate.warning_reason = warning_reason
                existing_candidate.updated_at = datetime.utcnow()
                # P20: Set run_id on update
                if is_party_role_field:
                    existing_candidate.run_id = request_id
            else:
                # Write-path observability: log creation
                if (DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG) and is_party_role_field:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={ef.field_path} doc_id={doc_id_uuid} "
                        f"action=CREATE overwrite={overwrite} value=\"{validated_value[:80]}\" "
                        f"page={ef.evidence['page_number']} confidence={final_confidence}"
                    )
                # P16/P23: Build evidence_json with raw_value and normalized_value if not already present
                evidence_json = {}
                if hasattr(ef, 'evidence_json') and ef.evidence_json:
                    evidence_json = ef.evidence_json.copy()
                elif 'evidence_json' in ef.evidence:
                    evidence_json = ef.evidence.get('evidence_json', {}).copy()
                # P23: For party roles, include original_raw_value, raw_value (cleaned), and normalized_value
                if is_party_role_field:
                    evidence_json["raw_value_original"] = ef.evidence.get("raw_value_original", ef.value)
                    evidence_json["raw_value"] = ef.evidence.get("raw_value", ef.value)
                    evidence_json["normalized_value"] = validated_value  # gate_normalized (or cleaned_raw)
                else:
                    evidence_json["raw_value"] = ef.value  # P16: Store raw value
                    evidence_json["normalized_value"] = validated_value  # P16: Store normalized value
                
                new_candidate = OCRExtractionCandidate(
                    org_id=org_id,
                    case_id=case_id,
                    document_id=doc_id_uuid,
                    page_number=ef.evidence["page_number"],
                    field_key=ef.field_path,
                    proposed_value=validated_value,  # P14: Use validated/normalized value
                    confidence=final_confidence,
                    snippet=ef.evidence.get("snippet"),
                    status="Pending",
                    quality_level_at_create=quality_level,
                    is_low_quality=is_low_quality,
                    warning_reason=warning_reason,
                    evidence_json=evidence_json if evidence_json else None,  # P16: Include evidence_json
                    run_id=request_id if is_party_role_field else None,  # P20: Set run_id for party roles
                )
                db.add(new_candidate)
            
            updated_fields.append(ef.field_path)
            if is_party_role_field:
                written_party += 1
                # Flush to get candidate ID
                db.flush()
                candidate_id = new_candidate.id if not existing_candidate else existing_candidate.id
                if DOSSIER_AUTOFILL_DEBUG or PARTY_ROLES_DEBUG:
                    logger.info(
                        f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] field={ef.field_path} WRITTEN candidate_id={candidate_id} "
                        f"run_id={request_id} table={OCRExtractionCandidate.__tablename__}"
                    )
        
        # E. After loop - ALWAYS log (forced observability)
        logger.info(
            f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] EXIT write loop attempted_party={attempted_party} "
            f"skipped_party={skipped_party} written_party={written_party}"
        )
        
        # F. Exception handling and commit
        try:
            logger.info(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] COMMIT starting")
            db.commit()
            
            # Log table name and record count after commit
            # OCRExtractionCandidate is already imported at top of file
            written_count = db.query(OCRExtractionCandidate).filter(
                OCRExtractionCandidate.case_id == case_id,
                OCRExtractionCandidate.org_id == org_id,
            ).count()
            party_count = db.query(OCRExtractionCandidate).filter(
                OCRExtractionCandidate.case_id == case_id,
                OCRExtractionCandidate.org_id == org_id,
                OCRExtractionCandidate.field_key.in_(['party.seller.names', 'party.buyer.names', 'party.witness.names']),
            ).count()
            logger.info(
                f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] COMMIT done table={OCRExtractionCandidate.__tablename__} "
                f"attempted_party={attempted_party} written_party={written_party} skipped_party={skipped_party} "
                f"total_records={written_count} party_role_records={party_count}"
            )
        except Exception as e:
            logger.exception(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] EXCEPTION stage=commit {repr(e)}")
            db.rollback()
            raise
    
    except Exception as e:
        logger.exception(f"DOSSIER_AUTOFILL_DEBUG: [{request_id}] EXCEPTION stage=write_loop {repr(e)}")
        db.rollback()
        raise
    
    return {
        "extracted": [
            {
                "field_path": ef.field_path,
                "value": ef.value,
                "confidence": ef.confidence,
                "evidence": ef.evidence,
            }
            for ef in extracted_fields
        ],
        "updated_fields": updated_fields,
        "skipped_fields": skipped_fields,
        "errors": errors,
    }

