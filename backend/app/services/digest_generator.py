"""Digest PDF generation service."""
import uuid
import io
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.models.case import Case
from app.models.rules import Exception_, ConditionPrecedent
from app.models.verification import Verification
from app.models.export import Export
from app.models.digest import DigestSchedule, DigestRun
from app.models.org import Org
from app.services.storage import put_object_bytes, get_presigned_get_url
from app.services.audit import write_audit_event


def generate_digest_for_run(db: Session, run_id: uuid.UUID, actor_user_id: uuid.UUID) -> Optional[str]:
    """
    Generate a digest PDF for a specific run.
    Returns presigned URL on success, None on failure.
    """
    # Get run and schedule
    run = db.query(DigestRun).filter(DigestRun.id == run_id).first()
    if not run:
        return None
    
    schedule = db.query(DigestSchedule).filter(DigestSchedule.id == run.schedule_id).first()
    if not schedule:
        run.status = "failed"
        run.error_message = "Schedule not found"
        db.commit()
        return None
    
    org = db.query(Org).filter(Org.id == schedule.org_id).first()
    org_name = org.name if org else "Unknown Organization"
    
    try:
        # Get filters from schedule
        filters = schedule.filters_json or {}
        days = filters.get("days", 30)
        severity_filter = filters.get("severity")
        status_filter = filters.get("status")
        
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=days)
        org_id = schedule.org_id
        
        # Gather KPIs
        active_cases = db.query(func.count(Case.id)).filter(
            Case.org_id == org_id,
            Case.status != "Closed",
            Case.created_at >= cutoff_date,
        ).scalar() or 0
        
        open_high = db.query(func.count(Exception_.id)).filter(
            Exception_.org_id == org_id,
            Exception_.severity == "High",
            Exception_.status == "Open",
        ).scalar() or 0
        
        open_medium = db.query(func.count(Exception_.id)).filter(
            Exception_.org_id == org_id,
            Exception_.severity == "Medium",
            Exception_.status == "Open",
        ).scalar() or 0
        
        open_low = db.query(func.count(Exception_.id)).filter(
            Exception_.org_id == org_id,
            Exception_.severity == "Low",
            Exception_.status == "Open",
        ).scalar() or 0
        
        # CP completion
        cp_satisfied = db.query(func.count(ConditionPrecedent.id)).filter(
            ConditionPrecedent.org_id == org_id,
            or_(
                ConditionPrecedent.status == "Satisfied",
                ConditionPrecedent.satisfied_at.isnot(None),
            ),
        ).scalar() or 0
        
        cp_open = db.query(func.count(ConditionPrecedent.id)).filter(
            ConditionPrecedent.org_id == org_id,
            ConditionPrecedent.status == "Open",
        ).scalar() or 0
        
        cp_total = cp_satisfied + cp_open
        cp_pct = round((cp_satisfied / cp_total * 100), 1) if cp_total > 0 else 100.0
        
        # Verification completion
        verified = db.query(func.count(Verification.id)).filter(
            Verification.org_id == org_id,
            Verification.status == "Verified",
        ).scalar() or 0
        
        pending = db.query(func.count(Verification.id)).filter(
            Verification.org_id == org_id,
            Verification.status == "Pending",
        ).scalar() or 0
        
        verif_total = verified + pending
        verif_pct = round((verified / verif_total * 100), 1) if verif_total > 0 else 100.0
        
        # Needs attention cases (top 10)
        cases_with_high_sq = db.query(
            Exception_.case_id,
            func.count(Exception_.id).label("high_count"),
        ).filter(
            Exception_.org_id == org_id,
            Exception_.severity == "High",
            Exception_.status == "Open",
        ).group_by(Exception_.case_id).subquery()
        
        cases_with_pending_sq = db.query(
            Verification.case_id,
            func.count(Verification.id).label("pending_count"),
        ).filter(
            Verification.org_id == org_id,
            Verification.status == "Pending",
        ).group_by(Verification.case_id).subquery()
        
        needs_attention = db.query(
            Case.title,
            Case.status,
            func.coalesce(cases_with_high_sq.c.high_count, 0).label("open_high"),
            func.coalesce(cases_with_pending_sq.c.pending_count, 0).label("pending_verifs"),
        ).outerjoin(
            cases_with_high_sq, Case.id == cases_with_high_sq.c.case_id
        ).outerjoin(
            cases_with_pending_sq, Case.id == cases_with_pending_sq.c.case_id
        ).filter(
            Case.org_id == org_id,
            Case.created_at >= cutoff_date,
            or_(
                cases_with_high_sq.c.high_count > 0,
                cases_with_pending_sq.c.pending_count > 0,
            ),
        ).order_by(
            func.coalesce(cases_with_high_sq.c.high_count, 0).desc(),
        ).limit(10).all()
        
        # Generate PDF
        pdf_bytes = create_digest_pdf(
            org_name=org_name,
            schedule_name=schedule.name,
            run_timestamp=now,
            days=days,
            active_cases=active_cases,
            open_high=open_high,
            open_medium=open_medium,
            open_low=open_low,
            cp_pct=cp_pct,
            verif_pct=verif_pct,
            needs_attention=needs_attention,
        )
        
        # Store in MinIO
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        filename = f"digest_{schedule.name.replace(' ', '_')}_{timestamp_str}.pdf"
        object_key = f"case-files/org/{org_id}/exports/digests/{filename}"
        
        put_object_bytes(object_key, pdf_bytes, "application/pdf")
        
        # Create Export record
        export = Export(
            org_id=org_id,
            case_id=None,
            export_type="digest_pdf",
            filename=filename,
            content_type="application/pdf",
            minio_key=object_key,
            created_by_user_id=actor_user_id,
        )
        db.add(export)
        db.commit()
        db.refresh(export)
        
        # Update run
        run.status = "success"
        run.output_export_id = export.id
        db.commit()
        
        # Audit log
        write_audit_event(
            db=db,
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="digest.run_completed",
            entity_type="digest_run",
            entity_id=run.id,
            event_metadata={
                "run_id": str(run.id),
                "schedule_id": str(schedule.id),
                "status": "success",
                "export_id": str(export.id),
            },
        )
        
        return get_presigned_get_url(object_key, expires_seconds=3600)
    
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)[:500]
        db.commit()
        
        # Audit log failure
        write_audit_event(
            db=db,
            org_id=schedule.org_id,
            actor_user_id=actor_user_id,
            action="digest.run_completed",
            entity_type="digest_run",
            entity_id=run.id,
            event_metadata={
                "run_id": str(run.id),
                "schedule_id": str(schedule.id),
                "status": "failed",
                "error": str(e)[:200],
            },
        )
        
        return None


