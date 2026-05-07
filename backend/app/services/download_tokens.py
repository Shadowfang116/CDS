import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

DOWNLOAD_TOKEN_SCOPE = "download-object"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_download_url(
    *,
    object_key: str,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    case_id: uuid.UUID | None,
    filename: str,
    content_type: str,
    expires_seconds: int,
    disposition: str = "attachment",
) -> str:
    token = jwt.encode(
        {
            "scope": DOWNLOAD_TOKEN_SCOPE,
            "object_key": object_key,
            "org_id": str(org_id),
            "user_id": str(user_id),
            "case_id": str(case_id) if case_id else None,
            "filename": filename,
            "content_type": content_type,
            "disposition": disposition,
            "exp": _utcnow() + timedelta(seconds=expires_seconds),
        },
        settings.APP_SECRET_KEY.get_secret_value(),
        algorithm=settings.APP_ALGORITHM,
    )
    return f"/api/v1/downloads/object?token={token}"


def decode_download_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.APP_SECRET_KEY.get_secret_value(),
            algorithms=[settings.APP_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Download link expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download link",
        ) from exc

    if payload.get("scope") != DOWNLOAD_TOKEN_SCOPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download link",
        )

    return payload
