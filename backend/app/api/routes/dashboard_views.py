"""Saved dashboard views API routes with sharing support."""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.saved_view import SavedView
from app.schemas.dashboard import SavedViewCreate, SavedViewUpdate, SavedViewResponse

router = APIRouter(prefix="/dashboard/views", tags=["dashboard-views"])


def can_view_saved_view(view: SavedView, current_user: CurrentUser) -> bool:
    """Check if current user can view a saved view."""
    # User can always see their own private views
    if view.created_by_user_id == current_user.user_id:
        return True
    
    # Check if org-shared and user's role is allowed
    if view.visibility == "org":
        # Empty shared_with_roles means all roles
        if not view.shared_with_roles:
            return True
        if current_user.role in view.shared_with_roles:
            return True
    
    return False


def can_edit_saved_view(view: SavedView, current_user: CurrentUser) -> bool:
    """Check if current user can edit a saved view."""
    # Admin can edit any view in their org
    if current_user.role == "Admin":
        return True
    
    # Others can only edit their own private views
    if view.created_by_user_id == current_user.user_id and view.visibility == "private":
        return True
    
    return False


@router.get("", response_model=List[SavedViewResponse])
async def list_saved_views(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List saved views for the current org.
    Returns org-shared views visible to user's role + user's private views.
    Sorted: org-shared first (default first), then private (default first).
    """
    # Get all views for this org
    all_views = db.query(SavedView).filter(
        SavedView.org_id == current_user.org_id
    ).all()
    
    # Filter to views the user can see
    visible_views = [v for v in all_views if can_view_saved_view(v, current_user)]
    
    # Sort: org-shared first, then private; within each group, default first then name
    def sort_key(v):
        visibility_order = 0 if v.visibility == "org" else 1
        default_order = 0 if v.is_default else 1
        return (visibility_order, default_order, v.name.lower())
    
    visible_views.sort(key=sort_key)
    
    return [
        SavedViewResponse(
            id=v.id,
            name=v.name,
            is_default=v.is_default,
            config_json=v.config_json,
            visibility=v.visibility,
            shared_with_roles=v.shared_with_roles or [],
            created_by_user_id=v.created_by_user_id,
            created_at=v.created_at,
            updated_at=v.updated_at,
            last_used_at=v.last_used_at,
        )
        for v in visible_views
    ]


@router.post("", response_model=SavedViewResponse, status_code=201)
async def create_saved_view(
    request: Request,
    payload: SavedViewCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new saved view. Only Admin can create org-shared views."""
    # Validate name length
    if len(payload.name) < 3 or len(payload.name) > 60:
        raise HTTPException(status_code=400, detail="View name must be 3-60 characters")
    
    # Only Admin can create org-shared views
    if payload.visibility == "org" and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can create org-shared views")
    
    # Check for duplicate name
    existing = db.query(SavedView).filter(
        SavedView.org_id == current_user.org_id,
        SavedView.name == payload.name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="View with this name already exists")
    
    # If setting as default, unset other defaults
    if payload.is_default:
        db.query(SavedView).filter(
            SavedView.org_id == current_user.org_id,
            SavedView.is_default == True,
        ).update({"is_default": False})
    
    view = SavedView(
        org_id=current_user.org_id,
        name=payload.name,
        is_default=payload.is_default,
        config_json=payload.config_json.model_dump(),
        visibility=payload.visibility,
        shared_with_roles=payload.shared_with_roles,
        shared_with_user_ids=[],
        created_by_user_id=current_user.user_id,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dashboard.view_saved",
        entity_type="saved_view",
        entity_id=view.id,
        event_metadata={
            "view_id": str(view.id),
            "name": view.name,
            "is_default": view.is_default,
            "visibility": view.visibility,
            "shared_with_roles": view.shared_with_roles,
        },
    )
    
    return SavedViewResponse(
        id=view.id,
        name=view.name,
        is_default=view.is_default,
        config_json=view.config_json,
        visibility=view.visibility,
        shared_with_roles=view.shared_with_roles or [],
        created_by_user_id=view.created_by_user_id,
        created_at=view.created_at,
        updated_at=view.updated_at,
        last_used_at=view.last_used_at,
    )


@router.patch("/{view_id}", response_model=SavedViewResponse)
async def update_saved_view(
    request: Request,
    view_id: UUID,
    payload: SavedViewUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a saved view. Admin can update any; others only their own private views."""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.org_id == current_user.org_id,
    ).first()
    
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # Check edit permissions
    if not can_edit_saved_view(view, current_user):
        raise HTTPException(status_code=403, detail="Cannot update this view")
    
    # Only Admin can change visibility/sharing
    if payload.visibility is not None or payload.shared_with_roles is not None:
        if current_user.role != "Admin":
            raise HTTPException(status_code=403, detail="Only Admin can change sharing settings")
    
    old_visibility = view.visibility
    
    # Update fields
    if payload.name is not None:
        if len(payload.name) < 3 or len(payload.name) > 60:
            raise HTTPException(status_code=400, detail="View name must be 3-60 characters")
        # Check for duplicate name
        existing = db.query(SavedView).filter(
            SavedView.org_id == current_user.org_id,
            SavedView.name == payload.name,
            SavedView.id != view_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="View with this name already exists")
        view.name = payload.name
    
    if payload.config_json is not None:
        view.config_json = payload.config_json.model_dump()
    
    if payload.is_default is not None:
        if payload.is_default:
            # Unset other defaults
            db.query(SavedView).filter(
                SavedView.org_id == current_user.org_id,
                SavedView.is_default == True,
                SavedView.id != view_id,
            ).update({"is_default": False})
        view.is_default = payload.is_default
    
    if payload.visibility is not None:
        view.visibility = payload.visibility
    
    if payload.shared_with_roles is not None:
        view.shared_with_roles = payload.shared_with_roles
    
    db.commit()
    db.refresh(view)
    
    # Determine audit action based on visibility change
    if old_visibility != view.visibility:
        if view.visibility == "org":
            action = "dashboard.view_shared"
        else:
            action = "dashboard.view_unshared"
    else:
        action = "dashboard.view_updated"
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action=action,
        entity_type="saved_view",
        entity_id=view.id,
        event_metadata={
            "view_id": str(view.id),
            "name": view.name,
            "is_default": view.is_default,
            "visibility": view.visibility,
            "shared_with_roles": view.shared_with_roles,
        },
    )
    
    return SavedViewResponse(
        id=view.id,
        name=view.name,
        is_default=view.is_default,
        config_json=view.config_json,
        visibility=view.visibility,
        shared_with_roles=view.shared_with_roles or [],
        created_by_user_id=view.created_by_user_id,
        created_at=view.created_at,
        updated_at=view.updated_at,
        last_used_at=view.last_used_at,
    )


@router.delete("/{view_id}", status_code=204)
async def delete_saved_view(
    request: Request,
    view_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved view. Admin can delete any; others only their own private views."""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.org_id == current_user.org_id,
    ).first()
    
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # Check edit permissions
    if not can_edit_saved_view(view, current_user):
        raise HTTPException(status_code=403, detail="Cannot delete this view")
    
    view_name = view.name
    db.delete(view)
    db.commit()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dashboard.view_deleted",
        entity_type="saved_view",
        entity_id=view_id,
        event_metadata={
            "view_id": str(view_id),
            "name": view_name,
        },
    )
    
    return None


@router.post("/{view_id}/use", status_code=200)
async def record_view_usage(
    request: Request,
    view_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record that a view was used (for analytics). Updates last_used_at."""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.org_id == current_user.org_id,
    ).first()
    
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # Check if user can view this
    if not can_view_saved_view(view, current_user):
        raise HTTPException(status_code=403, detail="Cannot access this view")
    
    # Update last_used_at
    view.last_used_at = datetime.utcnow()
    db.commit()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dashboard.view_used",
        entity_type="saved_view",
        entity_id=view_id,
        event_metadata={
            "view_id": str(view_id),
            "name": view.name,
        },
    )
    
    return {"status": "recorded", "view_id": str(view_id)}
