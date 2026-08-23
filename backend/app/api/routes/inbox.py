from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_viewer
from app.services.inbox import InboxQueue, list_inbox

router = APIRouter(tags=["inbox"])


class InboxItem(BaseModel):
    id: str
    title: str
    status: str
    decision: str | None = None
    assigned_to_user_id: str | None = None
    assigned_to_email: str | None = None
    updated_at: datetime
    created_at: datetime
    open_high: int
    open_medium: int
    open_low: int
    open_cps: int
    open_hard_stop: int
    next_action: str
    queues: list[str]


class InboxCounts(BaseModel):
    mine: int
    blocked: int
    waiting: int
    ready: int
    aging: int
    all: int


class InboxResponse(BaseModel):
    items: list[InboxItem]
    page: int
    page_size: int
    total: int
    counts: InboxCounts


@router.get("/inbox", response_model=InboxResponse)
async def get_inbox(
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
    queue: InboxQueue = Query("all"),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> InboxResponse:
    payload = list_inbox(
        db,
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        queue=queue,
        q=q,
        page=page,
        page_size=page_size,
    )
    return InboxResponse(**payload)
