from __future__ import annotations

from collections import defaultdict
from typing import Optional, Tuple

from app.models.document import DocumentType


# Keyword dictionaries are intentionally simple; weights are handled in code.
KEYWORDS = {
    DocumentType.SALE_DEED.value: [
        "sale deed",
        "bay nama",
        "baynama",
        "bai nama",
        "bainama",
        "conveyance deed",
    ],
    DocumentType.REGISTRY_DEED.value: [
        "registry",
        "registered deed",
        "registry deed",
    ],
    DocumentType.FARD.value: [
        "fard",
        "fard e malkiat",
        "fard e malkiyat",
        "malkiyat",
    ],
    DocumentType.JAMABANDI.value: [
        "jamabandi",
    ],
    DocumentType.SOCIETY_NOC.value: [
        "noc",
        "no objection certificate",
        "society approval",
    ],
    # Tightened below: only phrases with "letter"; scoring uses OCR text for this type
    DocumentType.ALLOTMENT_LETTER.value: [
        "allotment letter",
        "allocation letter",
        "letter of allotment",
    ],
    DocumentType.POWER_OF_ATTORNEY.value: [
        "power of attorney",
        "poa",
        "wakalatnama",
    ],
    DocumentType.SEARCH_REPORT.value: [
        "search report",
        # strong phrases handled separately for a big boost
    ],
    DocumentType.MAP_OR_SITE_PLAN.value: [
        "site plan",
        "site map",
        "map",
    ],
}

# Strong boosters (searched in filename and OCR text)
SEARCH_REPORT_STRONG = [
    "title search",
    "property search",
    "encumbrance search",
    "search report",
    "title verification",
    "legal search report",
]

MAP_PLAN_LOCAL = [
    "aks shajra",
    "naqsha nazri",
    "shajra",
    "site map",
    "layout plan",
    "master plan",
    "site plan",
    "plot map",
]

SALE_STRONG = [
    "sale deed",
    "bainama",
    "bay nama",
    "baynama",
    "bai nama",
    "conveyance deed",
]
SALE_NEGATIVE_GUARDS = [
    "completion certificate",
    "certificate of completion",
    "chain mutation",
    "mutation",
]

FARD_STRONG = [
    "fard",
    "fard e malkiat",
    "fard e malkiyat",
    "malkiyat",
]

ALLOTMENT_STRONG_TEXT = [
    "allotment letter",
    "allocation letter",
    "letter of allotment",
]


def _count_occurrences(haystack: str, needle: str) -> int:
    return haystack.count(needle)


