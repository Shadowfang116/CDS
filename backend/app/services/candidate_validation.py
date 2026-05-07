from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    confidence_factor: float
    reason: Optional[str]


FIELD_MIN_LENGTH = {
    "owner_name": 4,
    "buyer_name": 4,
    "seller_name": 4,
    "party_name": 4,
    "transferor": 4,
    "transferee": 4,
    "cnic": 15,
    "cnic_number": 15,
    "amount": 1,
    "consideration": 1,
    "price": 1,
    "plot_number": 2,
    "khasra_number": 2,
    "date": 6,
    "registration_date": 6,
    "lien_status": 3,
    "noc_status": 3,
}

_REQUIRED_HIGH_RISK_FIELDS = {
    "owner_name",
    "buyer_name",
    "seller_name",
    "party_name",
    "transferor",
    "transferee",
    "cnic",
    "cnic_number",
    "amount",
    "consideration",
    "price",
    "khasra_number",
    "plot_number",
}

try:
    from app.services.ocr_pipeline import HIGH_RISK_FIELDS as OCR_PIPELINE_HIGH_RISK_FIELDS
except Exception:
    HIGH_RISK_FIELDS = set(_REQUIRED_HIGH_RISK_FIELDS)
else:
    HIGH_RISK_FIELDS = set(OCR_PIPELINE_HIGH_RISK_FIELDS) | _REQUIRED_HIGH_RISK_FIELDS


_FIELD_ALIASES = {
    "party.seller.names": "seller_name",
    "party.buyer.names": "buyer_name",
    "party.witness.names": "party_name",
    "party.name.raw": "party_name",
    "party.cnic": "cnic",
    "party.cnic_number": "cnic_number",
    "consideration.amount": "amount",
    "property.plot_number": "plot_number",
    "property.khasra_number": "khasra_number",
    "property.khasra_numbers": "khasra_number",
    "document.execution_date": "execution_date",
    "registry.registry_date": "registration_date",
    "registry.registration_date": "registration_date",
}

_NOISE_PATTERN = re.compile(r"[A-Za-z0-9\u0600-\u06FF]")
_CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")
_DATE_PATTERN = re.compile(r"\b\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\b")
_NAME_FIELDS = {
    "owner_name",
    "buyer_name",
    "seller_name",
    "party_name",
    "transferor",
    "transferee",
}
_AMOUNT_FIELDS = {"amount", "consideration", "price"}
_DATE_FIELDS = {"date", "registration_date", "execution_date"}
_CNIC_FIELDS = {"cnic", "cnic_number"}


def _canonicalize_field_name(field_name: str) -> str:
    normalized = (field_name or "").strip()
    if normalized in _FIELD_ALIASES:
        return _FIELD_ALIASES[normalized]

    leaf = normalized.split(".")[-1]
    return _FIELD_ALIASES.get(leaf, leaf)


def validate_candidate(field_name: str, value: str, page_quality_level: str) -> ValidationResult:
    normalized_field_name = _canonicalize_field_name(field_name)
    stripped_value = (value or "").strip()

    if not _NOISE_PATTERN.search(stripped_value):
        return ValidationResult(False, 0.0, "junk_token_pattern")

    min_length = FIELD_MIN_LENGTH.get(normalized_field_name)
    if min_length is not None and len(stripped_value) < min_length:
        reason_field = normalized_field_name[:20]
        return ValidationResult(False, 0.1, f"short_{reason_field}_candidate")

    if normalized_field_name in _CNIC_FIELDS:
        digits_only = re.sub(r"\D", "", stripped_value)
        normalized_cnic = digits_only
        if len(digits_only) == 13:
            normalized_cnic = f"{digits_only[:5]}-{digits_only[5:12]}-{digits_only[12]}"
        if not _CNIC_PATTERN.match(normalized_cnic):
            return ValidationResult(False, 0.15, "invalid_cnic_format")
        return ValidationResult(True, 1.0, None)

    if normalized_field_name in _AMOUNT_FIELDS:
        compact_value = re.sub(r"[\s,.]", "", stripped_value)
        if not compact_value.isdigit():
            return ValidationResult(False, 0.2, "malformed_amount")

    if normalized_field_name in _DATE_FIELDS:
        if not _DATE_PATTERN.search(stripped_value):
            return ValidationResult(False, 0.2, "invalid_date_format")
        return ValidationResult(True, 0.9, None)

    if normalized_field_name in _NAME_FIELDS:
        non_space_chars = [char for char in stripped_value if not char.isspace()]
        digit_count = sum(1 for char in non_space_chars if char.isdigit())
        digit_ratio = (digit_count / len(non_space_chars)) if non_space_chars else 0.0
        if digit_ratio > 0.5:
            return ValidationResult(False, 0.15, "name_high_digit_ratio")

        words = [word for word in stripped_value.split() if word]
        if len(words) == 1 and len(words[0]) < 6:
            return ValidationResult(True, 0.4, "short_name_candidate")

    if normalized_field_name in HIGH_RISK_FIELDS and page_quality_level in {"poor", "unusable"}:
        return ValidationResult(True, 0.3, "low_quality_page")

    return ValidationResult(True, 1.0, None)
