"""D5: DOCX draft generation service."""
import io
from datetime import datetime
from typing import List, Dict, Any, Tuple

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _add_header(doc: Document, org_name: str, case_ref: str, date: str, title: str):
    """Add standard header to document."""
    # Organization name
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run(org_name.upper())
    run.bold = True
    run.font.size = Pt(14)
    
    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run(title)
    run.bold = True
    run.font.size = Pt(12)
    
    doc.add_paragraph()
    
    # Case reference and date
    ref_para = doc.add_paragraph()
    ref_para.add_run(f"Case Reference: ").bold = True
    ref_para.add_run(case_ref)
    
    date_para = doc.add_paragraph()
    date_para.add_run(f"Date: ").bold = True
    date_para.add_run(date)
    
    doc.add_paragraph()


def _add_section(doc: Document, title: str, items: List[str]):
    """Add a section with bullet points."""
    heading = doc.add_paragraph()
    run = heading.add_run(title)
    run.bold = True
    run.font.size = Pt(11)
    
    if not items:
        doc.add_paragraph("None noted.", style='List Bullet')
    else:
        for item in items:
            doc.add_paragraph(item, style='List Bullet')
    
    doc.add_paragraph()


def _format_exception(exc: Dict[str, Any]) -> str:
    """Format an exception for display."""
    status_marker = ""
    if exc.get("status") == "Resolved":
        status_marker = " [RESOLVED]"
    elif exc.get("status") == "Waived":
        status_marker = " [WAIVED]"
    
    text = f"[{exc.get('severity', 'Medium')}] {exc.get('title', 'Exception')}{status_marker}"
    if exc.get("description"):
        text += f": {exc['description']}"
    return text


def _format_cp(cp: Dict[str, Any]) -> str:
    """Format a CP for display."""
    text = f"[{cp.get('severity', 'Medium')}] {cp.get('text', '')}"
    if cp.get("evidence_required"):
        text += f" (Evidence: {cp['evidence_required']})"
    return text


def _get_borrower_info(dossier: Dict[str, List[str]]) -> Dict[str, str]:
    """Extract borrower information from dossier."""
    info = {
        "name": "[CONFIRM - Borrower Name]",
        "cnic": "[CONFIRM - CNIC]",
        "address": "[CONFIRM - Address]",
    }
    
    # Get name
    names = dossier.get("party.name.raw", [])
    if names:
        info["name"] = names[0]
    
    # Get CNIC
    cnics = dossier.get("party.cnic", [])
    if cnics:
        info["cnic"] = cnics[0]
    
    return info


def _get_property_info(dossier: Dict[str, List[str]]) -> str:
    """Extract property description from dossier."""
    parts = []
    
    if dossier.get("property.plot"):
        parts.append(f"Plot {dossier['property.plot'][0]}")
    if dossier.get("property.block"):
        parts.append(f"Block {dossier['property.block'][0]}")
    if dossier.get("property.phase"):
        parts.append(f"Phase {dossier['property.phase'][0]}")
    if dossier.get("property.society"):
        parts.append(dossier["property.society"][0])
    
    if parts:
        return ", ".join(parts)
    return "[CONFIRM - Property Description]"


