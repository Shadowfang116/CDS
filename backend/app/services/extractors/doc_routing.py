"""Document-class routing for autofill extractors."""
from __future__ import annotations

from typing import Optional


PARTY_ROLE_CLASSES = frozenset({"sale_deed"})
PLOT_BLOCK_CLASSES = frozenset({
    "sale_deed",
    "mutation",
    "tax",
    "valuation",
    "possession",
    "title_search",
    "fard",
    "other",
})
CNIC_CLASSES = frozenset({"cnic"})
BUYER_CORROBORATION_CLASSES = frozenset({"board", "facility"})

STRONG_SALE_DEED_MARKERS = (
    "بیع نامہ",
    "فروخت نامہ",
    "sale deed",
    "deed of sale",
    "فروخت کنندہ",
)
MUTATION_MARKERS = (
    "mutation",
    "intiqal",
    "انتقال",
    "منتقل کنندہ",
    "منتقل الیہ",
)
_COARSE_FROM_CANONICAL = {
    "Sale Deed": "sale_deed",
    "Mutation": "mutation",
    "Fard": "fard",
    "CNIC": "cnic",
    "Society/Authority NOC": "other",
    "Search Report": "title_search",
    "Valuation": "valuation",
    "Facility Approval": "facility",
    "Possession Letter": "possession",
    "Property Tax/PT-10": "tax",
    "Board Resolution": "board",
    "Building Plan": "other",
    "Dues Clearance": "other",
    "Charge Release": "other",
    "Identity Confirmation": "other",
}


def classify_document(
    filename: str = "",
    ocr_text: str = "",
    doc_type: Optional[str] = None,
) -> str:
    """Return a coarse doc class used to choose extractors."""
    from app.services.canonical_docs import classify_document_type

    classified, _source = classify_document_type(filename, ocr_text, doc_type)
    if classified in _COARSE_FROM_CANONICAL:
        return _COARSE_FROM_CANONICAL[classified]

    blob = f"{filename or ''} {doc_type or ''}".lower()
    text = ocr_text or ""
    mutation_hits = sum(1 for token in MUTATION_MARKERS if token in blob or token in text)
    sale_hits = sum(1 for token in STRONG_SALE_DEED_MARKERS if token in blob or token in text)

    if mutation_hits and sale_hits == 0:
        return "mutation"
    if sale_hits:
        return "sale_deed"
    if any(token in blob for token in ("pt-10", "pt10", "pt_10", "property_tax", "tax")):
        return "tax"
    if "valuation" in blob:
        return "valuation"
    if "possession" in blob:
        return "possession"
    if "title_search" in blob or "title search" in blob:
        return "title_search"
    if "fard" in blob:
        return "fard"
    if "cnic" in blob:
        return "cnic"
    if any(token in blob for token in ("board", "resolution")):
        return "board"
    if "facility" in blob:
        return "facility"
    return "other"


def allows_party_roles(doc_class: str) -> bool:
    return doc_class in PARTY_ROLE_CLASSES


def allows_plot_block(doc_class: str) -> bool:
    return doc_class in PLOT_BLOCK_CLASSES or doc_class in BUYER_CORROBORATION_CLASSES


def allows_cnic_person(doc_class: str) -> bool:
    return doc_class in CNIC_CLASSES
