import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from app.db.session import get_db
from app.core.config import settings
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
        role = payload["role"]
        
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
        if not role_mapping or role_mapping.role != role:
            raise HTTPException(status_code=401, detail="Role mapping invalid")
        
        return CurrentUser(user_id=user_id, org_id=org_id, role=role)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except KeyError:
        raise HTTPException(status_code=401, detail="Token missing required claims")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

