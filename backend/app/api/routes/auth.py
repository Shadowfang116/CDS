import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import jwt
from app.db.session import get_db
from app.core.config import settings
from app.core.roles import validate_role_for_creation
from app.models.org import Org
from app.models.user import User, UserOrgRole
from app.schemas.auth import DevLoginRequest, TokenResponse, UserResponse
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    request: Request,
    login_data: DevLoginRequest,
    db: Session = Depends(get_db),
):
    """
    DEV-ONLY: Quick login for development.
    Creates/updates org, user, and role mapping, then returns JWT.
    """
    # Normalize role upfront (raises 400 if invalid)
    canonical_role = validate_role_for_creation(login_data.role)
    
    # Upsert org
    org = db.query(Org).filter(Org.name == login_data.org_name).first()
    if not org:
        org = Org(name=login_data.org_name)
        db.add(org)
        db.commit()
        db.refresh(org)
    
    # Upsert user
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        user = User(email=login_data.email, full_name=login_data.email.split("@")[0])
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Upsert role mapping (always use canonical role)
    role_mapping = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user.id,
        UserOrgRole.org_id == org.id,
    ).first()
    if not role_mapping:
        role_mapping = UserOrgRole(
            user_id=user.id,
            org_id=org.id,
            role=canonical_role,
        )
        db.add(role_mapping)
        db.commit()
    else:
        role_mapping.role = canonical_role
        db.commit()
    
    # Generate JWT (use canonical role)
    expires = datetime.utcnow() + timedelta(hours=settings.APP_ACCESS_TOKEN_EXPIRE_HOURS)
    token_data = {
        "user_id": str(user.id),
        "org_id": str(org.id),
        "role": canonical_role,
        "exp": expires,
    }
    token = jwt.encode(token_data, settings.APP_SECRET_KEY.get_secret_value(), algorithm=settings.APP_ALGORITHM)
    
    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=org.id,
        actor_user_id=user.id,
        action="auth.dev_login",
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "role": canonical_role,
        },
        request_id=request_id,
    )
    
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user info."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    org = db.query(Org).filter(Org.id == current_user.org_id).first()
    
    if not user or not org:
        raise HTTPException(status_code=404, detail="User or org not found")
    
    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="auth.me",
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
        request_id=request_id,
    )
    
    return UserResponse(
        user_id=user.id,
        email=user.email,
        org_id=org.id,
        org_name=org.name,
        role=current_user.role,
    )

