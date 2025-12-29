from fastapi import APIRouter
from app.api.routes import auth, cases, documents, ocr, dossier, rules, exports, admin, verification

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(ocr.router)
api_router.include_router(dossier.router)
api_router.include_router(rules.router)
api_router.include_router(exports.router)
api_router.include_router(admin.router)
api_router.include_router(verification.router)

