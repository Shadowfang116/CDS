import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, require_admin
from app.core.config import settings
from app.core.roles import validate_role_for_creation
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.org import Org
from app.models.user import User, UserOrgRole
from app.schemas.auth import ChangePasswordRequest, CreateUserRequest, LoginRequest, UserResponse
from app.services.audit import SYSTEM_ACTOR_ID, SYSTEM_ORG_ID, log_request_event

router = APIRouter(prefix="/auth", tags=["auth"])

DUMMY_PASSWORD_HASH = get_password_hash("bank-diligence-platform-dummy-password")
LOCKOUT_MINUTES = 15
MAX_FAILED_LOGIN_ATTEMPTS = 5
INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _verify_password_timing_safe(password: str, password_hash: str | None) -> bool:
    hashed_value = password_hash or DUMMY_PASSWORD_HASH
    is_valid = verify_password(password, hashed_value)
    return bool(password_hash) and is_valid


def _create_access_token(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str,
    *,
    must_change_password: bool,
) -> str:
    expires = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "must_change_password": must_change_password,
        "exp": expires,
    }
    return jwt.encode(
        token_data,
        settings.APP_SECRET_KEY.get_secret_value(),
        algorithm=settings.APP_ALGORITHM,
    )


def _set_access_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.APP_ENV == "production",
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _clear_access_token_cookie(response: Response) -> None:
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        samesite="lax",
        secure=settings.APP_ENV == "production",
        path="/",
        max_age=0,
    )


def _build_user_response(user: User, org: Org, role: str) -> UserResponse:
    return UserResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=org.id,
        org_name=org.name,
        role=role,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
    )


def _load_user_context_by_email(
    db: Session,
    email: str,
) -> tuple[User, UserOrgRole, Org] | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    role_mapping = (
        db.query(UserOrgRole)
        .filter(UserOrgRole.user_id == user.id)
        .order_by(UserOrgRole.created_at.asc())
        .first()
    )
    if not role_mapping:
        return None

    org = db.query(Org).filter(Org.id == role_mapping.org_id).first()
    if not org:
        return None

    return user, role_mapping, org


def _log_login_failure(
    *,
    db: Session,
    request: Request,
    email: str,
    reason: str,
    user: User | None = None,
    org_id: uuid.UUID | None = None,
    before_snapshot: dict | None = None,
    after_snapshot: dict | None = None,
) -> None:
    log_request_event(
        db,
        request=request,
        action="auth.login_failure",
        org_id=org_id or SYSTEM_ORG_ID,
        actor_id=user.id if user else SYSTEM_ACTOR_ID,
        entity_type="user" if user else "auth",
        entity_id=user.id if user else email,
        before_json=before_snapshot,
        after_json={
            "email": email,
            "reason": reason,
            **(after_snapshot or {}),
        },
    )


@router.post("/login", response_model=UserResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    context = _load_user_context_by_email(db, body.email)
    if not context:
        verify_password(body.password, DUMMY_PASSWORD_HASH)
        _log_login_failure(
            db=db,
            request=request,
            email=body.email,
            reason="auth.login_failure",
        )
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS_MESSAGE)

    user, role_mapping, org = context
    now = _utcnow()

    if not user.is_active:
        _log_login_failure(
            db=db,
            request=request,
            email=body.email,
            reason="auth.login_failure",
            user=user,
            org_id=org.id,
        )
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS_MESSAGE)

    locked_until = _coerce_utc(user.locked_until)
    if locked_until and locked_until > now:
        _log_login_failure(
            db=db,
            request=request,
            email=body.email,
            reason="auth.login_failure",
            user=user,
            org_id=org.id,
            before_snapshot={"locked_until": locked_until.isoformat()},
            after_snapshot={"locked_until": locked_until.isoformat()},
        )
        raise HTTPException(
            status_code=423,
            detail={
                "message": INVALID_CREDENTIALS_MESSAGE,
                "locked_until": locked_until.isoformat(),
            },
        )

    if not _verify_password_timing_safe(body.password, user.password_hash):
        before_snapshot = {
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        }
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        db.refresh(user)

        _log_login_failure(
            db=db,
            request=request,
            email=body.email,
            reason="auth.login_failure",
            user=user,
            org_id=org.id,
            before_snapshot=before_snapshot,
            after_snapshot={
                "failed_login_attempts": user.failed_login_attempts,
                "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            },
        )
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS_MESSAGE)

    before_snapshot = {
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    db.refresh(user)

    token = _create_access_token(
        user.id,
        org.id,
        role_mapping.role,
        must_change_password=user.must_change_password,
    )
    _set_access_token_cookie(response, token)

    log_request_event(
        db,
        request=request,
        action="auth.login_success",
        org_id=org.id,
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
        before_json=before_snapshot,
        after_json={
            "email": user.email,
            "role": role_mapping.role,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
    )

    return _build_user_response(user, org, role_mapping.role)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.APP_SECRET_KEY.get_secret_value(),
                algorithms=[settings.APP_ALGORITHM],
            )
            user_id = uuid.UUID(payload["user_id"])
            org_id = uuid.UUID(payload["org_id"])
            log_request_event(
                db,
                request=request,
                action="auth.logout",
                org_id=org_id,
                actor_id=user_id,
                entity_type="user",
                entity_id=user_id,
                after_json={"status": "logged_out"},
            )
        except Exception:
            pass

    _clear_access_token_cookie(response)
    return {"message": "Logged out"}


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    request: Request,
    response: Response,
    body: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.user_id).first()
    org = db.query(Org).filter(Org.id == current_user.org_id).first()
    if not user or not org:
        raise HTTPException(status_code=404, detail="User or org not found")

    if user.password_hash is None or not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    before_snapshot = {
        "must_change_password": user.must_change_password,
    }
    user.password_hash = get_password_hash(body.new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)

    token = _create_access_token(
        user.id,
        org.id,
        current_user.role,
        must_change_password=user.must_change_password,
    )
    _set_access_token_cookie(response, token)

    log_request_event(
        db,
        request=request,
        action="auth.change_password",
        org_id=org.id,
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
        before_json=before_snapshot,
        after_json={"must_change_password": user.must_change_password},
    )

    return _build_user_response(user, org, current_user.role)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_auth_user(
    request: Request,
    body: CreateUserRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    org = db.query(Org).filter(Org.id == current_user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    canonical_role = validate_role_for_creation(body.role)
    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=get_password_hash(body.temporary_password),
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    db.add(
        UserOrgRole(
            user_id=user.id,
            org_id=current_user.org_id,
            role=canonical_role,
        )
    )
    db.commit()
    db.refresh(user)

    log_request_event(
        db,
        request=request,
        action="auth.user_created",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="user",
        entity_id=user.id,
        after_json={
            "email": body.email,
            "role": canonical_role,
            "must_change_password": user.must_change_password,
            "is_active": user.is_active,
        },
    )

    return _build_user_response(user, org, canonical_role)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.user_id).first()
    org = db.query(Org).filter(Org.id == current_user.org_id).first()
    if not user or not org:
        raise HTTPException(status_code=404, detail="User or org not found")
    return _build_user_response(user, org, current_user.role)
