"""Per-document legal facts used by gold rules.

Facts are generic (kanal/marla, dates, dues language, charge refs).
They are not hard-coded to CDS-GOLD-001 values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

from app.services.canonical_docs import canonical_display
from app.services.extractors.validators import is_plausible_party_name


URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Land-record spelling is کنال (noon). OCR of that glyph is often Latin "JUS".
_KANAL_UNIT = r"(?:کنال|کانال|kanal|jus)"
_MARLA_UNIT = r"(?:مرلہ|marla)s?"

# Prefer the stated total. Khasra fragments like "1 کنال 10 مرلہ" are not the property area.
TOTAL_AREA_RE = re.compile(
    r"کل\s*رقبہ(?:[^\n\d]{0,48})?"
    r"(\d+(?:\.\d+)?)\s*" + _KANAL_UNIT + r"(?:s)?"
    r"(?:[^\d]{0,16}(\d+(?:\.\d+)?)\s*" + _MARLA_UNIT + r")?",
    re.IGNORECASE,
)
LABELED_AREA_RE = re.compile(
    r"(?:رقبہ|area)\s*[:\-]?\s*"
    r"(\d+(?:\.\d+)?)\s*(?:کنال|کانال|kanal)s?"
    r"(?:[^\d]{0,24}(\d+(?:\.\d+)?)\s*" + _MARLA_UNIT + r")?",
    re.IGNORECASE,
)
FALLBACK_KANAL_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:کنال|کانال|kanal)s?"
    r"(?:[^\d]{0,24}(\d+(?:\.\d+)?)\s*" + _MARLA_UNIT + r")?",
    re.IGNORECASE,
)
MARLA_ONLY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*" + _MARLA_UNIT,
    re.IGNORECASE,
)

DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(
        r"\b(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,2}\s+(?:جنوری|فروری|مارچ|اپریل|مئی|جون|جولائی|اگست|"
        r"ستمبر|اکتوبر|نومبر|دسمبر)\s+\d{4})"
    ),
]

ISSUE_DATE_RE = re.compile(
    r"(?:تاریخ\s*)?اجرا\s*[:\-]?\s*(\d{1,2}\s+\S+\s+\d{4})"
)

URDU_MONTHS = {
    "جنوری": "January",
    "فروری": "February",
    "مارچ": "March",
    "اپریل": "April",
    "مئی": "May",
    "جون": "June",
    "جولائی": "July",
    "اگست": "August",
    "ستمبر": "September",
    "اکتوبر": "October",
    "نومبر": "November",
    "دسمبر": "December",
}

OWNER_PATTERNS = [
    re.compile(r"مالک\s*[:\-|]?\s*([^\n|]{3,80})"),
    re.compile(r"owner\s*[:\-]\s*([^\n|]{3,80})", re.IGNORECASE),
    re.compile(
        r"منتقل\s*کنندہ\s*[:\-]?\s*([A-Za-z\u0600-\u06FF][^\n|]{2,60})"
    ),
]

_OWNER_CUT_TOKENS = (
    " کے لیے",
    " ملاحظہ",
    " حصص",
    " منتقل",
    " رجسٹریشن",
    " ولد",
    "،",
    ",",
)
_OWNER_REJECT_FRAGMENTS = (
    "ملاحظہ",
    "کے لیے",
    "حصص داران",
    "ان /",
    "مندرجہ",
)

DUES_PATTERNS = [
    re.compile(r"development\s+charges?", re.IGNORECASE),
    re.compile(r"ترقیاتی\s+خرچ"),
    re.compile(r"outstanding.{0,40}dues", re.IGNORECASE),
    re.compile(r"بقایا"),
]

CHARGE_PATTERNS = [
    re.compile(r"(CHG[- ]?[A-Z0-9][-A-Z0-9/]*)", re.IGNORECASE),
    re.compile(r"prior\s+charge", re.IGNORECASE),
    re.compile(r"existing\s+mortgage", re.IGNORECASE),
    re.compile(r"سابقہ\s+رہن"),
    re.compile(r"بوجھ"),
]

TAX_HISTORY_PATTERNS = [
    re.compile(r"previous\s+years?", re.IGNORECASE),
    re.compile(r"historic(?:al)?\s+tax", re.IGNORECASE),
    re.compile(r"back\s+(?:years?|duty|tax)", re.IGNORECASE),
    re.compile(r"گزشتہ\s+سال"),
    re.compile(r"سابقہ\s+سال"),
    re.compile(r"تاریخی"),
    re.compile(r"paper\s+receipt", re.IGNORECASE),
    re.compile(r"waiver\s+scenario", re.IGNORECASE),
    re.compile(r"20-2019"),
]


@dataclass(frozen=True)
class DocumentFact:
    key: str
    value: str
    page_number: int
    snippet: str
    char_start: int = 0
    char_end: int = 0
    doc_type: Optional[str] = None
    document_id: Optional[str] = None


def _normalize_digits(text: str) -> str:
    return (text or "").translate(URDU_DIGITS)


def _normalize_months(text: str) -> str:
    blob = _normalize_digits(text or "")
    # OCR of اگست is گست. Do not rewrite the alef already present in اگست.
    blob = re.sub(r"(?<!ا)گست", "اگست", blob)
    return blob


def _area_value(kanal: str, marla: Optional[str]) -> str:
    if marla:
        return f"{kanal} Kanal {marla} Marla"
    return f"{kanal} Kanal"


def area_to_marlas(value: str) -> Optional[float]:
    text = _normalize_digits(value or "")
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*" + _KANAL_UNIT + r"(?:s)?"
        r"(?:[^\d]{0,24}(\d+(?:\.\d+)?)\s*" + _MARLA_UNIT + r")?",
        text,
        re.IGNORECASE,
    )
    if match:
        kanal = float(match.group(1))
        marla = float(match.group(2) or 0)
        return kanal * 20.0 + marla
    marla_only = MARLA_ONLY_RE.search(text)
    if marla_only:
        return float(marla_only.group(1))
    return None


_EN_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def parse_date_value(value: str) -> Optional[date]:
    raw = re.sub(r"\s+", " ", _normalize_months((value or "").strip())).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass

    named = raw
    for month_ur, month_en in URDU_MONTHS.items():
        named = named.replace(month_ur, month_en)
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", named)
    if not match:
        match = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", named)
        if match:
            month = _EN_MONTHS.get(match.group(1).lower())
            if month:
                try:
                    return date(int(match.group(3)), month, int(match.group(2)))
                except ValueError:
                    return None
        return None
    month = _EN_MONTHS.get(match.group(2).lower())
    if not month:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None


def _snippet(text: str, start: int, end: int, width: int = 48) -> str:
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def _plausible_owner(raw: str) -> Optional[str]:
    owner = re.sub(r"\s+", " ", raw or "").strip(" :-|/")
    for token in _OWNER_CUT_TOKENS:
        if token in owner:
            owner = owner.split(token, 1)[0].strip(" :-|/")
    if len(owner) < 4:
        return None
    if any(fragment in owner for fragment in _OWNER_REJECT_FRAGMENTS):
        return None
    ok, _reason = is_plausible_party_name(owner, role="buyer")
    if not ok:
        return None
    return owner


def _area_from_match(match: re.Match[str], *, require_kanal: bool = True) -> Optional[Tuple[str, int, int]]:
    kanal = match.group(1)
    marla = match.group(2) if match.lastindex and match.lastindex >= 2 else None
    if require_kanal and not kanal:
        return None
    return _area_value(kanal, marla), match.start(), match.end()


def _extract_area(blob: str) -> Optional[Tuple[str, int, int]]:
    total = TOTAL_AREA_RE.search(blob)
    if total:
        return _area_from_match(total)

    labeled = LABELED_AREA_RE.search(blob)
    if labeled:
        return _area_from_match(labeled)

    fallback = FALLBACK_KANAL_RE.search(blob)
    if fallback:
        kanal = float(fallback.group(1))
        # Single-kanal khasra pieces are not the property total.
        if kanal >= 2:
            return _area_from_match(fallback)
    return None


def _extract_issue_date(blob: str) -> Optional[Tuple[str, int, int]]:
    labeled = ISSUE_DATE_RE.search(blob)
    if labeled:
        parsed = parse_date_value(labeled.group(1))
        value = parsed.isoformat() if parsed else labeled.group(1)
        return value, labeled.start(1), labeled.end(1)

    for pattern in DATE_PATTERNS:
        match = pattern.search(blob)
        if not match:
            continue
        parsed = parse_date_value(match.group(1))
        value = parsed.isoformat() if parsed else match.group(1)
        return value, match.start(), match.end()
    return None


def extract_document_facts(
    *,
    text: str,
    page_number: int,
    filename: str = "",
    doc_type: Optional[str] = None,
    document_id: Optional[str] = None,
) -> List[DocumentFact]:
    blob = _normalize_months(text or "")
    resolved_type = canonical_display(doc_type) or canonical_display(filename)
    facts: List[DocumentFact] = []

    area = _extract_area(blob)
    if area:
        value, start, end = area
        facts.append(
            DocumentFact(
                key="fact.area",
                value=value,
                page_number=page_number,
                snippet=_snippet(blob, start, end),
                char_start=start,
                char_end=end,
                doc_type=resolved_type,
                document_id=document_id,
            )
        )

    issue = _extract_issue_date(blob)
    if issue:
        value, start, end = issue
        facts.append(
            DocumentFact(
                key="fact.issue_date",
                value=value,
                page_number=page_number,
                snippet=_snippet(blob, start, end),
                char_start=start,
                char_end=end,
                doc_type=resolved_type,
                document_id=document_id,
            )
        )

    for pattern in OWNER_PATTERNS:
        match = pattern.search(blob)
        if not match:
            continue
        owner = _plausible_owner(match.group(1))
        if not owner:
            continue
        facts.append(
            DocumentFact(
                key="fact.owner_name",
                value=owner,
                page_number=page_number,
                snippet=_snippet(blob, match.start(), match.end()),
                char_start=match.start(),
                char_end=match.end(),
                doc_type=resolved_type,
                document_id=document_id,
            )
        )
        break

    for pattern in DUES_PATTERNS:
        match = pattern.search(blob)
        if not match:
            continue
        facts.append(
            DocumentFact(
                key="fact.dues",
                value=match.group(0),
                page_number=page_number,
                snippet=_snippet(blob, match.start(), match.end()),
                char_start=match.start(),
                char_end=match.end(),
                doc_type=resolved_type,
                document_id=document_id,
            )
        )
        break

    for pattern in CHARGE_PATTERNS:
        match = pattern.search(blob)
        if not match:
            continue
        facts.append(
            DocumentFact(
                key="fact.charge_ref",
                value=match.group(0),
                page_number=page_number,
                snippet=_snippet(blob, match.start(), match.end()),
                char_start=match.start(),
                char_end=match.end(),
                doc_type=resolved_type,
                document_id=document_id,
            )
        )
        break

    for pattern in TAX_HISTORY_PATTERNS:
        match = pattern.search(blob)
        if not match:
            continue
        facts.append(
            DocumentFact(
                key="fact.tax_history",
                value=match.group(0),
                page_number=page_number,
                snippet=_snippet(blob, match.start(), match.end()),
                char_start=match.start(),
                char_end=match.end(),
                doc_type=resolved_type,
                document_id=document_id,
            )
        )
        break

    return facts
