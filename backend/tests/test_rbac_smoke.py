import uuid
import os
import sys
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import types

# Ensure the backend/ directory (containing `app`) is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Provide a lightweight stub for PyJWT to satisfy imports during tests
if 'jwt' not in sys.modules:
    jwt_stub = types.SimpleNamespace(
        encode=lambda *a, **k: "test-token",
        decode=lambda *a, **k: {},
        InvalidTokenError=Exception,
    )
    sys.modules['jwt'] = jwt_stub

# Stub email_validator required by Pydantic EmailStr
if 'email_validator' not in sys.modules:
    def _validate_email(addr, *args, **kwargs):
        return types.SimpleNamespace(email=addr)
    email_validator_stub = types.SimpleNamespace(validate_email=_validate_email)
    sys.modules['email_validator'] = email_validator_stub

# Stub boto3 and botocore to avoid optional infra deps during import
if 'boto3' not in sys.modules:
    def _dummy_client(*args, **kwargs):
        class _Dummy:
            def __getattr__(self, name):
                def _fn(*a, **k):
                    return {}
                return _fn
        return _Dummy()
    sys.modules['boto3'] = types.SimpleNamespace(client=_dummy_client)

if 'botocore.client' not in sys.modules:
    client_mod = types.ModuleType('botocore.client')
    class _Config:
        def __init__(self, *a, **k):
            pass
    client_mod.Config = _Config
    sys.modules['botocore.client'] = client_mod

if 'botocore.exceptions' not in sys.modules:
    exc_mod = types.ModuleType('botocore.exceptions')
    class _ClientError(Exception):
        def __init__(self, response=None, operation_name=None):
            self.response = response or {}
    exc_mod.ClientError = _ClientError
    sys.modules['botocore.exceptions'] = exc_mod

"""Provide a lightweight stub for the DB session module to avoid engine setup.
Note: do not stub 'app.db' (real package on disk). Only override the submodule entry.
"""
if 'app.db.session' not in sys.modules:
    session_stub = types.ModuleType('app.db.session')

    def _get_db_real_stub():
        class _Dummy:
            pass
        yield _Dummy()

    session_stub.get_db = _get_db_real_stub
    sys.modules['app.db.session'] = session_stub

from app.api.deps import CurrentUser, require_role


def _build_client_with_role(role: str) -> TestClient:
    # Override the inner dep before building route closures
    from app.api import deps as deps_module
    deps_module.require_authenticated_user = _override_role(role)

    app = FastAPI()

    @app.post("/cases/{case_id}/documents")
    def _upload(case_id: str, user: CurrentUser = Depends(require_role("Reviewer", "Approver", "Admin"))):
        return {"ok": True}

    @app.post("/exceptions/{exception_id}/evidence")
    def _attach_exc(exception_id: str, user: CurrentUser = Depends(require_role("Reviewer", "Approver", "Admin"))):
        return {"ok": True}

    @app.patch("/exceptions/{exception_id}/evidence/{evidence_id}/closing")
    def _mark_closing(exception_id: str, evidence_id: str, user: CurrentUser = Depends(require_role("Reviewer", "Approver", "Admin"))):
        return {"ok": True}

    @app.post("/cases/{case_id}/exports/bank-pack")
    def _generate_export(case_id: str, user: CurrentUser = Depends(require_role("Reviewer", "Approver", "Admin"))):
        return {"ok": True}

    @app.get("/exports/{export_id}/download")
    def _download_export(export_id: str, user: CurrentUser = Depends(require_role("Approver", "Admin"))):
        return {"ok": True}

    return TestClient(app)


def _override_role(role: str):
    def _dep():
        return CurrentUser(
            user_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            role=role,
        )
    return _dep


def test_viewer_blocked_from_document_upload():
    client = _build_client_with_role("Viewer")
    case_id = uuid.uuid4()
    files = {"file": ("test.pdf", b"%PDF-1.4\n%", "application/pdf")}
    r = client.post(f"/cases/{case_id}/documents", files=files)
    assert r.status_code == 403
    assert "Insufficient role permissions" in (r.json().get("detail", ""))


def test_viewer_blocked_from_evidence_mutations():
    client = _build_client_with_role("Viewer")
    exc_id = uuid.uuid4()
    body = {"document_id": str(uuid.uuid4()), "page_number": 1}
    r1 = client.post(f"/exceptions/{exc_id}/evidence", json=body)
    assert r1.status_code == 403
    assert "Insufficient role permissions" in (r1.json().get("detail", ""))

    ev_id = uuid.uuid4()
    r2 = client.patch(
        f"/exceptions/{exc_id}/evidence/{ev_id}/closing",
        json={"is_closing": True},
    )
    assert r2.status_code == 403
    assert "Insufficient role permissions" in (r2.json().get("detail", ""))


def test_unauthorized_export_actions_blocked():
    # Viewer cannot generate
    client = _build_client_with_role("Viewer")
    case_id = uuid.uuid4()
    r = client.post(f"/cases/{case_id}/exports/bank-pack")
    assert r.status_code == 403
    assert "Insufficient role permissions" in (r.json().get("detail", ""))

    # Reviewer cannot download
    client2 = _build_client_with_role("Reviewer")
    export_id = uuid.uuid4()
    r = client2.get(f"/exports/{export_id}/download")
    assert r.status_code == 403
    assert "Insufficient role permissions" in (r.json().get("detail", ""))
