"""D6: Admin endpoints for deletion, retention, and cleanup."""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.case import Case
from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun
from app.models.export import Export
from app.models.user import User, UserOrgRole
from app.models.audit_log import AuditLog
from app.api.deps import get_current_user, CurrentUser, require_role, require_tenant_scope
from app.services.audit import write_audit_event
from app.services.storage import delete_object, delete_objects_by_prefix

router = APIRouter(prefix="/admin", tags=["admin"])


# Admin-only routes use Depends(require_role("Admin")) instead of require_admin().


# ============================================================
# SCHEMAS
# ============================================================

class DeleteResponse(BaseModel):
    message: str
    deleted_db_rows: int
    deleted_minio_objects: int


class RetentionCleanupResponse(BaseModel):
    message: str
    cases_deleted: int
    cutoff_date: str


class MigrationsStatusResponse(BaseModel):
    current_revision: Optional[str]
    head_revisions: list[str]


class BuildInfoResponse(BaseModel):
    app_env: str
    build_sha: Optional[str] = None
    build_time: Optional[str] = None
    code_head_revisions: Optional[list[str]] = None


# ============================================================
# DELETE CASE
# ============================================================

@router.delete("/cases/{case_id}", response_model=DeleteResponse)
async def delete_case(
    request: Request,
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """
    Delete a case and all related data (Admin only).
    Removes: exports, exceptions, cps, evidence refs, dossier fields, documents, pages.
    Also removes all MinIO objects under the case prefix. Tenant-scoped: 404 if case not in org.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    deleted_rows = 0
    
    # Delete exports
    exports = db.query(Export).filter(
        Export.case_id == case_id,
        Export.org_id == org_id,
    ).all()
    for exp in exports:
        db.delete(exp)
    deleted_rows += len(exports)
    
    # Delete exception evidence refs (must delete before exceptions)
    exc_ids = db.query(Exception_.id).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
    ).all()
    exc_ids = [e[0] for e in exc_ids]
    
    if exc_ids:
        deleted = db.query(ExceptionEvidenceRef).filter(
            ExceptionEvidenceRef.exception_id.in_(exc_ids),
            ExceptionEvidenceRef.org_id == org_id,
        ).delete(synchronize_session=False)
        deleted_rows += deleted
    
    # Delete exceptions
    deleted = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete CPs
    deleted = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete rule runs
    deleted = db.query(RuleRun).filter(
        RuleRun.case_id == case_id,
        RuleRun.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete dossier fields
    deleted = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete document pages
    doc_ids = db.query(Document.id).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).all()
    doc_ids = [d[0] for d in doc_ids]
    
    if doc_ids:
        deleted = db.query(DocumentPage).filter(
            DocumentPage.document_id.in_(doc_ids),
            DocumentPage.org_id == org_id,
        ).delete(synchronize_session=False)
        deleted_rows += deleted
    
    # Delete documents
    deleted = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete case
    db.delete(case)
    deleted_rows += 1
    
    db.commit()
    
    # Delete MinIO objects
    minio_prefix = f"org/{org_id}/cases/{case_id}/"
    deleted_minio = delete_objects_by_prefix(minio_prefix)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="case.delete",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "case_title": case.title,
            "deleted_db_rows": deleted_rows,
            "deleted_minio_objects": deleted_minio,
        },
    )
    
    return DeleteResponse(
        message=f"Case '{case.title}' deleted successfully",
        deleted_db_rows=deleted_rows,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# DELETE EXPORT
# ============================================================

@router.delete("/exports/{export_id}", response_model=DeleteResponse)
async def delete_export(
    request: Request,
    export_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Delete an export and its MinIO object (Admin only, tenant-scoped)."""
    export = db.query(Export).filter(
        Export.id == export_id,
        Export.org_id == org_id,
    ).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    minio_key = export.minio_key
    case_id = export.case_id
    filename = export.filename
    
    db.delete(export)
    db.commit()
    
    # Delete MinIO object
    try:
        delete_object(minio_key)
        deleted_minio = 1
    except Exception as e:
        deleted_minio = 0
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.delete",
        entity_type="export",
        entity_id=export_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "export_id": str(export_id),
            "case_id": str(case_id),
            "filename": filename,
        },
    )
    
    return DeleteResponse(
        message=f"Export '{filename}' deleted successfully",
        deleted_db_rows=1,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(
    request: Request,
    document_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Delete a document, its pages, and MinIO objects (Admin only, tenant-scoped)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    deleted_rows = 0
    
    # Delete pages
    deleted = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    case_id = document.case_id
    filename = document.original_filename
    
    # Delete document
    db.delete(document)
    deleted_rows += 1
    
    db.commit()
    
    # Delete MinIO objects for this document
    minio_prefix = f"org/{org_id}/cases/{case_id}/docs/{document_id}/"
    deleted_minio = delete_objects_by_prefix(minio_prefix)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.delete",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(case_id),
            "filename": filename,
            "deleted_db_rows": deleted_rows,
            "deleted_minio_objects": deleted_minio,
        },
    )
    
    return DeleteResponse(
        message=f"Document '{filename}' deleted successfully",
        deleted_db_rows=deleted_rows,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# RETENTION CLEANUP
# ============================================================

@router.post("/run-retention-cleanup", response_model=RetentionCleanupResponse)
async def run_retention_cleanup(
    request: Request,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """
    Delete cases older than RETENTION_DAYS (Admin only, tenant-scoped).
    This is a manual cleanup endpoint.
    """
    retention_days = settings.RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    old_cases = db.query(Case).filter(
        Case.org_id == org_id,
        Case.created_at < cutoff_date,
    ).all()
    
    cases_deleted = 0
    total_db_rows = 0
    total_minio_objects = 0
    
    for case in old_cases:
        case_id = case.id
        
        # Delete exports (tenant-scoped)
        exports = db.query(Export).filter(
            Export.case_id == case_id,
            Export.org_id == org_id,
        ).all()
        for exp in exports:
            db.delete(exp)
        total_db_rows += len(exports)
        
        # Delete exception evidence refs (tenant-scoped)
        exc_ids = [e[0] for e in db.query(Exception_.id).filter(
            Exception_.case_id == case_id,
            Exception_.org_id == org_id,
        ).all()]
        if exc_ids:
            total_db_rows += db.query(ExceptionEvidenceRef).filter(
                ExceptionEvidenceRef.exception_id.in_(exc_ids),
                ExceptionEvidenceRef.org_id == org_id,
            ).delete(synchronize_session=False)
        
        # Delete exceptions
        total_db_rows += db.query(Exception_).filter(
            Exception_.case_id == case_id,
            Exception_.org_id == org_id,
        ).delete(synchronize_session=False)
        
        # Delete CPs
        total_db_rows += db.query(ConditionPrecedent).filter(
            ConditionPrecedent.case_id == case_id,
            ConditionPrecedent.org_id == org_id,
        ).delete(synchronize_session=False)
        
        # Delete rule runs
        total_db_rows += db.query(RuleRun).filter(
            RuleRun.case_id == case_id,
            RuleRun.org_id == org_id,
        ).delete(synchronize_session=False)
        
        # Delete dossier fields
        total_db_rows += db.query(CaseDossierField).filter(
            CaseDossierField.case_id == case_id,
            CaseDossierField.org_id == org_id,
        ).delete(synchronize_session=False)
        
        # Delete document pages and documents (tenant-scoped)
        doc_ids = [d[0] for d in db.query(Document.id).filter(
            Document.case_id == case_id,
            Document.org_id == org_id,
        ).all()]
        if doc_ids:
            total_db_rows += db.query(DocumentPage).filter(
                DocumentPage.document_id.in_(doc_ids),
                DocumentPage.org_id == org_id,
            ).delete(synchronize_session=False)
        
        total_db_rows += db.query(Document).filter(
            Document.case_id == case_id,
            Document.org_id == org_id,
        ).delete(synchronize_session=False)
        
        # Delete case
        db.delete(case)
        total_db_rows += 1
        
        # Delete MinIO objects
        minio_prefix = f"org/{org_id}/cases/{case_id}/"
        total_minio_objects += delete_objects_by_prefix(minio_prefix)
        
        cases_deleted += 1
    
    db.commit()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="retention.run",
        entity_type="system",
        entity_id=None,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "cases_deleted": cases_deleted,
            "total_db_rows": total_db_rows,
            "total_minio_objects": total_minio_objects,
        },
    )
    
    return RetentionCleanupResponse(
        message=f"Retention cleanup completed. Deleted {cases_deleted} cases older than {retention_days} days.",
        cases_deleted=cases_deleted,
        cutoff_date=cutoff_date.isoformat(),
    )