def generate_discrepancy_letter(
    case: Dict[str, Any],
    org: Dict[str, Any],
    dossier: Dict[str, List[str]],
    exceptions: List[Dict[str, Any]],
    cps: List[Dict[str, Any]],
) -> Tuple[bytes, str]:
    """
    Generate a discrepancy letter DOCX.
    
    Returns (bytes, filename).
    """
    doc = Document()
    
    case_ref = str(case.get("id", ""))[:8].upper()
    date_str = datetime.utcnow().strftime("%d %B %Y")
    org_name = org.get("name", "Bank Due Diligence")
    
    _add_header(doc, org_name, case_ref, date_str, "DISCREPANCY LETTER")
    
    # Addressee
    borrower = _get_borrower_info(dossier)
    doc.add_paragraph(f"To: {borrower['name']}")
    doc.add_paragraph(f"CNIC: {borrower['cnic']}")
    doc.add_paragraph()
    
    # Subject
    subject = doc.add_paragraph()
    subject.add_run("Subject: ").bold = True
    subject.add_run(f"Discrepancies Noted in Loan Application - {case.get('title', 'Case')}")
    doc.add_paragraph()
    
    # Introduction
    doc.add_paragraph(
        "Dear Sir/Madam,\n\n"
        "We have reviewed the documentation submitted in support of your loan application. "
        "The following discrepancies and/or missing documents have been identified which "
        "require your immediate attention and rectification:"
    )
    doc.add_paragraph()
    
    # Open exceptions only
    open_exceptions = [e for e in exceptions if e.get("status") == "Open"]
    high_exc = [_format_exception(e) for e in open_exceptions if e.get("severity") == "High"]
    medium_exc = [_format_exception(e) for e in open_exceptions if e.get("severity") == "Medium"]
    low_exc = [_format_exception(e) for e in open_exceptions if e.get("severity") == "Low"]
    
    if high_exc:
        _add_section(doc, "Critical Issues (High Priority)", high_exc)
    if medium_exc:
        _add_section(doc, "Important Issues (Medium Priority)", medium_exc)
    if low_exc:
        _add_section(doc, "Minor Issues (Low Priority)", low_exc)
    
    # Required actions (CPs)
    open_cps = [c for c in cps if c.get("status") == "Open"]
    cp_texts = [_format_cp(c) for c in open_cps]
    _add_section(doc, "Required Actions / Documents", cp_texts)
    
    # Closing
    doc.add_paragraph(
        "You are requested to provide the above-mentioned documents and/or clarifications "
        "within seven (7) working days from the date of this letter. Failure to do so may "
        "result in delay or rejection of your loan application.\n\n"
        "For any queries, please contact the undersigned.\n\n"
        "Yours faithfully,"
    )
    doc.add_paragraph()
    doc.add_paragraph("[Authorized Signatory]")
    doc.add_paragraph(org_name)
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    filename = f"discrepancy_letter_{case_ref}_{datetime.utcnow().strftime('%Y%m%d')}.docx"
    
    return buffer.getvalue(), filename


def generate_undertaking_indemnity(
    case: Dict[str, Any],
    org: Dict[str, Any],
    dossier: Dict[str, List[str]],
    exceptions: List[Dict[str, Any]],
    cps: List[Dict[str, Any]],
) -> Tuple[bytes, str]:
    """
    Generate an undertaking and indemnity DOCX.
    
    Returns (bytes, filename).
    """
    doc = Document()
    
    case_ref = str(case.get("id", ""))[:8].upper()
    date_str = datetime.utcnow().strftime("%d %B %Y")
    org_name = org.get("name", "Bank Due Diligence")
    
    _add_header(doc, org_name, case_ref, date_str, "UNDERTAKING AND INDEMNITY")
    
    borrower = _get_borrower_info(dossier)
    property_desc = _get_property_info(dossier)
    
    # Undertaking text
    doc.add_paragraph(
        f"I, {borrower['name']}, bearing CNIC No. {borrower['cnic']}, hereby provide this "
        f"Undertaking and Indemnity in connection with my loan application for the property "
        f"situated at {property_desc} (the \"Property\")."
    )
    doc.add_paragraph()
    
    doc.add_paragraph("I hereby undertake and confirm as follows:")
    doc.add_paragraph()
    
    # Undertakings based on waivers
    waived = [e for e in exceptions if e.get("status") == "Waived"]
    
    undertakings = [
        "I am the lawful owner/allottee of the Property and have clear and marketable title.",
        "All information provided in my loan application is true and correct.",
        "I shall immediately notify the Bank of any change in circumstances affecting the Property.",
    ]
    
    for waived_exc in waived:
        undertakings.append(
            f"With respect to '{waived_exc.get('title', 'exception')}': I acknowledge this matter "
            f"and undertake to provide the required documentation within [30] days of disbursement."
        )
    
    for i, u in enumerate(undertakings, 1):
        doc.add_paragraph(f"{i}. {u}")
    
    doc.add_paragraph()
    
    # Indemnity
    heading = doc.add_paragraph()
    heading.add_run("INDEMNITY").bold = True
    
    doc.add_paragraph(
        f"I hereby agree to indemnify and hold harmless {org_name} against any loss, damage, "
        "cost, or expense arising from any misrepresentation, defect in title, or breach of "
        "the above undertakings."
    )
    doc.add_paragraph()
    
    # Signature block
    doc.add_paragraph("IN WITNESS WHEREOF, I have executed this Undertaking and Indemnity on the date first above written.")
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph("_____________________________")
    doc.add_paragraph(f"Name: {borrower['name']}")
    doc.add_paragraph(f"CNIC: {borrower['cnic']}")
    doc.add_paragraph()
    doc.add_paragraph("Witness 1: _____________________ CNIC: _____________________")
    doc.add_paragraph("Witness 2: _____________________ CNIC: _____________________")
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    filename = f"undertaking_indemnity_{case_ref}_{datetime.utcnow().strftime('%Y%m%d')}.docx"
    
    return buffer.getvalue(), filename


