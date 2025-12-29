"""Extraction service for extracting structured data from OCR text."""
import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedField:
    """Represents an extracted field from OCR text."""
    field_key: str
    field_value: str
    source_document_id: Optional[uuid.UUID] = None
    source_page_number: Optional[int] = None
    confidence: Optional[float] = None


# CNIC patterns
# Format: 12345-1234567-1 or 1234512345671 (13 digits)
CNIC_PATTERN_FORMATTED = re.compile(r'\b(\d{5}-\d{7}-\d)\b')
CNIC_PATTERN_UNFORMATTED = re.compile(r'\b(\d{13})\b')

# Party name heuristics - look for common patterns
NAME_PATTERNS = [
    re.compile(r'(?:Name|نام)\s*[:\-]?\s*(.+)', re.IGNORECASE),
    re.compile(r'(?:Mr\.|Mrs\.|Ms\.|Miss)\s+([A-Za-z\s]+)', re.IGNORECASE),
    re.compile(r'(?:S/o|D/o|W/o|Son of|Daughter of|Wife of)\s+(.+)', re.IGNORECASE),
    re.compile(r'(?:Borrower|Applicant|Customer)\s*[:\-]?\s*(.+)', re.IGNORECASE),
]

# Property patterns - society, block, plot, phase
SOCIETY_PATTERNS = [
    re.compile(r'(?:Society|Housing Society|HS)\s*[:\-]?\s*([A-Za-z0-9\s\-]+)', re.IGNORECASE),
    re.compile(r'(DHA|Bahria Town|Gulberg|Model Town|Johar Town|Garden Town)', re.IGNORECASE),
]

BLOCK_PATTERNS = [
    re.compile(r'(?:Block|Sector)\s*[:\-]?\s*([A-Za-z0-9]+)', re.IGNORECASE),
]

PLOT_PATTERNS = [
    re.compile(r'(?:Plot|Plot No\.?|Plot #)\s*[:\-]?\s*([A-Za-z0-9\-/]+)', re.IGNORECASE),
    re.compile(r'(?:House|House No\.?|House #)\s*[:\-]?\s*([A-Za-z0-9\-/]+)', re.IGNORECASE),
]

PHASE_PATTERNS = [
    re.compile(r'(?:Phase)\s*[:\-]?\s*([A-Za-z0-9]+)', re.IGNORECASE),
]

# Risk keywords
RISK_KEYWORDS = [
    'litigation', 'dispute', 'lawsuit', 'court', 'legal action',
    'encumbrance', 'lien', 'mortgage', 'pledge',
    'fraud', 'forgery', 'fake', 'invalid',
    'disputed', 'contested', 'objection',
]


def extract_cnics(text: str, document_id: Optional[uuid.UUID] = None, page_number: Optional[int] = None) -> List[ExtractedField]:
    """Extract CNIC numbers from text."""
    fields = []
    seen = set()
    
    # Find formatted CNICs
    for match in CNIC_PATTERN_FORMATTED.finditer(text):
        cnic = match.group(1)
        if cnic not in seen:
            seen.add(cnic)
            fields.append(ExtractedField(
                field_key="party.cnic",
                field_value=cnic,
                source_document_id=document_id,
                source_page_number=page_number,
                confidence=0.9,
            ))
    
    # Find unformatted CNICs (13 consecutive digits)
    for match in CNIC_PATTERN_UNFORMATTED.finditer(text):
        digits = match.group(1)
        # Format as standard CNIC
        formatted = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
        if formatted not in seen:
            seen.add(formatted)
            fields.append(ExtractedField(
                field_key="party.cnic",
                field_value=formatted,
                source_document_id=document_id,
                source_page_number=page_number,
                confidence=0.7,  # Lower confidence for unformatted
            ))
    
    return fields