# ============================================================
# USER MANAGEMENT (Phase 10)
# ============================================================

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    created_at: datetime


class UserCreateRequest(BaseModel):
    email: str
    full_name: str
    role: str  # Admin, Reviewer, Approver, Viewer


class UserUpdateRequest(BaseModel):
    role: str


class AuditLogResponse(BaseModel):
    id: str
    actor_user_id: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    event_metadata: dict
    created_at: datetime


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """List all users in the org (Admin only)."""
    user_roles = db.query(UserOrgRole).filter(
        UserOrgRole.org_id == org_id
    ).all()
    
    # Get user details
    user_ids = [ur.user_id for ur in user_roles]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    roles_map = {ur.user_id: ur.role for ur in user_roles}
    
    return [
        UserResponse(
            id=str(user_id),
            email=users[user_id].email,
            full_name=users[user_id].full_name,
            role=roles_map[user_id],
            created_at=users[user_id].created_at,
        )
        for user_id in user_ids
        if user_id in users
    ]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    request: Request,
    body: UserCreateRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Create a user in the org with a role (Admin only, dev mode)."""
    
    # Validate role
    valid_roles = ["Admin", "Reviewer", "Approver", "Viewer"]
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    # Check if user exists
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        # Create user
        user = User(
            email=body.email,
            full_name=body.full_name,
        )
        db.add(user)
        db.flush()
    
    existing_role = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user.id,
        UserOrgRole.org_id == org_id,
    ).first()
    
    if existing_role:
        raise HTTPException(status_code=400, detail="User already exists in this org")
    
    user_role = UserOrgRole(
        user_id=user.id,
        org_id=org_id,
        role=body.role,
    )
    db.add(user_role)
    db.commit()
    db.refresh(user)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="admin.user_create",
        entity_type="user",
        entity_id=user.id,
        event_metadata={
            "email": body.email,
            "role": body.role,
        },
    )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=body.role,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_role(
    request: Request,
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Update a user's role in the org (Admin only)."""
    valid_roles = ["Admin", "Reviewer", "Approver", "Viewer"]
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    user_role = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id,
        UserOrgRole.org_id == org_id,
    ).first()
    
    if not user_role:
        raise HTTPException(status_code=404, detail="User not found in this org")
    
    old_role = user_role.role
    user_role.role = body.role
    db.commit()
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="admin.user_update",
        entity_type="user",
        entity_id=user_id,
        event_metadata={
            "email": user.email if user else None,
            "old_role": old_role,
            "new_role": body.role,
        },
    )
    
    return UserResponse(
        id=str(user_id),
        email=user.email if user else "",
        full_name=user.full_name if user else "",
        role=body.role,
        created_at=user.created_at if user else datetime.utcnow(),
    )


