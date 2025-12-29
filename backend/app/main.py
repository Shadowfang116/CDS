from fastapi import FastAPI
from sqlalchemy import text
from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.models import Org, User, UserOrgRole, Case, AuditLog  # Import to register models


app = FastAPI(title="Bank Diligence API", version="0.1.0")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """Verify database connection on startup."""
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

