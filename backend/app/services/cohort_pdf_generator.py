"""Cohort PDF report generation service."""
import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def create_cohort_pdf(
    org_name: str,
    filters: Dict[str, Any],
    days: int,
    timestamp: datetime,
    kpis: Dict[str, Any],
    cases_by_status: Dict[str, int],
    exceptions_by_severity: Dict[str, int],
    cases: List[Dict[str, Any]],
) -> bytes:
    """
    Create a cohort PDF report and return bytes.
    
    Args:
        org_name: Organization name
        filters: Applied filters (severity, status, date)
        days: Date range in days
        timestamp: Report generation timestamp
        kpis: KPI values (active_cases, open_high, cp_pct, verif_pct)
        cases_by_status: Count of cases by status
        exceptions_by_severity: Open exceptions by severity
        cases: List of case data dicts
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=0.75*inch, 
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CohortTitle',
        parent=styles['Heading1'],
        fontSize=22,
        spaceAfter=15,
        textColor=colors.HexColor('#1e293b'),
    )
    heading_style = ParagraphStyle(
        'CohortHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#334155'),
    )
    subheading_style = ParagraphStyle(
        'CohortSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor('#475569'),
    )
    normal_style = ParagraphStyle(
        'CohortNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#475569'),
    )
    
    elements = []
    
    # ===== PAGE 1: Title + KPIs + Filters =====
    elements.append(Paragraph(f"{org_name} - Cohort Report", title_style))
    
    # Filters summary
    filter_parts = [f"Last {days} days"]
    if filters.get("severity"):
        filter_parts.append(f"Severity: {filters['severity']}")
    if filters.get("status"):
        filter_parts.append(f"Status: {filters['status']}")
    if filters.get("date"):
        filter_parts.append(f"Date: {filters['date']}")
    
    elements.append(Paragraph(
        f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M UTC')} | Filters: {' | '.join(filter_parts)}",
        normal_style
    ))
    elements.append(Spacer(1, 25))
    
    # KPIs section
    elements.append(Paragraph("Key Performance Indicators", heading_style))
    
    kpi_data = [
        ["Active Cases", "Open High Ex.", "Open Medium Ex.", "Open Low Ex."],
        [
            str(kpis.get("active_cases", 0)),
            str(exceptions_by_severity.get("high", 0)),
            str(exceptions_by_severity.get("medium", 0)),
            str(exceptions_by_severity.get("low", 0)),
        ],
    ]
    
    kpi_table = Table(kpi_data, colWidths=[1.7*inch, 1.5*inch, 1.6*inch, 1.4*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 15))
    
    # Completion rates
    completion_data = [
        ["CP Completion", "Verification Completion"],
        [
            f"{kpis.get('cp_pct', 100.0)}%",
            f"{kpis.get('verif_pct', 100.0)}%",
        ],
    ]
    
    completion_table = Table(completion_data, colWidths=[3*inch, 3*inch])
    completion_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(completion_table)
    elements.append(Spacer(1, 25))
    
    # Cases by status (simplified bar representation)
    elements.append(Paragraph("Cases by Status", subheading_style))
    
    status_rows = [["Status", "Count"]]
    for status, count in sorted(cases_by_status.items(), key=lambda x: -x[1]):
        if count > 0:
            status_rows.append([status, str(count)])
    
    if len(status_rows) > 1:
        status_table = Table(status_rows, colWidths=[4*inch, 1.5*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ]))
        elements.append(status_table)
    
    # ===== PAGE 2+: Cases Table =====
    elements.append(PageBreak())
    elements.append(Paragraph("Cases Detail", heading_style))
    elements.append(Paragraph(f"Showing {len(cases)} cases matching filters", normal_style))
    elements.append(Spacer(1, 15))
    
    if cases:
        # Header row
        case_data = [["Title", "Status", "High", "Med", "Low", "Pending V."]]
        
        for case in cases:
            title = case.get("title", "")
            if len(title) > 35:
                title = title[:32] + "..."
            case_data.append([
                title,
                case.get("status", ""),
                str(case.get("open_high", 0)),
                str(case.get("open_medium", 0)),
                str(case.get("open_low", 0)),
                str(case.get("pending_verifications", 0)),
            ])
        
        # Split into chunks if too many rows
        chunk_size = 25
        for i in range(0, len(case_data), chunk_size):
            chunk = case_data[i:i+chunk_size] if i == 0 else [case_data[0]] + case_data[i:i+chunk_size]
            
            case_table = Table(chunk, colWidths=[2.8*inch, 1*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch])
            case_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
            ]))
            elements.append(case_table)
            
            if i + chunk_size < len(case_data):
                elements.append(PageBreak())
    else:
        elements.append(Paragraph("No cases match the current filters.", normal_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "This report was automatically generated by the Bank Diligence Platform.",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.HexColor('#94a3b8'))
    ))
    
    doc.build(elements)
    return buffer.getvalue()

