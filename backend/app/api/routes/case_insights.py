"""Case insights API endpoint - per-case analytics and timeseries."""
from datetime import datetime, timedelta, date
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.case import Case
from app.models.rules import Exception_, ConditionPrecedent, RuleRun
from app.models.verification import Verification
from app.models.export import Export
from app.models.document import DocumentPage, Document
from app.schemas.dashboard import (
    CaseInsightsResponse,
    CaseInsightsSummary,
    CaseInsightsTimeseries,
)

router = APIRouter(prefix="/cases", tags=["case-insights"])


def generate_date_range(start_date: date, end_date: date) -> List[date]:
    """Generate a list of dates from start to end (inclusive)."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


@router.get("/{case_id}/insights", response_model=CaseInsightsResponse)
async def get_case_insights(
    request: Request,
    case_id: UUID,
    days: int = Query(default=30, ge=7, le=365, description="Date range in days"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get insights and analytics for a specific case.
    Returns summary stats and daily timeseries data.
    """
    org_id = current_user.org_id
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=days)
    today = now.date()
    start_date = (now - timedelta(days=days - 1)).date()

    # Verify case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Summary: Open exceptions by severity
    open_high = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.severity == "High",
        Exception_.status == "Open",
    ).scalar() or 0

    open_medium = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.severity == "Medium",
        Exception_.status == "Open",
    ).scalar() or 0

    open_low = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.severity == "Low",
        Exception_.status == "Open",
    ).scalar() or 0

    # Summary: CP completion
    cp_satisfied = db.query(func.count(ConditionPrecedent.id)).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.satisfied_at.isnot(None),
    ).scalar() or 0

    cp_total = db.query(func.count(ConditionPrecedent.id)).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
    ).scalar() or 0

    cp_completion_pct = (cp_satisfied / cp_total * 100) if cp_total > 0 else 100.0

    # Summary: Verification completion
    verified_count = db.query(func.count(Verification.id)).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
        Verification.status == "Verified",
    ).scalar() or 0

    pending_count = db.query(func.count(Verification.id)).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
        Verification.status == "Pending",
    ).scalar() or 0

    verification_total = verified_count + pending_count
    verification_completion_pct = (verified_count / verification_total * 100) if verification_total > 0 else 100.0

    # Summary: Exports generated
    exports_generated = db.query(func.count(Export.id)).filter(
        Export.case_id == case_id,
        Export.org_id == org_id,
    ).scalar() or 0

    # Summary: Last rule run
    last_rule_run = db.query(func.max(RuleRun.created_at)).filter(
        RuleRun.case_id == case_id,
        RuleRun.org_id == org_id,
    ).scalar()

    # Summary: Last OCR (get documents for case, then get max ocr_finished_at from pages)
    doc_ids = db.query(Document.id).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).subquery()
    
    last_ocr = db.query(func.max(DocumentPage.ocr_finished_at)).filter(
        DocumentPage.document_id.in_(doc_ids),
    ).scalar()

    # Build timeseries
    date_range = generate_date_range(start_date, today)
    timeseries_data = {d.isoformat(): {
        "exceptions_opened": 0,
        "exceptions_resolved": 0,
        "cps_satisfied": 0,
        "verifications_verified": 0,
        "exports_generated": 0,
        "rule_evaluations": 0,
        "ocr_pages_done": 0,
    } for d in date_range}

    # Exceptions opened per day
    exceptions_opened = db.query(
        cast(Exception_.created_at, Date).label("day"),
        func.count(Exception_.id).label("count"),
    ).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.created_at >= cutoff_date,
    ).group_by(cast(Exception_.created_at, Date)).all()

    for row in exceptions_opened:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["exceptions_opened"] = row.count

    # Exceptions resolved per day (using resolved_at)
    exceptions_resolved = db.query(
        cast(Exception_.resolved_at, Date).label("day"),
        func.count(Exception_.id).label("count"),
    ).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.resolved_at.isnot(None),
        Exception_.resolved_at >= cutoff_date,
    ).group_by(cast(Exception_.resolved_at, Date)).all()

    for row in exceptions_resolved:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["exceptions_resolved"] = row.count

    # CPs satisfied per day
    cps_satisfied = db.query(
        cast(ConditionPrecedent.satisfied_at, Date).label("day"),
        func.count(ConditionPrecedent.id).label("count"),
    ).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.satisfied_at.isnot(None),
        ConditionPrecedent.satisfied_at >= cutoff_date,
    ).group_by(cast(ConditionPrecedent.satisfied_at, Date)).all()

    for row in cps_satisfied:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["cps_satisfied"] = row.count

    # Verifications verified per day
    verifications_verified = db.query(
        cast(Verification.verified_at, Date).label("day"),
        func.count(Verification.id).label("count"),
    ).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
        Verification.verified_at.isnot(None),
        Verification.verified_at >= cutoff_date,
    ).group_by(cast(Verification.verified_at, Date)).all()

    for row in verifications_verified:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["verifications_verified"] = row.count

    # Exports per day
    exports_by_day = db.query(
        cast(Export.created_at, Date).label("day"),
        func.count(Export.id).label("count"),
    ).filter(
        Export.case_id == case_id,
        Export.org_id == org_id,
        Export.created_at >= cutoff_date,
    ).group_by(cast(Export.created_at, Date)).all()

    for row in exports_by_day:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["exports_generated"] = row.count

    # Rule evaluations per day
    rule_runs = db.query(
        cast(RuleRun.created_at, Date).label("day"),
        func.count(RuleRun.id).label("count"),
    ).filter(
        RuleRun.case_id == case_id,
        RuleRun.org_id == org_id,
        RuleRun.created_at >= cutoff_date,
    ).group_by(cast(RuleRun.created_at, Date)).all()

    for row in rule_runs:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["rule_evaluations"] = row.count

    # OCR pages done per day
    ocr_pages = db.query(
        cast(DocumentPage.ocr_finished_at, Date).label("day"),
        func.count(DocumentPage.id).label("count"),
    ).filter(
        DocumentPage.document_id.in_(doc_ids),
        DocumentPage.ocr_finished_at.isnot(None),
        DocumentPage.ocr_finished_at >= cutoff_date,
    ).group_by(cast(DocumentPage.ocr_finished_at, Date)).all()

    for row in ocr_pages:
        day_str = row.day.isoformat()
        if day_str in timeseries_data:
            timeseries_data[day_str]["ocr_pages_done"] = row.count

    # Convert to list
    timeseries = [
        CaseInsightsTimeseries(
            date=d.isoformat(),
            exceptions_opened=timeseries_data[d.isoformat()]["exceptions_opened"],
            exceptions_resolved=timeseries_data[d.isoformat()]["exceptions_resolved"],
            cps_satisfied=timeseries_data[d.isoformat()]["cps_satisfied"],
            verifications_verified=timeseries_data[d.isoformat()]["verifications_verified"],
            exports_generated=timeseries_data[d.isoformat()]["exports_generated"],
            rule_evaluations=timeseries_data[d.isoformat()]["rule_evaluations"],
            ocr_pages_done=timeseries_data[d.isoformat()]["ocr_pages_done"],
        )
        for d in date_range
    ]

    # Audit log
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="case.insights_view",
        entity_type="case",
        entity_id=case_id,
        event_metadata={"range_days": days},
    )

    return CaseInsightsResponse(
        case_id=case_id,
        range_days=days,
        summary=CaseInsightsSummary(
            open_exceptions_high=open_high,
            open_exceptions_medium=open_medium,
            open_exceptions_low=open_low,
            cp_completion_pct=round(cp_completion_pct, 1),
            verification_completion_pct=round(verification_completion_pct, 1),
            exports_generated=exports_generated,
            last_rule_run_at=last_rule_run,
            last_ocr_at=last_ocr,
        ),
        timeseries=timeseries,
    )

