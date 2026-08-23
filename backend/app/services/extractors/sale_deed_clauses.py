"""Parse Pakistani sale-deed recitals (running clauses, not labelled form fields)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.services.extractors.validators import is_extraction_garbage, is_plausible_party_name


HONORIFICS = ("جناب", "محترمہ", "محترم")

SELLER_MARKERS = ("فروخت کنندہ", "فروخت‌کنندہ", "بائع")
BUYER_ORG_MARKERS = ("خریدار کمپنی", "اور خریدار", "خریدار")
WITNESS_MARKERS = ("گواہ نمبر", "گواہان", "گواہ")

SELLER_STOP = r"(?:ولد|ولدہ|ساکن|بالغ|شناختی|ایک جانب|جسے آئندہ)"
BUYER_STOP = r"(?:کمپنی\s+)?رجسٹریشن|بذریعہ|دوسری جانب"


@dataclass(frozen=True)
class ClauseHit:
    value: str
    page_number: int
    char_start: int
    char_end: int
    method: str = "clause_urdu"


def _strip_honorific(name: str) -> str:
    s = name.strip()
    for hon in HONORIFICS:
        if s.startswith(hon):
            s = s[len(hon) :].strip()
    return s


def _page_hit(page_number: int, text: str, start: int, end: int, value: str) -> ClauseHit:
    return ClauseHit(
        value=value,
        page_number=page_number,
        char_start=start,
        char_end=end,
        method="clause_urdu",
    )


def _extract_seller(text: str, page_number: int) -> Optional[ClauseHit]:
    for marker in SELLER_MARKERS:
        for match in re.finditer(re.escape(marker), text):
            after = text[match.end() :]
            name_match = re.match(
                rf"\s*(?:{'|'.join(HONORIFICS)})?\s*(.+?)\s*{SELLER_STOP}",
                after,
            )
            if not name_match:
                continue
            raw = _strip_honorific(name_match.group(1))
            raw = raw.strip(" '\"“”‘’,،")
            if not raw or is_extraction_garbage(raw, role="seller")[0]:
                continue
            ok, _ = is_plausible_party_name(raw, role="seller")
            if not ok:
                continue
            abs_start = match.end() + name_match.start(1)
            abs_end = match.end() + name_match.end(1)
            # Honorific may sit inside group 1; locate the cleaned value.
            located = text.find(raw, match.end())
            if located >= 0:
                abs_start, abs_end = located, located + len(raw)
            return _page_hit(page_number, text, abs_start, abs_end, raw)
    return None


def _extract_buyer(text: str, page_number: int) -> Optional[ClauseHit]:
    patterns = [
        rf"(?:خریدار\s+کمپنی|اور\s+خریدار(?:\s+کمپنی)?)\s+(.+?)\s+(?:{BUYER_STOP})",
        rf"خریدار\s+(.+?)\s+(?:{BUYER_STOP})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(1).strip()
        raw = re.sub(r"^(?:کمپنی\s+)", "", raw).strip()
        raw = raw.strip(" '\"“”‘’,،")
        if not raw or is_extraction_garbage(raw, role="buyer")[0]:
            continue
        ok, _ = is_plausible_party_name(raw, role="buyer")
        if not ok:
            continue
        return _page_hit(page_number, text, match.start(1), match.end(1), raw)
    signatory = re.search(r"مجاز\s+ڈائریکٹر\s+(?:جناب|محترمہ)?\s*([^\n،,]{3,40})", text)
    if signatory:
        # Signatory is extra evidence only; buyer org is the primary value.
        _ = signatory.group(1)
    return None


def _extract_witness(text: str, page_number: int) -> Optional[ClauseHit]:
    for marker in WITNESS_MARKERS:
        for match in re.finditer(re.escape(marker), text):
            after = text[match.end() :]
            name_match = re.match(r"[\s:،]*([^\n]{3,80})", after)
            if not name_match:
                continue
            raw = name_match.group(1).strip()
            raw = re.split(r"(?:گواہ|خریدار|فروخت|شناختی)", raw)[0].strip(" '\"“”‘’,،")
            if not raw or is_extraction_garbage(raw, role="witness")[0]:
                continue
            ok, _ = is_plausible_party_name(raw, role="witness")
            if not ok:
                continue
            located = text.find(raw, match.end())
            if located < 0:
                continue
            return _page_hit(page_number, text, located, located + len(raw), raw)
    return None


def extract_sale_deed_clauses(pages: List) -> Dict[str, ClauseHit]:
    """
    Extract seller / buyer / witness from sale-deed recital prose.

    `pages` is a list of objects with `.page_number` and `.text` (PageOCR).
    Empty roles are omitted — a missing witness is better than a watermark.
    """
    hits: Dict[str, ClauseHit] = {}
    for page in pages:
        text = page.text or ""
        page_number = getattr(page, "page_number", 1)
        if "seller" not in hits:
            seller = _extract_seller(text, page_number)
            if seller:
                hits["seller"] = seller
        if "buyer" not in hits:
            buyer = _extract_buyer(text, page_number)
            if buyer:
                hits["buyer"] = buyer
        if "witness" not in hits:
            witness = _extract_witness(text, page_number)
            if witness:
                hits["witness"] = witness
        if "seller" in hits and "buyer" in hits and "witness" in hits:
            break
    return hits
