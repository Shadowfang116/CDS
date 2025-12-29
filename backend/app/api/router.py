from fastapi import APIRouter
from app.api.routes import auth, cases, documents

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)

