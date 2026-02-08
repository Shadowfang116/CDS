import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from app.db.session import get_db
from app.core.config import settings
from app.core.roles import normalize_role
from app.models.user import User, UserOrgRole
from app.models.org import Org

security = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: uuid.UUID, org_id: uuid.UUID, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Extract and validate JWT token, return current user context."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.APP_ALGORITHM])
        user_id = uuid.UUID(payload["user_id"])
        org_id = uuid.UUID(payload["org_id"])
        token_role = payload.get("role")
        
        # Normalize role from token (handles case variants, aliases)
        # This raises HTTPException 401 if role is missing/invalid
        canonical_role = normalize_role(token_role)
        
        # Verify user and org still exist
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        org = db.query(Org).filter(Org.id == org_id).first()
        if not org:
            raise HTTPException(status_code=401, detail="Organization not found")
        
        # Verify role mapping still exists
        role_mapping = db.query(UserOrgRole).filter(
            UserOrgRole.user_id == user_id,
            UserOrgRole.org_id == org_id,
        ).first()
        if not role_mapping:
            raise HTTPException(status_code=401, detail="Role mapping not found")
        
        # Normalize DB role and compare canonical forms
        db_canonical_role = normalize_role(role_mapping.role)
        if db_canonical_role != canonical_role:
            raise HTTPException(status_code=401, detail="Role mapping mismatch")
        
        # Return canonical role for consistent RBAC checks
        return CurrentUser(user_id=user_id, org_id=org_id, role=canonical_role)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except KeyError:
        raise HTTPException(status_code=401, detail="Token missing required claims")
    except HTTPException:
        # Re-raise HTTPExceptions as-is (including those from normalize_role)
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def _flatten_roles(args):
    out = []
    for a in args:
        if a is None:
            continue
        if isinstance(a, (list, tuple, set)):
            out.extend(list(a))
        else:
            out.append(a)
    return out


def require_roles(*roles):
    allowed_raw = _flatten_roles(roles)
    if not allowed_raw:
        raise RuntimeError("require_roles() called with no roles")

    allowed = set()
    for r in allowed_raw:
        try:
            allowed.add(normalize_role(str(r)))
        except Exception as e:
            raise RuntimeError(f"Invalid role passed to require_roles(): {r!r}") from e

    def _dep(user: "CurrentUser" = Depends(get_current_user)) -> "CurrentUser":
        try:
            user_role = normalize_role(str(user.role))
        except Exception:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        if user_role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return user

    return _dep