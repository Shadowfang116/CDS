"""Rule Engine v1 - Evaluates cases against YAML rulepack."""
from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.regimes import Regime, normalize_regime
from app.models.case import Case
from app.models.document import CaseDossierField, Document, DocumentPage
from app.models.ocr_extraction import OCRExtractionCandidate
from app.models.rules import ConditionPrecedent, Exception_, ExceptionEvidenceRef, RuleRun
from app.models.verification import Verification
from app.services.canonical_docs import (
    canonical_key,
    classify_from_filename,
)
from app.services.extractors.document_facts import DocumentFact, area_to_marlas, parse_date_value
from app.services.rule_schema import load_rulepack_from_path

logger = logging.getLogger(__name__)

def _default_rulepack_path() -> Path:
    here = Path(__file__).resolve()
    names = (
        Path("docs") / "rulepacks" / "punjab_mortgage_v1.yaml",
        Path("docs") / "05_rulepack_v1.yaml",
    )
    for parent in here.parents:
        for relative in names:
            candidate = parent / relative
            if candidate.is_file():
                return candidate
    return here.parents[2] / "docs" / "rulepacks" / "punjab_mortgage_v1.yaml"


DEFAULT_RULEPACK_PATH = _default_rulepack_path()
RULEPACK_PATH = os.environ.get("RULEPACK_PATH", str(DEFAULT_RULEPACK_PATH))
OPEN_STATUSES = {"Open", "Pending"}
PRESERVED_EXCEPTION_STATUSES = {"Waived", "Resolved"}


class RuleEnginePreconditionError(ValueError):
    """Raised when the case cannot be evaluated safely."""


@dataclass
class EvidenceRef:
    """Reference to evidence in a document."""

    document_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    note: Optional[str] = None


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""

    rule_id: str
    module: str
    severity: str
    triggered: bool
    title: str = ""
    description: str = ""
    cp_text: str = ""
    evidence_required: str = ""
    resolution_conditions: str = ""
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    is_hard_stop: bool = False


@dataclass
class CaseContext:
    """Normalized case data for rule evaluation."""

    org_id: uuid.UUID
    case_id: uuid.UUID
    dossier: Dict[str, List[str]]
    doc_types: List[str]
    doc_filenames: List[str]
    documents: List[Document]
    pages: List[Tuple[uuid.UUID, int, str]]
    verifications: Dict[str, str] = field(default_factory=dict)
    ocr_complete: bool = True
    borrower_type: Optional[str] = None
    transaction_type: Optional[str] = None
    document_facts: List[DocumentFact] = field(default_factory=list)


def load_rulepack() -> Dict[str, Any]:
    """Load and validate the rulepack YAML."""
    try:
        result = load_rulepack_from_path(RULEPACK_PATH)
    except FileNotFoundError:
        logger.error("Rulepack not found at %s", RULEPACK_PATH)
        return {"rules": [], "errors": [f"Rulepack not found at {RULEPACK_PATH}"]}
    except Exception as exc:
        logger.error("Failed to load rulepack: %s", exc)
        return {"rules": [], "errors": [str(exc)]}

    if not result.ok:
        for error in result.errors:
            logger.error("Rulepack validation error: %s", error)
        return {"rules": [], "errors": result.errors}

    return {"rules": result.rules}


