"""Public configuration endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["config"])


class PublicConfigResponse(BaseModel):
    registry_verify_url: str
    estamp_verify_url: str


@router.get("/public", response_model=PublicConfigResponse)
async def get_public_config():
    """Get public configuration (URLs for verification portals)."""
    return PublicConfigResponse(
        registry_verify_url=settings.REGISTRY_VERIFY_URL,
        estamp_verify_url=settings.ESTAMP_VERIFY_URL,
    )

