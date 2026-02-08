"""Health check endpoints."""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import SessionLocal
from app.core.config import settings
from app.services.storage import get_s3_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok"}


@router.get("/health/deep")
async def deep_health_check():
    """
    Deep health check: verifies DB, Redis, MinIO, and worker connectivity.
    Returns detailed status for each component.
    """
    checks = {
        "status": "ok",
        "checks": {},
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        checks["status"] = "degraded"
        checks["checks"]["database"] = {"status": "error", "error": str(e)[:200]}
    
    # Check Redis (best-effort via env vars)
    try:
        import os
        import redis
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            socket_connect_timeout=2,
        )
        r.ping()
        checks["checks"]["redis"] = {"status": "ok"}
    except Exception as e:
        checks["status"] = "degraded"
        checks["checks"]["redis"] = {"status": "error", "error": str(e)[:200]}
    
    # Check MinIO bucket
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
        checks["checks"]["minio"] = {"status": "ok", "bucket": settings.MINIO_BUCKET}
    except Exception as e:
        checks["status"] = "degraded"
        checks["checks"]["minio"] = {"status": "error", "error": str(e)[:200]}
    
    # Check worker (best-effort via Celery inspect)
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active:
            checks["checks"]["worker"] = {"status": "ok", "active_workers": len(active)}
        else:
            checks["checks"]["worker"] = {"status": "warning", "message": "No active workers found"}
    except Exception as e:
        checks["checks"]["worker"] = {"status": "warning", "error": str(e)[:200]}
    
    if checks["status"] == "degraded":
        raise HTTPException(status_code=503, detail=checks)
    
    return checks

