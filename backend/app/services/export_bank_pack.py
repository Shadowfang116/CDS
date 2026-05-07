"""Bank pack PDF generation service."""

import io
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
SEVERITY_COLORS = {
    "Critical": "#ef4444",
    "High": "#f59e0b",
    "Medium": "#eab308",
    "Low": "#60a5fa",
}
DEFAULT_REQUIRED_EVIDENCE = "Supporting annexure confirmed by reviewer"
DEFAULT_CLOSURE_GUIDANCE = (
    "Reviewer confirmation required. Obtain supporting annexure, authority verification, or other "
    "documentary basis acceptable to the Bank before closure."
)
DEFAULT_CP_RECOMMENDED_TEXT = (
    "Prior to approval / disbursement, the borrower shall provide supporting annexure and reviewer "
    "confirmation acceptable to the Bank for this issue."
)
RULE_ID_ALIASES = {
    "LDA_001": "LAYOUT_APPROVAL_MISSING",
    "REG_001": "MISSING_REGISTERED_SALE_DEED",
    "TPA_CHAIN_GAP_001": "TITLE_CHAIN_GAP",
    "TPA_NOTICE_POSSESSION_001": "POSSESSION_EVIDENCE_MISSING",
    "TPA_CAPACITY_001": "CAPACITY_OR_AUTHORITY_ISSUE",
    "SOC_001": "SOCIETY_NOC_MISSING",
    "SOC_002": "SOCIETY_TRANSFER_MEMBERSHIP_ISSUE",
    "RUDA_001": "AUTHORITY_APPROVAL_DEPENDENCY",
    "CANT_001": "CANTONMENT_NOC_MISSING",
}


@lru_cache(maxsize=1)
def _load_rule_evidence_library() -> Dict[str, Dict[str, Any]]:
    library_path = Path(__file__).resolve().parents[3] / "frontend" / "config" / "rules_evidence.json"

    try:
        with library_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _get_borrower_label(dossier: Dict[str, List[str]]) -> str:
    borrower_values = dossier.get("party.name.borrower") or dossier.get("party.buyer.names") or []
    if borrower_values:
        return borrower_values[0]
    return "Borrower / client not recorded"


def _first_dossier_value(dossier: Dict[str, List[str]], *keys: str, default: str = "Not recorded") -> str:
    for key in keys:
        values = dossier.get(key) or []
        if values:
            return values[0]
    return default


def _is_open(item: Dict[str, Any]) -> bool:
    return item.get("status") == "Open"


def _open_exception_counts(exceptions: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for exception in exceptions:
        severity = exception.get("severity", "Low")
        if _is_open(exception) and severity in counts:
            counts[severity] += 1
    return counts


def _count_by_severity_status(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    counts = {
        "Critical": {"Open": 0, "Resolved": 0, "Waived": 0},
        "High": {"Open": 0, "Resolved": 0, "Waived": 0},
        "Medium": {"Open": 0, "Resolved": 0, "Waived": 0},
        "Low": {"Open": 0, "Resolved": 0, "Waived": 0},
    }

    for item in items:
        severity = item.get("severity", "Medium")
        status = item.get("status", "Open")
        if severity in counts and status in counts[severity]:
            counts[severity][status] += 1

    return counts


def _derive_decision(
    case: Dict[str, Any], exceptions: List[Dict[str, Any]], cps: List[Dict[str, Any]]
) -> Dict[str, str]:
    open_counts = _open_exception_counts(exceptions)
    open_cps = sum(1 for cp in cps if cp.get("status") == "Open")
    residual = open_counts["Medium"] + open_counts["Low"]
    case_status = case.get("status")

    if case_status == "Rejected" or open_counts["Critical"] >= 1 or open_counts["High"] >= 2:
        return {
            "label": "Review Required",
            "color": "#ef4444",
            "rationale": "Critical title or approval Exceptions remain outstanding and the matter is not yet ready for approval consideration.",
        }
    if open_counts["High"] >= 1:
        return {
            "label": "Hold",
            "color": "#f59e0b",
            "rationale": "One or more high-severity Exceptions require closure or Waiver before the credit decision can proceed.",
        }
    if open_cps > 0 or residual > 0:
        return {
            "label": "Proceed with Conditions",
            "color": "#eab308",
            "rationale": "No critical Exceptions remain open, but Conditions Precedent or residual Exceptions still require closure before full readiness.",
        }
    return {
        "label": "Ready",
        "color": "#588c66",
        "rationale": "No unresolved Exceptions or open Conditions Precedent remain on the matter.",
    }


def _truncate_text(value: str | None, max_length: int = 180) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "No reviewer description recorded."
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length].rstrip()}..."


