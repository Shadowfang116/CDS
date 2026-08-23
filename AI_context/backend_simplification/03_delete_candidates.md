# S3 delete candidates

Caller search: imports, router, Celery, frontend, scripts, tests, compose, env.

## Deleted this pass (grep clean)

| Path | Proof |
|---|---|
| `frontend/components/documents/DocumentViewer.tsx.bak` | No imports. Git has history. Live viewer is `DocumentViewer.tsx`. |
| `backend/app/services/doc_classifier.py.bak` | No imports. Live classifier is `doc_classifier.py`. |

## Not deleted (live or unproven)

| Path | Why |
|---|---|
| `backend/app/api/routes/documents_phase10.py` | Frontend `getPageThumbnailUrl` → `/documents/{id}/pages/{n}/thumbnail`. **ADAPTER, keep.** |
| dashboard / dashboard_views / case_insights / digests | Frontend `api.ts` + `/digests` page + Celery beat. **FROZEN, still registered.** |
| `ocr_paddle.py`, `ocr_layout.py` | Zero production imports but S6 forbids deletion until measurement gate. |
| Playbooks / case_controls / verifications | Not proven duplicate of Findings. |
| `backend/app/api/routes/extractions.py` | Unregistered, no frontend callers. Left in place this pass; not in the lowest-risk bak/phase10 list. |
| Email / webhooks | Later. |
| Old case-workspace | Later, after Inbox+Workbench is the only UI. |

## Stop rule

If any live caller appears, stop. UNKNOWN cannot be deleted.