def build_case_context(db: Session, org_id: uuid.UUID, case_id: uuid.UUID) -> CaseContext:
    """Build normalized case context from database."""
    dossier_rows = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
    ).all()

    dossier: Dict[str, List[str]] = {}
    for row in dossier_rows:
        if row.field_value:
            dossier.setdefault(row.field_key, []).append(row.field_value)

    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).all()

    doc_types: List[str] = []
    doc_filenames: List[str] = []
    pages: List[Tuple[uuid.UUID, int, str]] = []
    ocr_complete = True

    for doc in documents:
        if doc.doc_type:
            doc_types.append(doc.doc_type)
        doc_filenames.append(doc.original_filename)

        all_pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id,
            DocumentPage.org_id == org_id,
        ).all()
        done_pages = [page for page in all_pages if page.ocr_status == "Done"]

        if doc.page_count and len(done_pages) < doc.page_count:
            ocr_complete = False
        if all_pages and any(page.ocr_status != "Done" for page in all_pages):
            ocr_complete = False
        if doc.page_count and not all_pages:
            ocr_complete = False

        for page in done_pages:
            page_text = page.corrected_text or page.ocr_text
            if page_text:
                pages.append((doc.id, page.page_number, page_text))

    verifications_data = db.query(Verification).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
    ).all()
    verifications = {item.verification_type: item.status for item in verifications_data}

    dossier_borrower = (dossier.get("case.borrower_type") or [None])[0]
    dossier_txn = (dossier.get("case.transaction_type") or [None])[0]

    fact_rows = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.case_id == case_id,
        OCRExtractionCandidate.org_id == org_id,
        OCRExtractionCandidate.status.in_(["Pending", "Confirmed"]),
        OCRExtractionCandidate.field_key.like("fact.%"),
    ).all()
    party_rows = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.case_id == case_id,
        OCRExtractionCandidate.org_id == org_id,
        OCRExtractionCandidate.status.in_(["Pending", "Confirmed"]),
        OCRExtractionCandidate.field_key.in_(["party.buyer.names", "party.seller.names", "fact.owner_name"]),
    ).all()
    doc_type_by_id = {doc.id: doc.doc_type for doc in documents}
    document_facts: List[DocumentFact] = []
    for row in list(fact_rows) + list(party_rows):
        document_facts.append(
            DocumentFact(
                key=row.field_key,
                value=row.proposed_value or "",
                page_number=row.page_number or 1,
                snippet=row.snippet or "",
                doc_type=doc_type_by_id.get(row.document_id),
                document_id=str(row.document_id) if row.document_id else None,
            )
        )
    for row in dossier_rows:
        if row.field_key and row.field_key.startswith("fact.") and row.field_value:
            document_facts.append(
                DocumentFact(
                    key=row.field_key,
                    value=row.field_value,
                    page_number=row.source_page_number or 1,
                    snippet="",
                    doc_type=doc_type_by_id.get(row.source_document_id) if row.source_document_id else None,
                    document_id=str(row.source_document_id) if row.source_document_id else None,
                )
            )

    return CaseContext(
        org_id=org_id,
        case_id=case_id,
        dossier=dossier,
        doc_types=doc_types,
        doc_filenames=doc_filenames,
        documents=documents,
        pages=pages,
        verifications=verifications,
        ocr_complete=ocr_complete,
        borrower_type=str(dossier_borrower).strip().lower() if dossier_borrower else None,
        transaction_type=str(dossier_txn).strip().lower() if dossier_txn else None,
        document_facts=document_facts,
    )


def normalize_cnic(cnic: str) -> str:
    """Normalize CNIC by removing formatting."""
    return re.sub(r"[^0-9]", "", cnic)


def infer_doc_type_from_filename(filename: str) -> Optional[str]:
    """Infer canonical document type from filename (hint / corpus fallback)."""
    return classify_from_filename(filename)


def _normalize_doc_type(value: str) -> str:
    return canonical_key(value) or re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _canonical_doc_type(value: str) -> str:
    return canonical_key(value) or _normalize_doc_type(value)


def get_effective_doc_types(ctx: CaseContext) -> List[str]:
    """Get all doc types including inferred ones from filenames."""
    types = list(ctx.doc_types)
    for doc in ctx.documents:
        if not doc.doc_type:
            inferred = infer_doc_type_from_filename(doc.original_filename)
            if inferred and inferred not in types:
                types.append(inferred)
    return types


def _has_required_doc_type(required_types: Iterable[str], ctx: CaseContext) -> bool:
    effective_types = {_canonical_doc_type(doc_type) for doc_type in get_effective_doc_types(ctx)}
    return any(_canonical_doc_type(required_type) in effective_types for required_type in required_types)


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword.strip().lower()).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def _keyword_match_is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - 20):start].lower()
    return bool(re.search(r"(?:\bno|\bnot|\bwithout|\bfree\s+from)\s+$", window))


def _find_keywords_in_text(text: str, keywords: Iterable[str]) -> List[str]:
    matches: List[str] = []
    text_lower = text.lower()
    for keyword in keywords:
        pattern = _keyword_pattern(keyword)
        for match in pattern.finditer(text_lower):
            if _keyword_match_is_negated(text_lower, match.start()):
                continue
            matches.append(keyword)
            break
    return matches


def _text_contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    return bool(_find_keywords_in_text(text, keywords))


def _base_rule_result(
    rule: Dict[str, Any],
    *,
    triggered: bool,
    description: Optional[str] = None,
    evidence_refs: Optional[List[EvidenceRef]] = None,
    title: Optional[str] = None,
) -> RuleResult:
    outputs = rule.get("outputs", {})
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=title if title is not None else outputs.get("title", ""),
        description=outputs.get("exception", "") if description is None else description,
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
        evidence_refs=evidence_refs or [],
        is_hard_stop=bool(rule.get("is_hard_stop", False)),
    )