@router.post("/smoke/ping")
async def smoke_ping(
    request: Request,
    event: str,
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint for smoke tests to record audit events.
    Events: smoke.run_start, smoke.run_complete, smoke.ocr_done
    """
    
    # Write audit event
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action=f"smoke.{event}",
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "smoke_event": event,
        },
    )
    
    return {"status": "ok", "event": f"smoke.{event}"}


@router.get("/migrations/status", response_model=MigrationsStatusResponse)
async def migrations_status(
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """
    Admin-only. Returns current DB revision and code head revision(s) for deployment validation.
    """
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext

    # Resolve alembic.ini: from backend/app/api/routes -> backend
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    ini_path = backend_dir / "alembic.ini"
    if not ini_path.exists():
        return MigrationsStatusResponse(current_revision=None, head_revisions=[])

    alembic_cfg = Config(str(ini_path))
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    head_revisions = [getattr(h, "revision", str(h)) for h in heads]

    # Current revision from DB (read-only)
    conn = db.connection()
    context = MigrationContext.configure(conn)
    current_revision = context.get_current_revision()

    return MigrationsStatusResponse(
        current_revision=current_revision,
        head_revisions=head_revisions or [],
    )


@router.get("/build-info", response_model=BuildInfoResponse)
async def build_info(
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
):
    """
    Admin-only. Returns app_env, optional build_sha/build_time (from env), and optional code head revisions.
    Helps ops confirm what is deployed.
    """
    import os
    from pathlib import Path

    app_env = settings.APP_ENV
    build_sha = os.environ.get("APP_BUILD_SHA") or None
    build_time = os.environ.get("APP_BUILD_TIME") or None

    code_head_revisions = None
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent
        ini_path = backend_dir / "alembic.ini"
        if ini_path.exists():
            alembic_cfg = Config(str(ini_path))
            script = ScriptDirectory.from_config(alembic_cfg)
            heads = script.get_heads()
            code_head_revisions = [getattr(h, "revision", str(h)) for h in heads] or []
    except Exception:
        pass

    return BuildInfoResponse(
        app_env=app_env,
        build_sha=build_sha,
        build_time=build_time,
        code_head_revisions=code_head_revisions,
    )


@router.get("/audit", response_model=list[AuditLogResponse])
async def list_audit_logs(
    request: Request,
    days: int = 7,
    limit: int = 200,
    action_prefix: Optional[str] = None,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """List audit logs for the org (Admin only)."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(AuditLog).filter(
        AuditLog.org_id == org_id,
        AuditLog.created_at >= cutoff,
    )
    
    if action_prefix:
        query = query.filter(AuditLog.action.like(f"{action_prefix}%"))
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        AuditLogResponse(
            id=str(log.id),
            actor_user_id=str(log.actor_user_id),
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id) if log.entity_id else None,
            event_metadata=log.event_metadata or {},
            created_at=log.created_at,
        )
        for log in logs
    ]