def generate_internal_opinion_skeleton(
    case: Dict[str, Any],
    org: Dict[str, Any],
    dossier: Dict[str, List[str]],
    exceptions: List[Dict[str, Any]],
    cps: List[Dict[str, Any]],
) -> Tuple[bytes, str]:
    """
    Generate an internal legal opinion skeleton DOCX.
    
    Returns (bytes, filename).
    """
    doc = Document()
    
    case_ref = str(case.get("id", ""))[:8].upper()
    date_str = datetime.utcnow().strftime("%d %B %Y")
    org_name = org.get("name", "Bank Due Diligence")
    
    _add_header(doc, org_name, case_ref, date_str, "INTERNAL LEGAL OPINION (SKELETON)")
    
    borrower = _get_borrower_info(dossier)
    property_desc = _get_property_info(dossier)
    
    # Executive summary
    heading = doc.add_paragraph()
    heading.add_run("1. EXECUTIVE SUMMARY").bold = True
    doc.add_paragraph()
    
    open_high = [e for e in exceptions if e.get("status") == "Open" and e.get("severity") == "High"]
    waived_high = [e for e in exceptions if e.get("status") == "Waived" and e.get("severity") == "High"]
    
    if not open_high and not waived_high:
        decision = "PASS - Proceed with disbursement"
    elif not open_high and waived_high:
        decision = "CONDITIONAL PASS - Proceed subject to undertaking execution"
    else:
        decision = "FAIL - Do not proceed until exceptions resolved"
    
    doc.add_paragraph(f"Recommendation: {decision}")
    doc.add_paragraph()
    
    # Case details
    heading = doc.add_paragraph()
    heading.add_run("2. CASE DETAILS").bold = True
    doc.add_paragraph()
    
    doc.add_paragraph(f"Case Title: {case.get('title', '[CONFIRM]')}")
    doc.add_paragraph(f"Borrower: {borrower['name']}")
    doc.add_paragraph(f"CNIC: {borrower['cnic']}")
    doc.add_paragraph(f"Property: {property_desc}")
    doc.add_paragraph()
    
    # Findings
    heading = doc.add_paragraph()
    heading.add_run("3. KEY FINDINGS").bold = True
    doc.add_paragraph()
    
    all_exceptions = [_format_exception(e) for e in exceptions]
    _add_section(doc, "Exceptions Identified", all_exceptions)
    
    # Title verification
    heading = doc.add_paragraph()
    heading.add_run("4. TITLE VERIFICATION").bold = True
    doc.add_paragraph()
    doc.add_paragraph("[To be completed by reviewing lawyer - verify chain of title, encumbrances, etc.]")
    doc.add_paragraph()
    
    # Conditions precedent
    heading = doc.add_paragraph()
    heading.add_run("5. CONDITIONS PRECEDENT").bold = True
    doc.add_paragraph()
    
    open_cps = [c for c in cps if c.get("status") == "Open"]
    cp_texts = [_format_cp(c) for c in open_cps]
    _add_section(doc, "Outstanding CPs", cp_texts)
    
    # Recommendation
    heading = doc.add_paragraph()
    heading.add_run("6. RECOMMENDATION").bold = True
    doc.add_paragraph()
    doc.add_paragraph(f"Based on the above analysis, the recommendation is: {decision}")
    doc.add_paragraph()
    doc.add_paragraph("[Additional comments by reviewing officer]")
    doc.add_paragraph()
    
    # Signature
    doc.add_paragraph()
    doc.add_paragraph("_____________________________")
    doc.add_paragraph("Prepared by: [Legal Officer Name]")
    doc.add_paragraph(f"Date: {date_str}")
    doc.add_paragraph()
    doc.add_paragraph("_____________________________")
    doc.add_paragraph("Reviewed by: [Senior Legal Counsel]")
    doc.add_paragraph("Date: _____________________")
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    filename = f"internal_opinion_{case_ref}_{datetime.utcnow().strftime('%Y%m%d')}.docx"
    
    return buffer.getvalue(), filename

