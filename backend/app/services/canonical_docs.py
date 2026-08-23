"""Canonical document types for CDS classification and rule matching.

Filename may hint (useful for the labelled test corpus). Production
classification also uses OCR content. Manual corrections are never overwritten.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional, Sequence, Tuple

from sqlalchemy.orm import Session


CANONICAL_TYPES = [
    "Sale Deed",
    "Mutation",
    "Fard",
    "CNIC",
    "Society/Authority NOC",
    "Search Report",
    "Valuation",
    "Facility Approval",
    "Possession Letter",
    "Property Tax/PT-10",
    "Board Resolution",
    "Building Plan",
    "Dues Clearance",
    "Charge Release",
    "Identity Confirmation",
]

# Display name -> matching key used by the rule engine.
CANONICAL_KEYS = {
    "Sale Deed": "sale_deed",
    "Mutation": "mutation",
    "Fard": "fard",
    "CNIC": "cnic_copy",
    "Society/Authority NOC": "society_noc",
    "Search Report": "search_report",
    "Valuation": "valuation",
    "Facility Approval": "facility_approval",
    "Possession Letter": "possession_letter",
    "Property Tax/PT-10": "property_tax",
    "Board Resolution": "board_resolution",
    "Building Plan": "building_plan",
    "Dues Clearance": "dues_clearance",
    "Charge Release": "charge_release",
    "Identity Confirmation": "identity_confirmation",
}

# Any stored or required label collapses to a matching key.
ALIASES = {
    "sale_deed": "sale_deed",
    "sale deed": "sale_deed",
    "registered sale deed": "sale_deed",
    "registered_sale_deed": "sale_deed",
    "registry_deed": "sale_deed",
    "registry_instrument": "sale_deed",
    "registry": "sale_deed",
    "registered deed": "sale_deed",
    "certified_copy": "sale_deed",
    "certified copy": "sale_deed",
    "mutation": "mutation",
    "mutation_entry": "mutation",
    "intiqal": "mutation",
    "fard": "fard",
    "fard e malkiat": "fard",
    "jamabandi": "fard",
    "cnic": "cnic_copy",
    "cnic_copy": "cnic_copy",
    "cnic copy": "cnic_copy",
    "national_id": "cnic_copy",
    "national id": "cnic_copy",
    "society_noc": "society_noc",
    "society noc": "society_noc",
    "society/authority noc": "society_noc",
    "noc": "society_noc",
    "no objection certificate": "society_noc",
    "society approval": "society_noc",
    "transfer noc": "society_noc",
    "search_report": "search_report",
    "search report": "search_report",
    "title search": "search_report",
    "valuation": "valuation",
    "facility_approval": "facility_approval",
    "facility approval": "facility_approval",
    "possession_letter": "possession_letter",
    "possession letter": "possession_letter",
    "possession_affidavit": "possession_letter",
    "handover certificate": "possession_letter",
    "possession certificate": "possession_letter",
    "property_tax": "property_tax",
    "property tax/pt-10": "property_tax",
    "property tax": "property_tax",
    "pt-10": "property_tax",
    "pt10": "property_tax",
    "pt1": "property_tax",
    "pt-1": "property_tax",
    "property_tax_receipt": "property_tax",
    "board_resolution": "board_resolution",
    "board resolution": "board_resolution",
    "company resolution": "board_resolution",
    "corporate authorization": "board_resolution",
    "building_plan": "building_plan",
    "building plan": "building_plan",
    "approved plan": "building_plan",
    "construction plan": "building_plan",
    "dues_clearance": "dues_clearance",
    "dues clearance": "dues_clearance",
    "charge_release": "charge_release",
    "charge release": "charge_release",
    "release letter": "charge_release",
    "identity_confirmation": "identity_confirmation",
    "identity confirmation": "identity_confirmation",
    "name confirmation": "identity_confirmation",
    "photograph": "photograph",
    "photo": "photograph",
    "passport photo": "photograph",
    "salary slip": "salary_slip",
    "salary_slip": "salary_slip",
    "utility bill": "utility_bill",
    "utility_bill": "utility_bill",
    "allotment letter": "allotment_letter",
    "allotment_letter": "allotment_letter",
    "site report": "site_report",
    "site_report": "site_report",
    "site verification": "site_report",
    "property inspection": "site_report",
    "physical verification": "site_report",
    "power of attorney": "power_of_attorney",
    "estamp_certificate": "estamp_certificate",
    "clu": "clu",
}

# Specific-first filename patterns. First match wins.
_FILENAME_PATTERNS: Sequence[Tuple[Tuple[str, ...], str]] = (
    (("identity confirmation", "name confirmation", "identity_name"), "Identity Confirmation"),
    (("charge release", "release letter", "prior_charge_release"), "Charge Release"),
    (("dues clearance", "development charges clearance", "charges_clearance"), "Dues Clearance"),
    (("building plan", "approved_building", "approved plan"), "Building Plan"),
    (("board resolution", "board_resolution"), "Board Resolution"),
    (("facility approval", "facility_approval"), "Facility Approval"),
    (("search report", "search_report", "title_search", "title search"), "Search Report"),
    (("possession letter", "possession_letter"), "Possession Letter"),
    (("registered_sale", "sale_deed", "sale deed", "registry deed"), "Sale Deed"),
    (("pt-10", "pt10", "property_tax", "property tax"), "Property Tax/PT-10"),
    (("valuation",), "Valuation"),
    (("mutation", "intiqal"), "Mutation"),
    (("fard",), "Fard"),
    (("cnic", "nic", "id card"), "CNIC"),
    (("noc", "no objection"), "Society/Authority NOC"),
    (("photograph", "passport photo"), "Photograph"),
    (("salary", "payslip", "pay slip"), "Salary Slip"),
    (("utility bill", "electricity bill", "gas bill", "water bill"), "Utility Bill"),
    (("allotment letter", "plot allotment"), "Allotment Letter"),
    (("site report", "site verification"), "Site Report"),
    (("power of attorney", "wakalatnama"), "Power of Attorney"),
    (("e-stamp", "estamp", "stamp certificate"), "estamp_certificate"),
    (("clu", "land conversion"), "CLU"),
)

_CONTENT_PATTERNS: Sequence[Tuple[Tuple[str, ...], str]] = (
    (("بیع نامہ", "فروخت نامہ", "sale deed", "deed of sale", "فروخت کنندہ"), "Sale Deed"),
    (("انتقال", "منتقل کنندہ", "منتقل الیہ", "mutation", "intiqal"), "Mutation"),
    (("فرد", "fard", "fard-e-malkiat"), "Fard"),
    (("possession letter", "قبضہ", "handover letter"), "Possession Letter"),
    (("search report", "title search", "encumbrance search"), "Search Report"),
    (("no objection", "این او سی", "noc"), "Society/Authority NOC"),
    (("valuation", "مالیت", "market value"), "Valuation"),
    (("facility approval", "facility sanctioned"), "Facility Approval"),
    (("board resolution", "بورڈ قرارداد"), "Board Resolution"),
    (("building plan", "نقشہ تعمیر", "approved plan"), "Building Plan"),
    (("dues clearance", "کلیئرنس", "development charges clearance"), "Dues Clearance"),
    (("release of charge", "رہائی", "charge released"), "Charge Release"),
    (("identity confirmation", "name confirmation"), "Identity Confirmation"),
    (("pt-10", "property tax", "پراپرٹی ٹیکس"), "Property Tax/PT-10"),
    (("cnic", "شناختی کارڈ"), "CNIC"),
)

_MUTATION_INDICATORS = (
    "mutation",
    "intiqal",
    "انتقال",
    "منتقل کنندہ",
    "منتقل الیہ",
    "اندراج نمبر",
)

_STRONG_SALE_DEED = (
    "بیع نامہ",
    "فروخت نامہ",
    "sale deed",
    "deed of sale",
    "فروخت کنندہ",
)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def canonical_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if raw in CANONICAL_KEYS:
        return CANONICAL_KEYS[raw]
    lowered = raw.lower()
    if lowered in ALIASES:
        return ALIASES[lowered]
    normalized = _normalize_key(raw).replace("_", " ")
    if normalized in ALIASES:
        return ALIASES[normalized]
    underscored = _normalize_key(raw)
    if underscored in ALIASES:
        return ALIASES[underscored]
    return underscored or None


def canonical_display(value: Optional[str]) -> Optional[str]:
    key = canonical_key(value)
    if not key:
        return None
    for display, mapped in CANONICAL_KEYS.items():
        if mapped == key:
            return display
    return value


def _blob(filename: str, ocr_text: str) -> str:
    return f"{filename or ''}\n{ocr_text or ''}"


def classify_from_filename(filename: str) -> Optional[str]:
    lowered = (filename or "").lower()
    for patterns, doc_type in _FILENAME_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return doc_type
    return None


def classify_from_content(ocr_text: str, filename: str = "") -> Optional[str]:
    blob = _blob(filename, ocr_text)
    blob_lower = blob.lower()
    mutation_hits = sum(1 for token in _MUTATION_INDICATORS if token in blob or token in blob_lower)
    sale_hits = sum(1 for token in _STRONG_SALE_DEED if token in blob or token in blob_lower)

    for patterns, doc_type in _CONTENT_PATTERNS:
        if any(token in blob or token in blob_lower for token in patterns):
            if doc_type == "Sale Deed" and mutation_hits and sale_hits == 0:
                continue
            if doc_type == "Mutation" and sale_hits and mutation_hits == 0:
                continue
            return doc_type
    return None


def classify_document_type(
    filename: str = "",
    ocr_text: str = "",
    existing_doc_type: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """Return (canonical display name, source)."""
    existing_display = canonical_display(existing_doc_type) if existing_doc_type else None
    filename_hit = classify_from_filename(filename)
    content_hit = classify_from_content(ocr_text, filename) if ocr_text else None
    blob = _blob(filename, ocr_text)
    blob_lower = blob.lower()
    mutation_hits = sum(1 for token in _MUTATION_INDICATORS if token in blob or token in blob_lower)
    sale_hits = sum(1 for token in _STRONG_SALE_DEED if token in blob or token in blob_lower)

    protected = {
        "Fard", "CNIC", "Search Report", "Valuation", "Facility Approval",
        "Possession Letter", "Property Tax/PT-10", "Board Resolution",
        "Building Plan", "Dues Clearance", "Charge Release",
        "Identity Confirmation", "Society/Authority NOC",
    }
    if filename_hit in protected:
        return filename_hit, "filename"
    if filename_hit == "Mutation":
        return "Mutation", "filename"
    if filename_hit == "Sale Deed":
        return "Sale Deed", "filename"

    if mutation_hits and mutation_hits >= sale_hits and sale_hits <= 1:
        return "Mutation", "content" if ocr_text else "filename"
    if content_hit:
        return content_hit, "content"
    if filename_hit:
        return filename_hit, "filename"
    if existing_display:
        return existing_display, "existing"
    return None, "none"


def persist_document_classification(
    db: Session,
    document,
    ocr_text: str = "",
    *,
    overwrite_manual: bool = False,
) -> Optional[str]:
    """Write canonical doc_type onto the document unless a reviewer locked it."""
    if getattr(document, "doc_type_source", None) == "manual" and not overwrite_manual:
        return document.doc_type

    classified, source = classify_document_type(
        getattr(document, "original_filename", "") or "",
        ocr_text or "",
        getattr(document, "doc_type", None),
    )
    if not classified:
        return document.doc_type

    document.doc_type = classified
    document.doc_type_source = "auto"
    document.doc_type_updated_at = datetime.utcnow()
    document.predicted_doc_type = classified
    if source == "filename" and not (ocr_text or "").strip():
        document.classification_confidence = 0.7
    else:
        document.classification_confidence = 0.9 if source == "content" else 0.75
    document.classification_status = "auto"
    db.add(document)
    return classified


def effective_type_keys(values: Iterable[str]) -> set[str]:
    keys = set()
    for value in values:
        key = canonical_key(value)
        if key:
            keys.add(key)
    return keys
