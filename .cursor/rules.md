# Cursor Collaboration Rules

## Change discipline
- Small diffs only; no speculative refactors.
- Add tests for critical parsing / rules evaluation when feasible.

## Security & multi-tenancy
- Every DB table containing business data must have org_id.
- Every query must filter by org_id.
- Every export must be authorized by RBAC checks.

## Logging
- Every key action writes AuditLog event:
  login, view_case, create_case, upload_doc, ocr_complete, generate_export, status_change, resolve_exception, waive_exception

## Output formatting
- Provide exact file paths and pasteable code.
- Provide verification steps and expected results.