def _any_in(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def classify_document(
    filename: str,
    ocr_text: Optional[str] = None,
) -> Tuple[str, float, dict]:
    """
    Heuristic classifier using filename + OCR text.
    Returns: (doc_type, confidence [0-1], details)
    """
    name = (filename or "").lower()
    text = (ocr_text or "").lower()

    scores = defaultdict(float)
    hits = defaultdict(int)
    details: dict = {"rules": []}

    # 1) Score baseline keywords
    for doc_type, phrases in KEYWORDS.items():
        for p in phrases:
            if not p:
                continue
            # Special handling: allotment_letter must be supported by OCR text only
            if doc_type == DocumentType.ALLOTMENT_LETTER.value:
                if p in text:
                    c = _count_occurrences(text, p)
                    scores[doc_type] += min(5, c) * 0.7  # slightly higher than default text weight
                    hits[doc_type] += c
                continue

            # filename hits (higher weight)
            if p in name:
                c = max(1, _count_occurrences(name, p))
                scores[doc_type] += 1.0 * c
                hits[doc_type] += c
            # OCR text hits (lower weight per occurrence; cap to avoid inflation)
            if p in text:
                c = _count_occurrences(text, p)
                if c:
                    scores[doc_type] += min(5, c) * 0.5
                    hits[doc_type] += c

    # 2) Strong boosters (search_report, map/site plan)
    sr_matches = 0
    for p in SEARCH_REPORT_STRONG:
        sr_matches += _count_occurrences(name, p)
        sr_matches += _count_occurrences(text, p)
    if sr_matches >= 1:
        # Big boost so it wins over others
        scores[DocumentType.SEARCH_REPORT.value] += 8.0 + min(2, sr_matches - 1) * 1.5
        hits[DocumentType.SEARCH_REPORT.value] += sr_matches
        details["rules"].append({"rule": "search_report_strong", "matches": sr_matches})

    # Map / site plan local signals
    mp_hits = 0
    for p in MAP_PLAN_LOCAL:
        h = _count_occurrences(name, p) + _count_occurrences(text, p)
        if h:
            scores[DocumentType.MAP_OR_SITE_PLAN.value] += 3.0 * h
            hits[DocumentType.MAP_OR_SITE_PLAN.value] += h
            mp_hits += h
    if mp_hits:
        details["rules"].append({"rule": "map_plan_local", "matches": mp_hits})

    # 3) Type-specific guards
    sale_strong = _any_in(name, SALE_STRONG) or _any_in(text, SALE_STRONG)
    sale_neg = _any_in(name, SALE_NEGATIVE_GUARDS) or _any_in(text, SALE_NEGATIVE_GUARDS)
    if not sale_strong or sale_neg:
        # Disallow weak/contradicted sale deed classification
        scores[DocumentType.SALE_DEED.value] = 0.0
        if sale_neg:
            details["rules"].append({"rule": "sale_neg_guard"})

    # Allotment must be backed by OCR text (already enforced above). If no OCR match, zero it.
    if not _any_in(text, ALLOTMENT_STRONG_TEXT):
        scores[DocumentType.ALLOTMENT_LETTER.value] = 0.0

    # Fard must include one of the strong terms
    fard_present = _any_in(name, FARD_STRONG) or _any_in(text, FARD_STRONG)
    if not fard_present:
        scores[DocumentType.FARD.value] = 0.0

    # 4) Choose best by score
    if scores:
        best_type = max(scores, key=lambda k: scores[k])
        sorted_scores = sorted(scores.values(), reverse=True)
        second = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        raw = scores[best_type]
    else:
        best_type = DocumentType.UNKNOWN.value
        second = 0.0
        raw = 0.0

    # 5) Fallbacks when still nothing matched
    if raw == 0.0:
        # No positive signal so far
        best_type = DocumentType.UNKNOWN.value
        # 'deed' + sale context (honor strong/negative rules)
        if ("deed" in name or "deed" in text):
            if (("sale" in name or "sale" in text) or ("conveyance" in name or "conveyance" in text)) and sale_strong and not sale_neg:
                best_type = DocumentType.SALE_DEED.value
                raw = 1.0
            else:
                best_type = DocumentType.REGISTRY_DEED.value
                raw = 0.8
        elif ("jamabandi" in name or "jamabandi" in text):
            best_type = DocumentType.JAMABANDI.value
            raw = 1.0
        elif fard_present:
            best_type = DocumentType.FARD.value
            raw = 0.9
        elif ("noc" in name or "no objection" in text or "society" in text):
            best_type = DocumentType.SOCIETY_NOC.value
            raw = 0.7
        elif ("power of attorney" in text) or ("poa" in name) or ("wakalat" in text):
            best_type = DocumentType.POWER_OF_ATTORNEY.value
            raw = 0.9

    # 6) Confidence calibration
    if raw <= 0:
        confidence = 0.0
    else:
        denom = raw + max(0.0, second)
        comp = (raw / denom) if denom > 0 else 1.0
        # map to [0.55, 0.98] and give a small boost for multiple hits
        boost = 0.02 * max(0, hits.get(best_type, 0) - 1)
        confidence = max(0.55, min(0.98, 0.55 + 0.4 * comp + boost))

    # Ensure high confidence for strong search report signals
    if best_type == DocumentType.SEARCH_REPORT.value and sr_matches >= 1:
        confidence = max(confidence, 0.90)

    details.update({
        "scores": dict(scores),
        "hits": dict(hits),
    })
    return best_type, confidence, details