def evaluate_missing_evidence(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Check if required document types are missing."""
    required_types = rule.get("logic", {}).get("required_doc_types", [])
    triggered = not _has_required_doc_type(required_types, ctx)
    return _base_rule_result(rule, triggered=triggered)


def _normalize_comparable_value(field_name: str, value: str) -> str:
    raw = str(value).strip()
    lowered = field_name.lower()
    if "cnic" in lowered:
        return normalize_cnic(raw)
    if any(token in lowered for token in ("number", "khasra", "khewat", "registry")):
        return re.sub(r"[^a-z0-9]", "", raw.lower())
    return re.sub(r"\s+", " ", raw.lower())


def _collect_values_by_field_pattern(ctx: CaseContext, field_pattern: str) -> List[str]:
    values: List[str] = []
    for key, entries in ctx.dossier.items():
        if field_pattern in key:
            values.extend(entries)
    return values


def _collect_values(ctx: CaseContext, field_name: str) -> List[str]:
    return list(ctx.dossier.get(field_name, []))


def _parse_numeric(value: str) -> Optional[float]:
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(value))
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def _parse_date_value(value: str) -> Optional[date]:
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def evaluate_mismatch(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Check for mismatched values in dossier fields."""
    logic = rule.get("logic", {})
    evidence_refs: List[EvidenceRef] = []
    triggered = False

    field_pattern = str(logic.get("field_pattern", "")).strip()
    if field_pattern:
        values = _collect_values_by_field_pattern(ctx, field_pattern)
        normalized = {_normalize_comparable_value(field_pattern, value) for value in values if str(value).strip()}
        if len(normalized) > 1:
            triggered = True
            evidence_refs.append(EvidenceRef(note=f"{field_pattern} values: {sorted(normalized)}"))

    compare_fields = [str(item).strip() for item in logic.get("compare_fields", []) if str(item).strip()]
    threshold_percent = logic.get("threshold_percent")
    if compare_fields and threshold_percent is not None:
        left_values = _collect_values(ctx, compare_fields[0])
        right_values = _collect_values(ctx, compare_fields[1])
        left = _parse_numeric(left_values[0]) if left_values else None
        right = _parse_numeric(right_values[0]) if right_values else None
        if left is not None and right is not None:
            baseline = max(abs(left), abs(right), 1.0)
            delta_percent = abs(left - right) / baseline * 100
            if delta_percent > float(threshold_percent):
                triggered = True
                evidence_refs.append(
                    EvidenceRef(
                        note=(
                            f"{compare_fields[0]}={left_values[0]} vs "
                            f"{compare_fields[1]}={right_values[0]} ({delta_percent:.2f}% delta)"
                        )
                    )
                )
    elif compare_fields:
        for field_name in compare_fields:
            values = _collect_values(ctx, field_name)
            normalized = {_normalize_comparable_value(field_name, value) for value in values if str(value).strip()}
            if len(normalized) > 1:
                triggered = True
                evidence_refs.append(EvidenceRef(note=f"{field_name} values: {sorted(normalized)}"))

    if logic.get("compare_dates"):
        date_field_pattern = str(logic.get("field_pattern_date", "")).strip()
        date_values = _collect_values_by_field_pattern(ctx, date_field_pattern)
        normalized_dates = {
            _parse_date_value(value).isoformat()
            if _parse_date_value(value)
            else _normalize_comparable_value(date_field_pattern, value)
            for value in date_values
            if str(value).strip()
        }
        if len(normalized_dates) > 1:
            triggered = True
            evidence_refs.append(EvidenceRef(note=f"{date_field_pattern} values: {sorted(normalized_dates)}"))

    return _base_rule_result(rule, triggered=triggered, evidence_refs=evidence_refs)


def _document_type_by_id(ctx: CaseContext) -> Dict[uuid.UUID, str]:
    mapping: Dict[uuid.UUID, str] = {}
    for doc in ctx.documents or []:
        if getattr(doc, "id", None) and getattr(doc, "doc_type", None):
            mapping[doc.id] = doc.doc_type
    return mapping


def _page_doc_type(ctx: CaseContext, doc_id: uuid.UUID) -> Optional[str]:
    mapping = _document_type_by_id(ctx)
    if doc_id in mapping:
        return mapping[doc_id]
    for doc in ctx.documents or []:
        if getattr(doc, "id", None) == doc_id:
            inferred = infer_doc_type_from_filename(getattr(doc, "original_filename", "") or "")
            return inferred
    return None


def evaluate_keyword_risk(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Search OCR text for risk keywords."""
    logic = rule.get("logic", {})
    keywords = logic.get("keywords_any", [])
    if not keywords:
        keywords = rule.get("inputs", {}).get("keywords", [])
    in_doc_types = [_canonical_doc_type(item) for item in logic.get("in_doc_types", []) if str(item).strip()]
    cleared_by = [_canonical_doc_type(item) for item in logic.get("cleared_by_doc_types", []) if str(item).strip()]

    if cleared_by and _has_required_doc_type(cleared_by, ctx):
        return _base_rule_result(rule, triggered=False)

    triggered = False
    evidence_refs: List[EvidenceRef] = []
    found_keywords: set[str] = set()

    for doc_id, page_num, ocr_text in ctx.pages:
        if in_doc_types:
            page_type = _page_doc_type(ctx, doc_id)
            if page_type and _canonical_doc_type(page_type) not in in_doc_types:
                continue
        matched = _find_keywords_in_text(ocr_text, keywords)
        if not matched:
            continue
        triggered = True
        found_keywords.update(matched)
        if not any(ref.document_id == doc_id and ref.page_number == page_num for ref in evidence_refs):
            evidence_refs.append(
                EvidenceRef(
                    document_id=doc_id,
                    page_number=page_num,
                    note=f"Contains keyword(s): {', '.join(sorted(set(matched)))}",
                )
            )

    description = rule.get("outputs", {}).get("exception", "")
    if found_keywords:
        description += f" (Keywords found: {', '.join(sorted(found_keywords))})"

    return _base_rule_result(
        rule,
        triggered=triggered,
        description=description,
        evidence_refs=evidence_refs,
    )


def evaluate_constructed_gate(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Check for missing evidence only if property appears to be constructed."""
    logic = rule.get("logic", {})
    constructed_indicators = logic.get("constructed_indicators", [])
    required_types = logic.get("required_doc_types", [])

    is_constructed_likely = False
    if "property.constructed" in ctx.dossier:
        if any(value.lower() in {"true", "yes", "1"} for value in ctx.dossier["property.constructed"]):
            is_constructed_likely = True

    if not is_constructed_likely:
        for _, _, ocr_text in ctx.pages:
            if _text_contains_keyword(ocr_text, constructed_indicators):
                is_constructed_likely = True
                break

    triggered = is_constructed_likely and not _has_required_doc_type(required_types, ctx)
    description = rule.get("outputs", {}).get("exception", "")
    if triggered:
        description += " (Property appears constructed)"

    return _base_rule_result(rule, triggered=triggered, description=description)


def evaluate_timeline_gap(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    raise ValueError("timeline_gap evaluator is not supported")


def evaluate_verification_check(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Check if verification is required and not yet completed."""
    verification_type = rule.get("inputs", {}).get("verification_type", "")
    keywords = rule.get("inputs", {}).get("keywords", [])
    dossier_keys = rule.get("inputs", {}).get("dossier_keys", [])

    verification_status = ctx.verifications.get(verification_type, "Pending")
    if verification_status == "Verified":
        return _base_rule_result(rule, triggered=False)

    has_keys = False
    for key in dossier_keys:
        if ctx.dossier.get(key):
            has_keys = True
            break
        for dossier_key, values in ctx.dossier.items():
            if key in dossier_key and values:
                has_keys = True
                break
        if has_keys:
            break

    has_keywords = False
    evidence_refs: List[EvidenceRef] = []
    for doc_id, page_num, ocr_text in ctx.pages:
        matched = _find_keywords_in_text(ocr_text, keywords)
        if matched:
            has_keywords = True
            evidence_refs.append(
                EvidenceRef(
                    document_id=doc_id,
                    page_number=page_num,
                    note=f"Contains keyword(s): {', '.join(sorted(set(matched)))}",
                )
            )
            break

    triggered = has_keys or has_keywords
    description = rule.get("outputs", {}).get("exception", "")
    if triggered and verification_status == "Failed":
        description += " (Previous verification attempt failed)"

    return _base_rule_result(
        rule,
        triggered=triggered,
        description=description,
        evidence_refs=evidence_refs,
    )


def _facts_for(ctx: CaseContext, key: str) -> List[DocumentFact]:
    return [fact for fact in (ctx.document_facts or []) if fact.key == key and (fact.value or "").strip()]


def _parse_fact_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _naive_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.min
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return datetime.min


def _document_created_at(ctx: CaseContext, document_id: Optional[str]) -> datetime:
    if not document_id:
        return datetime.min
    for doc in ctx.documents or []:
        if str(getattr(doc, "id", "")) != str(document_id):
            continue
        return _naive_datetime(getattr(doc, "created_at", None))
    return datetime.min


def _document_created_date(ctx: CaseContext, document_id: Optional[str]) -> date:
    created = _document_created_at(ctx, document_id)
    if created == datetime.min:
        return date.min
    return created.date()


def _fact_recency(ctx: CaseContext, fact: DocumentFact) -> date:
    """Which instrument is current on file.

    Upload time may break ties between documents. It is not a legal issue date.
    """
    best = date.min
    for dated in _facts_for(ctx, "fact.issue_date"):
        if dated.document_id != fact.document_id:
            continue
        parsed = parse_date_value(dated.value)
        if parsed and parsed > best:
            best = parsed
    created = _document_created_at(ctx, fact.document_id)
    created_as_date = created.date() if created != datetime.min else date.min
    return max(best, created_as_date)


def _area_fact_score(fact: DocumentFact, marlas: float) -> float:
    blob = f"{fact.snippet or ''} {fact.value or ''}"
    score = 0.0
    if "کل رقبہ" in blob:
        score += 100.0
    if "Kanal" in (fact.value or ""):
        score += 10.0
    score += min(marlas, 400.0) / 10.0
    return score


def _preferred_areas(parsed: List[Tuple[DocumentFact, float]]) -> List[Tuple[DocumentFact, float]]:
    grouped: Dict[str, Tuple[DocumentFact, float]] = {}
    for fact, marlas in parsed:
        key = fact.document_id or f"{fact.doc_type}:{fact.page_number}:{fact.value}"
        prev = grouped.get(key)
        if prev is None or _area_fact_score(fact, marlas) > _area_fact_score(prev[0], prev[1]):
            grouped[key] = (fact, marlas)
    return list(grouped.values())


def evaluate_area_mismatch(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Compare property area facts from title instruments vs revenue record."""
    areas = _facts_for(ctx, "fact.area")
    parsed: List[Tuple[DocumentFact, float]] = []
    for fact in areas:
        marlas = area_to_marlas(fact.value)
        if marlas is not None:
            parsed.append((fact, marlas))
    parsed = _preferred_areas(parsed)
    if len(parsed) < 2:
        return _base_rule_result(rule, triggered=False)

    title_keys = {"sale_deed", "possession_letter"}
    record_keys = {"fard", "mutation"}
    title = [item for item in parsed if canonical_key(item[0].doc_type) in title_keys]
    records = [item for item in parsed if canonical_key(item[0].doc_type) in record_keys]
    fards = [item for item in records if canonical_key(item[0].doc_type) == "fard"]
    if fards:
        records = fards
    if not title or not records:
        return _base_rule_result(rule, triggered=False)

    newest_record = max(
        records,
        key=lambda item: (
            _document_created_at(ctx, item[0].document_id),
            _fact_recency(ctx, item[0]),
        ),
    )
    left = max(title, key=lambda item: _area_fact_score(item[0], item[1]))
    delta = abs(left[1] - newest_record[1])
    triggered = delta > 0.5
    refs = []
    if triggered:
        refs = [
            EvidenceRef(
                document_id=_parse_fact_uuid(left[0].document_id),
                page_number=left[0].page_number,
                note=f"Title area {left[0].value} ({left[1]:.1f} marla)",
            ),
            EvidenceRef(
                document_id=_parse_fact_uuid(newest_record[0].document_id),
                page_number=newest_record[0].page_number,
                note=f"Record area {newest_record[0].value} ({newest_record[1]:.1f} marla)",
            ),
        ]
    return _base_rule_result(rule, triggered=triggered, evidence_refs=refs)


def _target_documents(ctx: CaseContext, target_types: List[str]) -> List[Any]:
    matched = []
    for doc in ctx.documents or []:
        key = canonical_key(getattr(doc, "doc_type", None))
        if target_types and key not in target_types:
            continue
        matched.append(doc)
    return matched


def _issue_dates_for_document(ctx: CaseContext, document_id: Optional[str], target_types: List[str]) -> List[Tuple[DocumentFact, date]]:
    dated: List[Tuple[DocumentFact, date]] = []
    for fact in _facts_for(ctx, "fact.issue_date"):
        key = canonical_key(fact.doc_type)
        if target_types and key not in target_types:
            continue
        if document_id and str(fact.document_id or "") != str(document_id):
            continue
        parsed = parse_date_value(fact.value)
        if not parsed:
            continue
        dated.append((fact, parsed))
    return dated


def evaluate_stale_document(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Trigger when the newest instrument is stale or has no parseable issue date.

    Upload time selects which document is current on file. It is never treated
    as the legal issue date. Missing dates stay unconfirmed rather than current.
    """
    logic = rule.get("logic", {}) or {}
    target_types = [_canonical_doc_type(item) for item in logic.get("doc_types", [])]
    max_age_days = int(logic.get("max_age_days") or 90)
    as_of_raw = logic.get("as_of_date")
    as_of = parse_date_value(str(as_of_raw)) if as_of_raw else date.today()
    if as_of is None:
        as_of = date.today()

    target_docs = _target_documents(ctx, target_types)
    if target_docs:
        newest_doc = max(
            target_docs,
            key=lambda doc: (
                _document_created_at(ctx, str(getattr(doc, "id", "") or "")),
                str(getattr(doc, "id", "") or ""),
            ),
        )
        newest_id = str(getattr(newest_doc, "id", "") or "")
        dated = _issue_dates_for_document(ctx, newest_id, target_types)
        if not dated:
            return _base_rule_result(
                rule,
                triggered=True,
                title="Fard date unconfirmed" if "fard" in target_types else "Document date unconfirmed",
                description=(
                    "The newest document of this type has no parseable issue date. "
                    "Upload time is not treated as the legal issue date."
                ),
                evidence_refs=[
                    EvidenceRef(
                        document_id=_parse_fact_uuid(newest_id),
                        page_number=1,
                        note=f"Newest {getattr(newest_doc, 'doc_type', None) or 'document'} issue date unconfirmed",
                    )
                ],
            )
        newest_fact, newest_date = max(dated, key=lambda item: item[1])
    else:
        dated = _issue_dates_for_document(ctx, None, target_types)
        if not dated:
            return _base_rule_result(rule, triggered=False)
        newest_fact, newest_date = max(dated, key=lambda item: item[1])

    age_days = (as_of - newest_date).days
    triggered = age_days > max_age_days
    refs = [
        EvidenceRef(
            document_id=_parse_fact_uuid(newest_fact.document_id),
            page_number=newest_fact.page_number,
            note=f"Newest {newest_fact.doc_type or 'document'} dated {newest_date.isoformat()} ({age_days} days old)",
        )
    ]
    return _base_rule_result(rule, triggered=triggered, evidence_refs=refs)


def _normalize_person_org_name(value: str) -> str:
    text = re.sub(r"[^\w\u0600-\u06FF]+", " ", value or "", flags=re.UNICODE)
    drop = {
        "pvt", "pvt.", "private", "limited", "ltd", "company", "the",
        "لمیٹڈ", "پرائیویٹ", "کمپنی",
    }
    tokens = [tok for tok in text.casefold().split() if tok not in drop]
    return " ".join(tokens)


def evaluate_name_variation(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Party/owner names that are similar but not identical across sources."""
    logic = rule.get("logic", {}) or {}
    cleared_by = logic.get("cleared_by_doc_types") or []
    if cleared_by and _has_required_doc_type(cleared_by, ctx):
        return _base_rule_result(rule, triggered=False)

    from app.services.extractors.validators import is_plausible_party_name

    names: List[Tuple[str, DocumentFact]] = []
    for fact in ctx.document_facts or []:
        if fact.key not in {"fact.owner_name", "party.buyer.names"}:
            continue
        value = (fact.value or "").strip()
        if not value:
            continue
        if not is_plausible_party_name(value, role="buyer")[0]:
            continue
        names.append((value, fact))

    normalized = []
    for raw, fact in names:
        compact = _normalize_person_org_name(raw)
        if compact:
            normalized.append((compact, raw, fact))
    unique = {item[0] for item in normalized}
    if len(unique) <= 1:
        return _base_rule_result(rule, triggered=False)

    variants = sorted({item[1] for item in normalized})
    refs = [
        EvidenceRef(
            document_id=_parse_fact_uuid(item[2].document_id),
            page_number=item[2].page_number,
            note=f"Name variant: {item[1]}",
        )
        for item in normalized
    ]
    description = (rule.get("outputs", {}).get("exception", "") + f" Variants: {variants}").strip()
    return _base_rule_result(rule, triggered=True, description=description, evidence_refs=refs)


def evaluate_historical_keyword(rule: Dict[str, Any], ctx: CaseContext) -> RuleResult:
    """Finding that stays open for controlled waiver (historic tax, etc.)."""
    if _facts_for(ctx, "fact.tax_history"):
        facts = _facts_for(ctx, "fact.tax_history")
        refs = [
            EvidenceRef(
                document_id=_parse_fact_uuid(fact.document_id),
                page_number=fact.page_number,
                note=fact.snippet or fact.value,
            )
            for fact in facts
        ]
        return _base_rule_result(rule, triggered=True, evidence_refs=refs)
    return evaluate_keyword_risk(rule, ctx)


EVALUATORS = {
    "missing_evidence": evaluate_missing_evidence,
    "mismatch": evaluate_mismatch,
    "keyword_risk": evaluate_keyword_risk,
    "timeline_gap": evaluate_timeline_gap,
    "verification_check": evaluate_verification_check,
    "constructed_gate": evaluate_constructed_gate,
    "area_mismatch": evaluate_area_mismatch,
    "stale_document": evaluate_stale_document,
    "name_variation": evaluate_name_variation,
    "historical_keyword": evaluate_historical_keyword,
}

_REGIME_EQ_CONDITIONAL_RE = re.compile(
    r"if\s+regime\s*==\s*([A-Za-z0-9_]+)",
    re.IGNORECASE,
)


def _case_regime_from_context(ctx: CaseContext) -> Optional[Regime]:
    """First canonical non-UNKNOWN regime from dossier property.regime."""
    values = ctx.dossier.get("property.regime") or []
    for raw in values:
        if not raw or not str(raw).strip():
            continue
        regime = normalize_regime(str(raw).strip())
        if regime is None or regime == Regime.UNKNOWN:
            continue
        return regime
    return None


def _rule_required_regimes(rule: Dict) -> List[str]:
    """Regime codes this rule applies to; empty list means no regime restriction."""
    logic = rule.get("logic") or {}
    structured = logic.get("regimes")
    if isinstance(structured, list) and structured:
        return [str(item).strip().upper() for item in structured if str(item).strip()]

    conditional = logic.get("conditional")
    if isinstance(conditional, str):
        match = _REGIME_EQ_CONDITIONAL_RE.search(conditional)
        if match:
            return [match.group(1).upper()]
    return []


def _rule_applies(ctx: CaseContext, rule: Dict[str, Any]) -> bool:
    applies = rule.get("applies_when") or {}
    if not isinstance(applies, dict):
        applies = {}

    required_borrower = [str(item).strip().lower() for item in applies.get("borrower_type") or [] if str(item).strip()]
    borrower = (ctx.borrower_type or "individual").lower()
    if required_borrower and borrower not in required_borrower:
        return False

    required_txn = [str(item).strip().lower() for item in applies.get("transaction_type") or [] if str(item).strip()]
    txn = (ctx.transaction_type or "mortgage").lower()
    if required_txn and txn not in required_txn:
        return False

    required_regimes = [str(item).strip().upper() for item in applies.get("regime") or [] if str(item).strip()]
    if required_regimes:
        case_regime = _case_regime_from_context(ctx)
        if case_regime is None:
            return False
        if case_regime.value not in required_regimes:
            return False

    return True


def _rule_should_run(case_regime: Optional[Regime], rule: Dict, ctx: Optional[CaseContext] = None) -> bool:
    required = _rule_required_regimes(rule)
    if required:
        if case_regime is None:
            return False
        if case_regime.value not in required:
            return False
    if ctx is not None and not _rule_applies(ctx, rule):
        return False
    return True


def _ensure_case_preconditions(ctx: CaseContext, rules: List[Dict[str, Any]]) -> None:
    if not ctx.ocr_complete:
        raise RuleEnginePreconditionError("OCR incomplete; cannot evaluate rulepack until OCR is complete.")

    case_regime = _case_regime_from_context(ctx)
    if case_regime is None and any(_rule_required_regimes(rule) for rule in rules):
        raise RuleEnginePreconditionError("property.regime is required to evaluate regime-conditional rules.")


def evaluate_rule(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Evaluate a single rule against case context."""
    evaluator_name = rule.get("evaluator", "missing_evidence")
    evaluator = EVALUATORS.get(evaluator_name)
    if evaluator is None:
        raise ValueError(f"Unknown evaluator '{evaluator_name}' for rule {rule.get('id', 'unknown')}")
    return evaluator(rule, ctx)


def evaluate_ruleset(ctx: CaseContext, rules: Optional[List[Dict[str, Any]]] = None) -> List[RuleResult]:
    if rules is None:
        rulepack = load_rulepack()
        rules = rulepack.get("rules", [])

    rules = list(rules or [])
    _ensure_case_preconditions(ctx, rules)
    case_regime = _case_regime_from_context(ctx)

    results: List[RuleResult] = []
    for rule in rules:
        if not _rule_should_run(case_regime, rule, ctx):
            continue
        results.append(evaluate_rule(rule, ctx))
    return results


def compute_case_decision(
    items: Iterable[Any],
    *,
    open_material_cps: int = 0,
    required_evidence_deficient: bool = False,
    approval_rejected: bool = False,
    required_evidence_complete: bool = True,
    required_fields_confirmed: bool = True,
) -> str:
    """PASS / CONDITIONAL_PASS / FAIL from live findings.

    Open CPs are residual conditions, not a clearance. High ≠ hard-stop.
    """
    has_conditional_high = False

    for item in items:
        triggered = getattr(item, "triggered", True)
        if not triggered:
            continue

        status = getattr(item, "status", "Open") or "Open"
        severity = getattr(item, "severity", "")
        is_hard_stop = bool(getattr(item, "is_hard_stop", False))

        if is_hard_stop and status in OPEN_STATUSES:
            return "FAIL"
        if severity == "High" and status in OPEN_STATUSES:
            return "FAIL"
        if severity == "High" and status == "Waived":
            has_conditional_high = True

    if approval_rejected or required_evidence_deficient:
        return "FAIL"
    if has_conditional_high or open_material_cps > 0:
        return "CONDITIONAL_PASS"
    if not required_evidence_complete or not required_fields_confirmed:
        return "CONDITIONAL_PASS"
    return "PASS"


def run_rules(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Dict[str, Any]:
    """Run all rules against a case, create exceptions and CPs, and persist the decision."""
    started_at = datetime.utcnow()
    rule_run = RuleRun(
        org_id=org_id,
        case_id=case_id,
        started_at=started_at,
    )
    db.add(rule_run)
    db.flush()

    try:
        from app.services.regime_classifier import infer_and_store_regime
        from app.services.dossier_autofill import infer_and_store_case_context
        infer_and_store_regime(db, case_id, org_id, overwrite=False)
        infer_and_store_case_context(db, case_id, org_id)
        ctx = build_case_context(db, org_id, case_id)
        rulepack = load_rulepack()
        rules = rulepack.get("rules", [])
        if not rules and rulepack.get("errors"):
            raise ValueError("; ".join(rulepack["errors"]))

        db.query(ExceptionEvidenceRef).filter(
            ExceptionEvidenceRef.org_id == org_id,
            ExceptionEvidenceRef.exception_id.in_(
                db.query(Exception_.id).filter(
                    Exception_.case_id == case_id,
                    Exception_.org_id == org_id,
                    Exception_.status == "Open",
                )
            ),
        ).delete(synchronize_session=False)

        db.query(Exception_).filter(
            Exception_.case_id == case_id,
            Exception_.org_id == org_id,
            Exception_.status == "Open",
        ).delete(synchronize_session=False)

        db.query(ConditionPrecedent).filter(
            ConditionPrecedent.case_id == case_id,
            ConditionPrecedent.org_id == org_id,
            ConditionPrecedent.status == "Open",
        ).delete(synchronize_session=False)

        preserved_rule_ids = {
            row.rule_id
            for row in db.query(Exception_).filter(
                Exception_.case_id == case_id,
                Exception_.org_id == org_id,
                Exception_.status.in_(tuple(PRESERVED_EXCEPTION_STATUSES)),
            ).all()
            if row.rule_id
        }

        results = evaluate_ruleset(ctx, rules=rules)
        counts: Dict[str, Any] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
            "cps_total": 0,
            "hard_stop_count": 0,
        }

        for result in results:
            if not result.triggered:
                continue
            if result.rule_id in preserved_rule_ids:
                continue

            exc = Exception_(
                org_id=org_id,
                case_id=case_id,
                rule_id=result.rule_id,
                module=result.module,
                severity=result.severity,
                title=result.title,
                description=result.description,
                evidence_refs=[
                    {
                        "document_id": str(ref.document_id) if ref.document_id else None,
                        "page_number": ref.page_number,
                        "note": ref.note,
                    }
                    for ref in result.evidence_refs
                ],
                cp_text=result.cp_text,
                resolution_conditions=result.resolution_conditions,
                is_hard_stop=result.is_hard_stop,
                status="Open",
            )
            db.add(exc)
            db.flush()

            for ref in result.evidence_refs:
                db.add(
                    ExceptionEvidenceRef(
                        org_id=org_id,
                        exception_id=exc.id,
                        document_id=ref.document_id,
                        page_number=ref.page_number,
                        note=ref.note,
                        is_closing=False,
                    )
                )

            if result.cp_text:
                db.add(
                    ConditionPrecedent(
                        org_id=org_id,
                        case_id=case_id,
                        rule_id=result.rule_id,
                        severity=result.severity,
                        text=result.cp_text,
                        evidence_required=result.evidence_required,
                        status="Open",
                    )
                )
                counts["cps_total"] += 1

            severity_lower = result.severity.lower()
            if severity_lower in counts:
                counts[severity_lower] += 1
            if result.is_hard_stop:
                counts["hard_stop_count"] += 1
            counts["total"] += 1

        db.flush()
        live_exceptions = (
            db.query(Exception_)
            .filter(Exception_.case_id == case_id, Exception_.org_id == org_id)
            .all()
        )
        open_cps = (
            db.query(ConditionPrecedent)
            .filter(
                ConditionPrecedent.case_id == case_id,
                ConditionPrecedent.org_id == org_id,
                ConditionPrecedent.status == "Open",
            )
            .count()
        )
        counts["cps_total"] = int(open_cps)
        decision = compute_case_decision(live_exceptions, open_material_cps=int(open_cps))
        counts["decision"] = decision

        case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
        if case:
            case.decision = decision

        rule_run.finished_at = datetime.utcnow()
        rule_run.summary = counts
        db.commit()
        return counts

    except Exception as exc:
        rule_run.finished_at = datetime.utcnow()
        rule_run.summary = {"error": str(exc)}
        db.commit()
        raise
