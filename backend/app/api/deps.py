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
    """Canonical current-user context: always scoped to one org and one role."""

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
        payload = jwt.decode(token, settings.APP_SECRET_KEY.get_secret_value(), algorithms=[settings.APP_ALGORITHM])
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


# ---------------------------------------------------------------------------
# Canonical RBAC + tenant dependencies (deny-by-default)
# ---------------------------------------------------------------------------


def require_authenticated_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Ensure the request has a valid authenticated user. Use this or a role/tenant dep."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def require_role(*allowed_roles: str):
    """
    Dependency factory: allow only the given roles. Deny by default.
    Usage: Depends(require_role("Admin", "Approver"))
    """
    if not allowed_roles:
        raise RuntimeError("require_role() must be called with at least one role")

    allowed = set()
    for r in allowed_roles:
        if r is None:
            continue
        try:
            allowed.add(normalize_role(str(r)))
        except Exception as e:
            raise RuntimeError(f"Invalid role passed to require_role(): {r!r}") from e

    def _require_role(
        current_user: CurrentUser = Depends(require_authenticated_user),
    ) -> CurrentUser:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return current_user

    return _require_role


def require_tenant_scope(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_authenticated_user),
) -> uuid.UUID:
    """
    Returns org_id that MUST be used for all queries in this request.
    Client must NEVER supply org_id explicitly; it is taken from the token.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing",
        )
    return current_user.org_id


# Backward compatibility: require_roles is an alias for require_role
def require_roles(*roles):
    """Alias for require_role. Prefer require_role for new code."""
    return require_role(*roles)