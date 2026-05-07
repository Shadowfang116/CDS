import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import CurrentUser, require_viewer
from app.core.config import settings
from app.db.session import get_db
from app.models.case import Case
from app.services.download_tokens import decode_download_token
from app.services.storage import get_s3_client

router = APIRouter(tags=["downloads"])


@router.get("/downloads/object")
async def download_object(
    token: str = Query(...),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    payload = decode_download_token(token)
    if payload.get("user_id") != str(current_user.user_id) or payload.get("org_id") != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download link is not valid for this user",
        )

    object_key = str(payload.get("object_key") or "")
    expected_prefix = f"org/{current_user.org_id}/"
    if not object_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download link scope mismatch",
        )

    raw_case_id = payload.get("case_id")
    if raw_case_id:
        try:
            case_id = uuid.UUID(str(raw_case_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid download link",
            ) from exc
        case = (
            db.query(Case)
            .filter(Case.id == case_id, Case.org_id == current_user.org_id)
            .first()
        )
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=object_key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey"}:
            raise HTTPException(status_code=404, detail="File not found") from exc
        raise HTTPException(status_code=502, detail="File retrieval failed") from exc

    filename = str(payload.get("filename") or object_key.rsplit("/", 1)[-1])
    content_type = str(
        payload.get("content_type") or response.get("ContentType") or "application/octet-stream"
    )
    disposition = "inline" if payload.get("disposition") == "inline" else "attachment"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
    }
    content_length = response.get("ContentLength")
    if content_length:
        headers["Content-Length"] = str(content_length)

    body = response["Body"]
    return StreamingResponse(
        body.iter_chunks(),
        media_type=content_type,
        headers=headers,
        background=BackgroundTask(body.close),
    )