def create_digest_pdf(
    org_name: str,
    schedule_name: str,
    run_timestamp: datetime,
    days: int,
    active_cases: int,
    open_high: int,
    open_medium: int,
    open_low: int,
    cp_pct: float,
    verif_pct: float,
    needs_attention: list,
) -> bytes:
    """Create a digest PDF and return bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DigestTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        textColor=colors.HexColor('#1e293b'),
    )
    heading_style = ParagraphStyle(
        'DigestHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#334155'),
    )
    normal_style = ParagraphStyle(
        'DigestNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#475569'),
    )
    
    elements = []
    
    # Title page
    elements.append(Paragraph(f"{org_name}", title_style))
    elements.append(Paragraph(f"Digest Report: {schedule_name}", heading_style))
    elements.append(Paragraph(
        f"Generated: {run_timestamp.strftime('%Y-%m-%d %H:%M UTC')} | Range: Last {days} days",
        normal_style
    ))
    elements.append(Spacer(1, 30))
    
    # KPIs section
    elements.append(Paragraph("Key Performance Indicators", heading_style))
    
    kpi_data = [
        ["Metric", "Value"],
        ["Active Cases", str(active_cases)],
        ["Open High Exceptions", str(open_high)],
        ["Open Medium Exceptions", str(open_medium)],
        ["Open Low Exceptions", str(open_low)],
        ["CP Completion", f"{cp_pct}%"],
        ["Verification Completion", f"{verif_pct}%"],
    ]
    
    kpi_table = Table(kpi_data, colWidths=[3*inch, 2*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f1f5f9')]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 30))
    
    # Needs attention section
    elements.append(Paragraph("Cases Needing Attention", heading_style))
    
    if needs_attention:
        attention_data = [["Case Title", "Status", "High Ex.", "Pending Verif."]]
        for row in needs_attention:
            attention_data.append([
                row.title[:40] + "..." if len(row.title) > 40 else row.title,
                row.status,
                str(row.open_high),
                str(row.pending_verifs),
            ])
        
        attention_table = Table(attention_data, colWidths=[3*inch, 1.2*inch, 0.9*inch, 1.1*inch])
        attention_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f1f5f9')]),
        ]))
        elements.append(attention_table)
    else:
        elements.append(Paragraph("No cases currently need attention.", normal_style))
    
    elements.append(Spacer(1, 30))
    
    # Footer
    elements.append(Paragraph(
        "This report was automatically generated by the Bank Diligence Platform.",
        ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.HexColor('#94a3b8'))
    ))
    
    doc.build(elements)
    return buffer.getvalue()