def extract_party_names(text: str, document_id: Optional[uuid.UUID] = None, page_number: Optional[int] = None) -> List[ExtractedField]:
    """Extract party names from text using heuristics."""
    fields = []
    seen = set()
    
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            # Clean up the name
            name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
            name = name[:100]  # Limit length
            
            if name and name.lower() not in seen and len(name) > 2:
                seen.add(name.lower())
                fields.append(ExtractedField(
                    field_key="party.name.raw",
                    field_value=name,
                    source_document_id=document_id,
                    source_page_number=page_number,
                    confidence=0.5,  # Names are often noisy
                ))
    
    return fields


def extract_property_info(text: str, document_id: Optional[uuid.UUID] = None, page_number: Optional[int] = None) -> List[ExtractedField]:
    """Extract property information (society, block, plot, phase)."""
    fields = []
    
    # Extract society
    for pattern in SOCIETY_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value and len(value) > 1:
                fields.append(ExtractedField(
                    field_key="property.society",
                    field_value=value,
                    source_document_id=document_id,
                    source_page_number=page_number,
                    confidence=0.7,
                ))
                break  # Take first match
    
    # Extract block
    for pattern in BLOCK_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value and len(value) > 0:
                fields.append(ExtractedField(
                    field_key="property.block",
                    field_value=value,
                    source_document_id=document_id,
                    source_page_number=page_number,
                    confidence=0.7,
                ))
                break
    
    # Extract plot
    for pattern in PLOT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value and len(value) > 0:
                fields.append(ExtractedField(
                    field_key="property.plot",
                    field_value=value,
                    source_document_id=document_id,
                    source_page_number=page_number,
                    confidence=0.7,
                ))
                break
    
    # Extract phase
    for pattern in PHASE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value and len(value) > 0:
                fields.append(ExtractedField(
                    field_key="property.phase",
                    field_value=value,
                    source_document_id=document_id,
                    source_page_number=page_number,
                    confidence=0.7,
                ))
                break
    
    return fields


def extract_risk_keywords(text: str, document_id: Optional[uuid.UUID] = None, page_number: Optional[int] = None) -> List[ExtractedField]:
    """Detect risk keywords in text."""
    fields = []
    text_lower = text.lower()
    
    found_keywords = []
    for keyword in RISK_KEYWORDS:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)
    
    if found_keywords:
        fields.append(ExtractedField(
            field_key="risk.keywords",
            field_value=", ".join(found_keywords),
            source_document_id=document_id,
            source_page_number=page_number,
            confidence=0.8,
        ))
    
    return fields


def extract_all_from_text(
    text: str, 
    document_id: Optional[uuid.UUID] = None, 
    page_number: Optional[int] = None
) -> List[ExtractedField]:
    """Run all extractors on a single piece of text."""
    fields = []
    fields.extend(extract_cnics(text, document_id, page_number))
    fields.extend(extract_party_names(text, document_id, page_number))
    fields.extend(extract_property_info(text, document_id, page_number))
    fields.extend(extract_risk_keywords(text, document_id, page_number))
    return fields


def extract_from_case_pages(
    pages_data: List[Tuple[uuid.UUID, int, str]]
) -> List[ExtractedField]:
    """
    Extract fields from all pages of all documents in a case.
    
    Args:
        pages_data: List of (document_id, page_number, ocr_text) tuples
        
    Returns:
        List of extracted fields
    """
    all_fields = []
    
    for doc_id, page_num, text in pages_data:
        if text:
            fields = extract_all_from_text(text, doc_id, page_num)
            all_fields.extend(fields)
    
    return all_fields


def deduplicate_fields(fields: List[ExtractedField]) -> List[ExtractedField]:
    """
    Deduplicate extracted fields, keeping the highest confidence for each unique value.
    """
    seen: Dict[Tuple[str, str], ExtractedField] = {}
    
    for field in fields:
        key = (field.field_key, field.field_value.lower())
        if key not in seen or (field.confidence or 0) > (seen[key].confidence or 0):
            seen[key] = field
    
    return list(seen.values())