def _normalize_fallback_evidence(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]
    return []


def _get_rule_evidence(rule_id: str | None, fallback_evidence: Any = None) -> Dict[str, Any]:
    resolved_rule_id = RULE_ID_ALIASES.get(rule_id or "", rule_id or "")
    configured = _load_rule_evidence_library().get(resolved_rule_id, {})
    fallback_required = _normalize_fallback_evidence(fallback_evidence)
    return {
        "required_evidence": configured.get("required_evidence") or fallback_required or [DEFAULT_REQUIRED_EVIDENCE],
        "acceptable_substitutes": configured.get("acceptable_substitutes") or [],
        "closure_guidance": configured.get("closure_guidance") or DEFAULT_CLOSURE_GUIDANCE,
        "cp_recommended_text": configured.get("cp_recommended_text") or DEFAULT_CP_RECOMMENDED_TEXT,
        "reviewer_confirmation_required": not bool(configured),
    }


def _is_evidence_satisfied(evidence_refs: List[Dict[str, Any]] | None) -> bool:
    return bool(evidence_refs)


def _format_evidence_ref(ref: Dict[str, Any], documents: Dict[str, Dict[str, Any]]) -> str:
    document_id = ref.get("document_id")
    page_num = ref.get("page_number")
    note = ref.get("note")

    label = "Annexure reference pending"
    if document_id and document_id in documents:
        label = documents[document_id].get("original_filename", "Unknown document")
    elif page_num:
        label = f"Page {page_num}"

    segments = [label]
    if page_num and document_id in documents:
        segments.append(f"Page {page_num}")
    if note:
        segments.append(str(note))
    return " • ".join(segments)


def _get_key_issues(exceptions: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    prioritized = sorted(
        [exception for exception in exceptions if _is_open(exception)],
        key=lambda item: (SEVERITY_ORDER.get(item.get("severity", "Low"), 3), item.get("title", "")),
    )
    return prioritized[:limit]


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def _append_label_value_rows(
    story: List[Any],
    rows: List[List[str]],
    widths: List[float],
    table_style: List[Tuple[Any, ...]],
) -> None:
    table = Table(rows, colWidths=widths)
    table.setStyle(TableStyle(table_style))
    story.append(table)


def _draw_watermark(label: str):
    def _callback(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 56)
        canvas.setFillColor(colors.Color(0.55, 0.57, 0.62, alpha=0.12))
        canvas.translate(300, 420)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, label)
        canvas.restoreState()
    return _callback


