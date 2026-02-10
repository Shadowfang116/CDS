from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.models import Org, User, UserOrgRole, Case, AuditLog, Document, DocumentPage, CaseDossierField, Exception_, ConditionPrecedent, ExceptionEvidenceRef, CPEvidenceRef, RuleRun, Export, Verification, VerificationEvidenceRef  # Import to register models
from app.services.storage import ensure_bucket_exists
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware, UploadSizeLimitMiddleware
from app.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Bank Diligence API", version="0.1.0")

# ============================================================
# MIDDLEWARE (first added = outermost = runs first)
# ============================================================

# Request context: X-Request-ID, latency, structured request log
app.add_middleware(RequestContextMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Upload size limit
app.add_middleware(UploadSizeLimitMiddleware)

# CORS - configure origins from settings
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """Verify database connection and initialize storage on startup."""
    # Test database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")
    
    # Initialize MinIO bucket
    try:
        ensure_bucket_exists()
        logger.info("Storage bucket initialized")
    except Exception as e:
        logger.warning(f"Storage bucket initialization failed: {e}")

