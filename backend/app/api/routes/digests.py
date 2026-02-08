"""Digest schedules and runs API routes."""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.digest import DigestSchedule, DigestRun
from app.schemas.dashboard import (
    DigestScheduleCreate,
    DigestScheduleUpdate,
    DigestScheduleResponse,
    DigestRunResponse,
    DigestRunNowResponse,
    DigestFiltersConfig,
)

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("/schedules", response_model=List[DigestScheduleResponse])
async def list_digest_schedules(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all digest schedules for the current org."""
    schedules = db.query(DigestSchedule).filter(
        DigestSchedule.org_id == current_user.org_id
    ).order_by(DigestSchedule.name.asc()).all()
    
    return [
        DigestScheduleResponse(
            id=s.id,
            name=s.name,
            cadence=s.cadence,
            hour_local=s.hour_local,
            weekday=s.weekday,
            is_enabled=s.is_enabled,
            filters_json=DigestFiltersConfig(**(s.filters_json or {})),
            created_by_user_id=s.created_by_user_id,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in schedules
    ]


@router.post("/schedules", response_model=DigestScheduleResponse, status_code=201)
async def create_digest_schedule(
    request: Request,
    payload: DigestScheduleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new digest schedule. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can create digest schedules")
    
    # Validate
    if len(payload.name) < 3 or len(payload.name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 3-100 characters")
    
    if payload.cadence not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Cadence must be 'daily' or 'weekly'")
    
    if payload.hour_local < 0 or payload.hour_local > 23:
        raise HTTPException(status_code=400, detail="Hour must be 0-23")
    
    if payload.cadence == "weekly" and (payload.weekday is None or payload.weekday < 0 or payload.weekday > 6):
        raise HTTPException(status_code=400, detail="Weekday must be 0-6 for weekly cadence")
    
    schedule = DigestSchedule(
        org_id=current_user.org_id,
        name=payload.name,
        cadence=payload.cadence,
        hour_local=payload.hour_local,
        weekday=payload.weekday if payload.cadence == "weekly" else None,
        is_enabled=payload.is_enabled,
        filters_json=payload.filters_json.model_dump(),
        created_by_user_id=current_user.user_id,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="digest.schedule_create",
        entity_type="digest_schedule",
        entity_id=schedule.id,
        event_metadata={
            "schedule_id": str(schedule.id),
            "name": schedule.name,
            "cadence": schedule.cadence,
        },
    )
    
    return DigestScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        cadence=schedule.cadence,
        hour_local=schedule.hour_local,
        weekday=schedule.weekday,
        is_enabled=schedule.is_enabled,
        filters_json=DigestFiltersConfig(**(schedule.filters_json or {})),
        created_by_user_id=schedule.created_by_user_id,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@router.patch("/schedules/{schedule_id}", response_model=DigestScheduleResponse)
async def update_digest_schedule(
    request: Request,
    schedule_id: UUID,
    payload: DigestScheduleUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a digest schedule. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can update digest schedules")
    
    schedule = db.query(DigestSchedule).filter(
        DigestSchedule.id == schedule_id,
        DigestSchedule.org_id == current_user.org_id,
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if payload.name is not None:
        if len(payload.name) < 3 or len(payload.name) > 100:
            raise HTTPException(status_code=400, detail="Name must be 3-100 characters")
        schedule.name = payload.name
    
    if payload.cadence is not None:
        if payload.cadence not in ["daily", "weekly"]:
            raise HTTPException(status_code=400, detail="Cadence must be 'daily' or 'weekly'")
        schedule.cadence = payload.cadence
    
    if payload.hour_local is not None:
        if payload.hour_local < 0 or payload.hour_local > 23:
            raise HTTPException(status_code=400, detail="Hour must be 0-23")
        schedule.hour_local = payload.hour_local
    
    if payload.weekday is not None:
        if payload.weekday < 0 or payload.weekday > 6:
            raise HTTPException(status_code=400, detail="Weekday must be 0-6")
        schedule.weekday = payload.weekday
    
    if payload.is_enabled is not None:
        schedule.is_enabled = payload.is_enabled
    
    if payload.filters_json is not None:
        schedule.filters_json = payload.filters_json.model_dump()
    
    schedule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(schedule)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="digest.schedule_update",
        entity_type="digest_schedule",
        entity_id=schedule.id,
        event_metadata={
            "schedule_id": str(schedule.id),
            "name": schedule.name,
            "is_enabled": schedule.is_enabled,
        },
    )
    
    return DigestScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        cadence=schedule.cadence,
        hour_local=schedule.hour_local,
        weekday=schedule.weekday,
        is_enabled=schedule.is_enabled,
        filters_json=DigestFiltersConfig(**(schedule.filters_json or {})),
        created_by_user_id=schedule.created_by_user_id,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_digest_schedule(
    request: Request,
    schedule_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a digest schedule. Admin only."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete digest schedules")
    
    schedule = db.query(DigestSchedule).filter(
        DigestSchedule.id == schedule_id,
        DigestSchedule.org_id == current_user.org_id,
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule_name = schedule.name
    
    # Delete associated runs first
    db.query(DigestRun).filter(DigestRun.schedule_id == schedule_id).delete()
    db.delete(schedule)
    db.commit()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="digest.schedule_delete",
        entity_type="digest_schedule",
        entity_id=schedule_id,
        event_metadata={
            "schedule_id": str(schedule_id),
            "name": schedule_name,
        },
    )
    
    return None


@router.post("/schedules/{schedule_id}/run-now", response_model=DigestRunNowResponse)
async def run_digest_now(
    request: Request,
    schedule_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger an immediate digest run. Admin or Approver can run."""
    if current_user.role not in ["Admin", "Approver"]:
        raise HTTPException(status_code=403, detail="Only Admin or Approver can trigger digest runs")
    
    schedule = db.query(DigestSchedule).filter(
        DigestSchedule.id == schedule_id,
        DigestSchedule.org_id == current_user.org_id,
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Create a pending run
    run = DigestRun(
        org_id=current_user.org_id,
        schedule_id=schedule.id,
        run_at=datetime.utcnow(),
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="digest.run_now",
        entity_type="digest_run",
        entity_id=run.id,
        event_metadata={
            "run_id": str(run.id),
            "schedule_id": str(schedule.id),
            "schedule_name": schedule.name,
        },
    )
    
    # Trigger Celery task (import here to avoid circular imports)
    try:
        from app.workers.tasks.digest_tasks import generate_digest_pdf
        generate_digest_pdf.delay(str(run.id), str(current_user.user_id))
    except Exception as e:
        # If Celery not available, run synchronously (MVP fallback)
        from app.services.digest_generator import generate_digest_for_run
        try:
            generate_digest_for_run(db, run.id, current_user.user_id)
            run.status = "success"
        except Exception as gen_error:
            run.status = "failed"
            run.error_message = str(gen_error)
        db.commit()
    
    return DigestRunNowResponse(
        run_id=run.id,
        status=run.status,
        message=f"Digest run triggered for '{schedule.name}'",
    )


@router.get("/runs", response_model=List[DigestRunResponse])
async def list_digest_runs(
    request: Request,
    limit: int = Query(default=50, ge=10, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent digest runs for the current org."""
    runs = db.query(DigestRun).filter(
        DigestRun.org_id == current_user.org_id
    ).order_by(DigestRun.created_at.desc()).limit(limit).all()
    
    return [
        DigestRunResponse(
            id=r.id,
            schedule_id=r.schedule_id,
            run_at=r.run_at,
            status=r.status,
            output_export_id=r.output_export_id,
            error_message=r.error_message,
            created_at=r.created_at,
        )
        for r in runs
    ]