def generate_bank_pack_pdf(
    case: Dict[str, Any],
    org: Dict[str, Any],
    dossier: Dict[str, List[str]],
    exceptions: List[Dict[str, Any]],
    cps: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    evidence_refs: Dict[str, List[Dict[str, Any]]],
    verifications: List[Dict[str, Any]] | None = None,
    dossier_fields: List[Dict[str, Any]] | None = None,
) -> Tuple[bytes, str]:
    """Generate a bank pack PDF."""

    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BankPackTitle",
        parent=styles["Heading1"],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "BankPackSubtitle",
        parent=styles["Heading2"],
        fontSize=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4d5966"),
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "BankPackHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1f2933"),
        spaceBefore=14,
        spaceAfter=10,
    )
    subheading_style = ParagraphStyle(
        "BankPackSubheading",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#38424d"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BankPackBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1f2933"),
    )
    muted_style = ParagraphStyle(
        "BankPackMuted",
        parent=body_style,
        textColor=colors.HexColor("#66727f"),
    )

    story: List[Any] = []
    verifications = verifications or []
    dossier_fields = dossier_fields or []
    document_lookup = {str(document.get("id")): document for document in documents}
    case_ref = str(case.get("id", ""))[:8].upper()
    generated_on = datetime.utcnow().strftime("%d %B %Y")
    org_name = org.get("name", "Covenant Diligence Systems")
    borrower = _get_borrower_label(dossier)
    open_counts = _open_exception_counts(exceptions)
    open_cps = sum(1 for cp in cps if cp.get("status") == "Open")
    waived_exceptions = sum(1 for exception in exceptions if exception.get("status") == "Waived")
    satisfied_cps = sum(1 for cp in cps if cp.get("status") == "Satisfied")
    decision = _derive_decision(case, exceptions, cps)
    key_issues = _get_key_issues(exceptions)
    counts = _count_by_severity_status(exceptions)
    approval_ready = open_counts["High"] == 0 and open_cps == 0

    property_address = _first_dossier_value(dossier, "property.address", "property.scheme_name", default="Property details not recorded")
    transaction_amount = _first_dossier_value(dossier, "transaction.amount_pkr", default="PKR amount not recorded")
    title_type = _first_dossier_value(dossier, "title.title_type", default="Title type not recorded")
    matter_reference = _first_dossier_value(dossier, "matter.reference", default=case_ref)
    generated_timestamp = datetime.utcnow().strftime("%d %B %Y %I:%M %p UTC")
    open_exception_total = sum(open_counts.values())
    waived_cps = sum(1 for cp in cps if cp.get("status") == "Waived")
    closed_cps = satisfied_cps + waived_cps
    cp_completion_pct = int(round((closed_cps / len(cps)) * 100)) if cps else 100

    story.append(_paragraph(org_name.upper(), title_style))
    story.append(_paragraph("BANK PACK [DRAFT]", title_style))
    story.append(_paragraph("Property-Backed Finance Matter Pack", subtitle_style))

    story.append(_paragraph("MATTER HEADER", heading_style))
    matter_rows = [
        ["Matter Name", case.get("title", "N/A"), "Matter Reference", matter_reference],
        ["Date", generated_on, "Institution / Firm", org_name],
        ["Borrower", borrower, "Matter Status", case.get("status", "N/A")],
    ]
    _append_label_value_rows(
        story,
        matter_rows,
        [1.35 * inch, 2.35 * inch, 1.35 * inch, 1.85 * inch],
        [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ],
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(_paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(
        _paragraph(
            f"This matter concerns {property_address} and is being reviewed in connection with a property-backed finance transaction for {borrower}. The reported transaction value is {transaction_amount} and the working title classification is {title_type}.",
            body_style,
        )
    )
    story.append(
        _paragraph(
            f"The current readiness signal is <font color='{decision['color']}'><b>{decision['label']}</b></font>. There are {open_exception_total} outstanding Exceptions and CP completion is presently {cp_completion_pct}%, so the matter should continue through controlled legal review before any final approval step.",
            body_style,
        )
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(_paragraph("DECISION / READINESS SIGNAL", heading_style))
    readiness_rows = [
        ["Signal", decision["label"]],
        ["Outstanding Exceptions", str(open_exception_total)],
        ["Critical Exceptions", str(open_counts["Critical"])],
        ["High Exceptions", str(open_counts["High"])],
        ["CP Completion", f"{cp_completion_pct}%"],
        ["Decision Basis", decision["rationale"]],
    ]
    readiness_table = Table(readiness_rows, colWidths=[2.2 * inch, 4.1 * inch])
    readiness_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#253746")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f6d6d4") if decision['label'] == "Review Required" else colors.HexColor("#f8f0d7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(readiness_table)

    story.append(Spacer(1, 0.18 * inch))
    story.append(_paragraph("EXCEPTIONS SUMMARY", heading_style))
    exception_rows = [["Severity", "Exception", "Status", "Evidence / Annexure"]]
    for exception in sorted(exceptions, key=lambda item: SEVERITY_ORDER.get(item.get("severity", "Low"), 99)):
        refs = evidence_refs.get(str(exception.get("id")), [])
        evidence_label = ", ".join(_format_evidence_ref(ref, document_lookup) for ref in refs[:3]) or "Annexure reference pending"
        exception_rows.append(
            [
                exception.get("severity", "-"),
                _truncate_text(exception.get("title"), 80),
                exception.get("status", "Open"),
                evidence_label,
            ]
        )
    if len(exception_rows) > 1:
        exception_table = Table(exception_rows, colWidths=[0.95 * inch, 2.8 * inch, 0.9 * inch, 2.35 * inch])
        exception_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253746")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(exception_table)
    else:
        story.append(_paragraph("No Exceptions are recorded for this matter.", muted_style))

    story.append(Spacer(1, 0.18 * inch))
    story.append(_paragraph("CP SUMMARY", heading_style))
    cp_rows = [["Severity", "Condition Precedent", "Status", "Evidence Required"]]
    for cp in sorted(cps, key=lambda item: SEVERITY_ORDER.get(item.get("severity", "Low"), 99)):
        cp_rows.append(
            [
                cp.get("severity", "-"),
                _truncate_text(cp.get("text"), 95),
                "Fulfilled" if cp.get("status") == "Satisfied" else ("Pending" if cp.get("status") == "Open" else cp.get("status", "Pending")),
                _truncate_text(cp.get("evidence_required"), 90),
            ]
        )
    if len(cp_rows) > 1:
        cp_table = Table(cp_rows, colWidths=[0.95 * inch, 2.95 * inch, 0.9 * inch, 2.2 * inch])
        cp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253746")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(cp_table)
    else:
        story.append(_paragraph("No Conditions Precedent are currently recorded for this matter.", muted_style))

    story.append(Spacer(1, 0.18 * inch))
    story.append(_paragraph("DOSSIER FIELDS", heading_style))
    key_fields = {
        "matter.reference": "Matter Reference",
        "party.name.borrower": "Borrower",
        "property.address": "Property Address",
        "property.scheme_name": "Scheme / Area",
        "property.block": "Block",
        "transaction.amount_pkr": "Transaction Amount",
        "title.title_type": "Title Type",
        "title.registry_reference": "Registry Reference",
        "revenue.mutation_reference": "Mutation Reference",
        "authority.noc_reference": "Authority NOC",
    }
    dossier_field_lookup: Dict[str, List[Dict[str, Any]]] = {}
    for field in dossier_fields:
        dossier_field_lookup.setdefault(field.get("field_key"), []).append(field)

    dossier_rows = [["Field", "Value", "Evidence / Source"]]
    for field_key, field_label in key_fields.items():
        values = dossier.get(field_key, [])
        if not values:
            continue
        source_label = "Manual confirmation"
        field_sources = dossier_field_lookup.get(field_key, [])
        if field_sources:
            source = field_sources[0]
            if source.get("source_document_id") in document_lookup:
                source_doc = document_lookup[source["source_document_id"]]
                source_label = source_doc.get("original_filename", "Unknown document")
                if source.get("source_page_number"):
                    source_label = f"{source_label} - Page {source['source_page_number']}"
        dossier_rows.append([field_label, ", ".join(values[:2]), source_label])

    if len(dossier_rows) > 1:
        dossier_table = Table(dossier_rows, colWidths=[1.8 * inch, 2.7 * inch, 2.0 * inch])
        dossier_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253746")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(dossier_table)
    else:
        story.append(_paragraph("No structured dossier fields have been confirmed for this matter.", muted_style))

    story.append(PageBreak())
    story.append(_paragraph("ANNEXURES / EVIDENCE REFERENCES", heading_style))
    story.append(_paragraph("Reviewed Annexures", subheading_style))
    annexure_rows = [["#", "Annexure / Evidence", "Type", "Pages"]]
    for index, document in enumerate(documents, start=1):
        annexure_rows.append(
            [
                str(index),
                document.get("original_filename", "Unknown document"),
                document.get("doc_type", "-"),
                str(document.get("page_count") or "-"),
            ]
        )
    if len(annexure_rows) > 1:
        annexure_table = Table(annexure_rows, colWidths=[0.35 * inch, 3.7 * inch, 1.45 * inch, 0.55 * inch])
        annexure_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253746")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(annexure_table)
    else:
        story.append(_paragraph("No annexures are currently linked to this matter.", muted_style))

    story.append(Spacer(1, 0.16 * inch))
    story.append(_paragraph("Evidence Cross-reference", subheading_style))
    evidence_rows = [["Exception / CP", "Evidence Reference"]]
    for exception in exceptions:
        refs = evidence_refs.get(str(exception.get("id")), [])
        evidence_rows.append(
            [
                exception.get("title", "Exception"),
                ", ".join(_format_evidence_ref(ref, document_lookup) for ref in refs[:3]) or "Annexure reference pending",
            ]
        )
    for cp in cps:
        linked_refs = cp.get("evidence_refs", [])
        evidence_rows.append(
            [
                _truncate_text(cp.get("text"), 70),
                ", ".join(_format_evidence_ref(ref, document_lookup) for ref in linked_refs[:3]) or _truncate_text(cp.get("evidence_required"), 90),
            ]
        )
    if len(evidence_rows) > 1:
        evidence_table = Table(evidence_rows, colWidths=[2.65 * inch, 3.65 * inch])
        evidence_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253746")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(evidence_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        _paragraph(
            f"Generation timestamp: {generated_timestamp}. This Bank Pack is a structured internal draft prepared for legal and banking review only.",
            ParagraphStyle("BankPackFooter", parent=muted_style, fontSize=8),
        )
    )

    watermark_label = "APPROVED" if case.get("status") == "Approved" else "DRAFT"
    pdf_doc.build(story, onFirstPage=_draw_watermark(watermark_label), onLaterPages=_draw_watermark(watermark_label))
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    case_id_str = str(case.get("id", ""))
    file_date = datetime.utcnow().strftime("%Y%m%d")
    filename = f"BANK_PACK__CASE_{case_id_str}__{file_date}__v1.pdf"

    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata(
            {
                "/Title": "Bank Pack - Credit Decision Support Memorandum",
                "/Creator": "Covenant Diligence Systems",
            }
        )
        out = io.BytesIO()
        writer.write(out)
        pdf_bytes = out.getvalue()
    except Exception:
        pass

    return pdf_bytes, filename
