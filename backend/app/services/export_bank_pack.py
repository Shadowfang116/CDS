"""D5: Bank Pack PDF generation service using ReportLab. Phase 8: deterministic filename and ordering."""
import io
from datetime import datetime
from typing import List, Dict, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def _get_decision(exceptions: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Determine the executive decision.
    
    Returns (decision, color_code).
    """
    open_high = [e for e in exceptions if e.get("status") == "Open" and e.get("severity") == "High"]
    waived_high = [e for e in exceptions if e.get("status") == "Waived" and e.get("severity") == "High"]
    
    if not open_high and not waived_high:
        return "PASS", "#28a745"
    elif not open_high and waived_high:
        return "CONDITIONAL PASS", "#ffc107"
    else:
        return "FAIL", "#dc3545"


def _count_by_severity_status(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Count items by severity and status."""
    counts = {
        "High": {"Open": 0, "Resolved": 0, "Waived": 0},
        "Medium": {"Open": 0, "Resolved": 0, "Waived": 0},
        "Low": {"Open": 0, "Resolved": 0, "Waived": 0},
    }
    
    for item in items:
        sev = item.get("severity", "Medium")
        status = item.get("status", "Open")
        if sev in counts and status in counts[sev]:
            counts[sev][status] += 1
    
    return counts


def _format_evidence_ref(ref: Dict[str, Any], documents: Dict[str, Dict]) -> str:
    """Format an evidence reference as 'filename p.X'."""
    doc_id = ref.get("document_id")
    page_num = ref.get("page_number")
    
    if doc_id and doc_id in documents:
        filename = documents[doc_id].get("original_filename", "Unknown")
        if page_num:
            return f"{filename} p.{page_num}"
        return filename
    elif page_num:
        return f"Page {page_num}"
    return "Evidence not specified"


def generate_bank_pack_pdf(
    case: Dict[str, Any],
    org: Dict[str, Any],
    dossier: Dict[str, List[str]],
    exceptions: List[Dict[str, Any]],
    cps: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    evidence_refs: Dict[str, List[Dict[str, Any]]],  # exception_id -> list of refs
    verifications: List[Dict[str, Any]] = None,  # Verification records
    dossier_fields: List[Dict[str, Any]] = None,  # Full dossier field objects with source info
) -> Tuple[bytes, str]:
    """
    Generate a Bank Pack PDF.
    
    Returns (pdf_bytes, filename).
    """
    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#1a5276'),
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    # Build document lookup
    doc_lookup = {str(d.get("id")): d for d in documents}
    
    case_ref = str(case.get("id", ""))[:8].upper()
    date_str = datetime.utcnow().strftime("%d %B %Y")
    org_name = org.get("name", "Bank Due Diligence")
    
    # ================================================================
    # COVER / EXECUTIVE SUMMARY
    # ================================================================
    
    story.append(Paragraph(org_name.upper(), title_style))
    story.append(Paragraph("BANK PACK - DUE DILIGENCE REPORT", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Case info table
    case_data = [
        ["Case Reference:", case_ref],
        ["Case Title:", case.get("title", "N/A")],
        ["Status:", case.get("status", "N/A")],
        ["Generated:", date_str],
    ]
    
    case_table = Table(case_data, colWidths=[2*inch, 4*inch])
    case_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(case_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Decision
    decision, decision_color = _get_decision(exceptions)
    
    decision_style = ParagraphStyle(
        'Decision',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor(decision_color),
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=20,
    )
    
    story.append(Paragraph(f"DECISION: {decision}", decision_style))
    
    # Exception counts
    counts = _count_by_severity_status(exceptions)
    
    count_data = [
        ["Severity", "Open", "Resolved", "Waived", "Total"],
        ["High", str(counts["High"]["Open"]), str(counts["High"]["Resolved"]), 
         str(counts["High"]["Waived"]), str(sum(counts["High"].values()))],
        ["Medium", str(counts["Medium"]["Open"]), str(counts["Medium"]["Resolved"]), 
         str(counts["Medium"]["Waived"]), str(sum(counts["Medium"].values()))],
        ["Low", str(counts["Low"]["Open"]), str(counts["Low"]["Resolved"]), 
         str(counts["Low"]["Waived"]), str(sum(counts["Low"].values()))],
    ]
    
    count_table = Table(count_data, colWidths=[1.2*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.8*inch])
    count_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        # Color code High row
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#ffebee')),
        ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#fff8e1')),
        ('BACKGROUND', (0, 3), (0, 3), colors.HexColor('#e3f2fd')),
    ]))
    story.append(count_table)
    
    # ================================================================
    # VERIFICATION SUMMARY (after Executive Summary)
    # ================================================================
    
    if verifications is None:
        verifications = []
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("VERIFICATION SUMMARY", heading_style))
    
    verification_types = {
        "e_stamp": "e-Stamp Verification",
        "registry_rod": "Registry / ROD Verification",
    }
    
    # Build verification lookup
    v_lookup = {v.get("verification_type"): v for v in verifications}
    
    for v_type, v_label in verification_types.items():
        v_data = v_lookup.get(v_type)
        
        story.append(Paragraph(f"<b>{v_label}</b>", subheading_style))
        
        if v_data:
            status = v_data.get("status", "Pending")
            status_color = {"Verified": "#28a745", "Failed": "#dc3545", "Pending": "#ffc107"}.get(status, "#6c757d")
            
            # Status row
            status_style = ParagraphStyle(
                f'VerStatus{v_type}',
                parent=normal_style,
                textColor=colors.HexColor(status_color),
            )
            story.append(Paragraph(f"Status: <b>{status}</b>", status_style))
            
            # Keys (if any)
            keys_json = v_data.get("keys_json", {})
            if keys_json:
                story.append(Paragraph("Verification Keys:", normal_style))
                for key, value in keys_json.items():
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;• {key}: {value}", normal_style))
            
            # Verified by / at
            if v_data.get("verified_by_email"):
                story.append(Paragraph(
                    f"Verified by: {v_data['verified_by_email']}", 
                    normal_style
                ))
            if v_data.get("verified_at"):
                story.append(Paragraph(
                    f"Verified at: {v_data['verified_at'][:19].replace('T', ' ')}", 
                    normal_style
                ))
            
            # Evidence refs
            v_evidence = v_data.get("evidence_refs", [])
            if v_evidence:
                story.append(Paragraph("Evidence:", normal_style))
                for ev in v_evidence:
                    filename = ev.get("filename", "Unknown")
                    page_num = ev.get("page_number", 1)
                    story.append(Paragraph(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;• {filename} p.{page_num}",
                        normal_style
                    ))
            elif status == "Pending":
                story.append(Paragraph(
                    "<i>Required Action: Complete verification via official portal and attach evidence</i>",
                    ParagraphStyle('Required', parent=normal_style, textColor=colors.HexColor('#856404'))
                ))
            
            # Notes
            if v_data.get("notes"):
                story.append(Paragraph(f"Notes: {v_data['notes']}", normal_style))
        else:
            # No verification record exists
            story.append(Paragraph("Status: <b>Pending</b>", 
                ParagraphStyle('Pending', parent=normal_style, textColor=colors.HexColor('#ffc107'))
            ))
            story.append(Paragraph(
                "<i>Required Action: Complete verification via official portal and attach evidence</i>",
                ParagraphStyle('Required', parent=normal_style, textColor=colors.HexColor('#856404'))
            ))
        
        story.append(Spacer(1, 0.15*inch))
    
    story.append(PageBreak())
    
    # ================================================================
    # DOSSIER SUMMARY (AUTOFILLED)
    # ================================================================
    
    story.append(Paragraph("DOSSIER SUMMARY (AUTOFILLED)", heading_style))
    
    # Key dossier fields to display
    key_fields = {
        'property.plot_number': 'Plot Number',
        'property.block': 'Block',
        'property.phase': 'Phase',
        'property.scheme_name': 'Scheme Name',
        'property.district': 'District',
        'property.tehsil': 'Tehsil',
        'property.mouza': 'Mouza',
        'property.khasra_numbers': 'Khasra Numbers',
        'registry.registry_number': 'Registry Number',
        'registry.registry_date': 'Registry Date',
        'stamp.estamp_id_or_number': 'e-Stamp ID/Number',
    }
    
    # Build dossier field lookup with source info
    dossier_field_lookup = {}
    if dossier_fields:
        for df in dossier_fields:
            field_key = df.get('field_key')
            if field_key not in dossier_field_lookup:
                dossier_field_lookup[field_key] = []
            dossier_field_lookup[field_key].append(df)
    
    # Get dossier fields (dossier is Dict[str, List[str]])
    dossier_rows = []
    for field_path, field_label in key_fields.items():
        values = dossier.get(field_path, [])
        if values:
            value_str = ', '.join(values[:3])  # Limit to first 3 values
            if len(values) > 3:
                value_str += f' (+{len(values) - 3} more)'
            
            # Get source evidence info
            evidence_str = '—'
            field_objs = dossier_field_lookup.get(field_path, [])
            if field_objs:
                first_field = field_objs[0]
                source_doc_id = first_field.get('source_document_id')
                source_page = first_field.get('source_page_number')
                if source_doc_id and source_doc_id in doc_lookup:
                    filename = doc_lookup[source_doc_id].get('original_filename', 'Unknown')
                    if source_page:
                        evidence_str = f'{filename} p.{source_page}'
                    else:
                        evidence_str = filename
            
            dossier_rows.append([field_label, value_str, evidence_str])
    
    if dossier_rows:
        dossier_data = [["Field", "Value", "Evidence"]] + dossier_rows
        
        dossier_table = Table(dossier_data, colWidths=[2*inch, 2.5*inch, 2*inch])
        dossier_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(dossier_table)
    else:
        story.append(Paragraph("No dossier fields autofilled yet.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(PageBreak())
    
    # ================================================================
    # EXCEPTIONS SECTION
    # ================================================================
    
    story.append(Paragraph("EXCEPTIONS", heading_style))
    
    # Group by severity then module
    for severity in ["High", "Medium", "Low"]:
        severity_exceptions = [e for e in exceptions if e.get("severity") == severity]
        
        if not severity_exceptions:
            continue
        
        sev_color = {"High": "#dc3545", "Medium": "#ffc107", "Low": "#17a2b8"}.get(severity, "#6c757d")
        
        sev_style = ParagraphStyle(
            f'Sev{severity}',
            parent=subheading_style,
            textColor=colors.HexColor(sev_color),
        )
        story.append(Paragraph(f"{severity} Priority Exceptions ({len(severity_exceptions)})", sev_style))
        
        # Group by module
        modules = {}
        for exc in severity_exceptions:
            module = exc.get("module", "Other")
            if module not in modules:
                modules[module] = []
            modules[module].append(exc)
        
        for module, module_exceptions in modules.items():
            story.append(Paragraph(f"<b>{module}</b>", normal_style))
            
            for exc in module_exceptions:
                exc_id = str(exc.get("id", ""))
                status = exc.get("status", "Open")
                status_marker = {"Open": "⚠", "Resolved": "✓", "Waived": "~"}.get(status, "")
                
                # Exception details
                exc_text = f"{status_marker} <b>{exc.get('title', 'Exception')}</b> [{status}]"
                story.append(Paragraph(exc_text, normal_style))
                
                if exc.get("description"):
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{exc['description']}", normal_style))
                
                # Evidence refs
                refs = evidence_refs.get(exc_id, [])
                if refs:
                    ref_texts = [_format_evidence_ref(r, doc_lookup) for r in refs]
                    story.append(Paragraph(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Evidence: {', '.join(ref_texts)}</i>", 
                        normal_style
                    ))
                
                # CP text
                if exc.get("cp_text"):
                    story.append(Paragraph(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>CP:</b> {exc['cp_text']}", 
                        normal_style
                    ))
                
                story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())
    
    # ================================================================
    # CONDITIONS PRECEDENT SECTION
    # ================================================================
    
    story.append(Paragraph("CONDITIONS PRECEDENT", heading_style))
    
    for severity in ["High", "Medium", "Low"]:
        severity_cps = [c for c in cps if c.get("severity") == severity]
        
        if not severity_cps:
            continue
        
        sev_color = {"High": "#dc3545", "Medium": "#ffc107", "Low": "#17a2b8"}.get(severity, "#6c757d")
        
        sev_style = ParagraphStyle(
            f'CP{severity}',
            parent=subheading_style,
            textColor=colors.HexColor(sev_color),
        )
        story.append(Paragraph(f"{severity} Priority ({len(severity_cps)})", sev_style))
        
        for cp in severity_cps:
            status = cp.get("status", "Open")
            status_marker = {"Open": "○", "Satisfied": "●", "Waived": "◐"}.get(status, "○")
            
            cp_text = f"{status_marker} {cp.get('text', '')} [{status}]"
            story.append(Paragraph(cp_text, normal_style))
            
            if cp.get("evidence_required"):
                story.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Required: {cp['evidence_required']}</i>",
                    normal_style
                ))
            
            story.append(Spacer(1, 0.05*inch))
        
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())
    
    # ================================================================
    # ANNEXURE INDEX
    # ================================================================
    
    story.append(Paragraph("ANNEXURE INDEX", heading_style))
    
    # Document list
    story.append(Paragraph("<b>Documents Reviewed</b>", subheading_style))
    
    if documents:
        doc_data = [["#", "Filename", "Type", "Pages"]]
        
        for i, doc in enumerate(documents, 1):
            doc_data.append([
                str(i),
                doc.get("original_filename", "Unknown"),
                doc.get("doc_type", "—"),
                str(doc.get("page_count", "—")),
            ])
        
        doc_table = Table(doc_data, colWidths=[0.4*inch, 3*inch, 1.5*inch, 0.6*inch])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(doc_table)
    else:
        story.append(Paragraph("No documents in case.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Evidence references summary
    story.append(Paragraph("<b>Evidence References by Rule</b>", subheading_style))
    
    # Collect all refs
    all_refs = []
    for exc in exceptions:
        exc_id = str(exc.get("id", ""))
        exc_refs = evidence_refs.get(exc_id, [])
        if exc_refs:
            ref_texts = [_format_evidence_ref(r, doc_lookup) for r in exc_refs]
            all_refs.append([exc.get("rule_id", "—"), ", ".join(ref_texts)])
    
    if all_refs:
        ref_data = [["Rule ID", "Evidence"]] + all_refs
        
        ref_table = Table(ref_data, colWidths=[1*inch, 4.5*inch])
        ref_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(ref_table)
    else:
        story.append(Paragraph("No evidence references recorded.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Verification Evidence sub-section
    story.append(Paragraph("<b>Verification Evidence</b>", subheading_style))
    
    verification_types_labels = {
        "e_stamp": "e-Stamp",
        "registry_rod": "Registry/ROD",
    }
    
    v_evidence_rows = []
    for v in (verifications or []):
        v_type = v.get("verification_type", "")
        v_label = verification_types_labels.get(v_type, v_type)
        v_status = v.get("status", "Pending")
        
        for ev in v.get("evidence_refs", []):
            v_evidence_rows.append([
                v_label,
                v_status,
                ev.get("filename", "Unknown"),
                str(ev.get("page_number", 1)),
            ])
    
    if v_evidence_rows:
        v_ev_data = [["Verification Type", "Status", "Filename", "Page"]] + v_evidence_rows
        
        v_ev_table = Table(v_ev_data, colWidths=[1.2*inch, 0.8*inch, 2.8*inch, 0.5*inch])
        v_ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(v_ev_table)
    else:
        story.append(Paragraph("No verification evidence documents attached.", normal_style))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        f"<i>Generated by {org_name} Due Diligence System on {date_str}</i>",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey)
    ))
    
    # Build PDF
    pdf_doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    # Phase 8: deterministic filename and stable PDF metadata
    case_id_str = str(case.get("id", ""))
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"BANK_PACK__CASE_{case_id_str}__{date_str}__v1.pdf"

    # Set consistent creator/title (no volatile metadata)
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata({
            "/Title": "Bank Pack - Due Diligence Report",
            "/Creator": "Bank Diligence Platform",
        })
        out = io.BytesIO()
        writer.write(out)
        pdf_bytes = out.getvalue()
    except Exception:
        pass  # keep original bytes if metadata step fails

    return pdf_bytes, filename

