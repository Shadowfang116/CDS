# Development playbook (CDS)

Use this when implementing features or fixes so changes stay aligned with the **end-to-end pipeline** and bank-grade constraints.

## Core pipeline (map every change to a stage)

1. **Upload** — documents ingestion, storage, tenant scoping  
2. **OCR** — page text, quality signals, manual review gates  
3. **Classification** — document types / routing  
4. **Extraction** — structured fields → dossier inputs  
5. **Dossier** — `Case.dossier_json` and related persistence  
6. **Rules** — `docs/05_rulepack_v1.yaml` + `services/rule_engine.py`  
7. **Exceptions + CPs** — `models/rules.py`, `api/routes/rules.py`, UI under `components/exceptions`  
8. **Approval** — case workflow `services/workflow.py`, `api/routes/cases.py`, approvals routes/services  
9. **Bank pack export** — `services/export_bank_pack.py`, `api/routes/exports.py`  

When unclear about intent, read **[00_context_sources.md](00_context_sources.md)** first, then Graphify (if present), then code.

## Likely touchpoints by concern

| Concern | Start here |
|---------|------------|
| Case status / transitions | `backend/app/services/workflow.py`, `api/routes/cases.py` |
| Rule outcomes | `docs/05_rulepack_v1.yaml`, `services/rule_engine.py` |
| Exception / CP behavior | `models/rules.py`, `api/routes/rules.py`, `services/export_bank_pack.py` |
| OCR / async processing | `api/routes/ocr.py`, `workers/tasks_ocr.py`, `services/ocr_pipeline.py` |
| Multi-tenancy | `api/deps.py`; every query must filter `org_id` |
| Audit | `core/audit_guard.py` + `log_request_event` patterns in routes |

## Verification (before claiming done)

From inner `bank-diligence-platform/`:

```powershell
scripts/dev/verify_backend_routes.ps1
scripts/dev/smoke_test.ps1
```

Frontend:

```bash
cd frontend && npm run lint && npm run typecheck
```

See [CLAUDE.md](../CLAUDE.md) for full commands, URLs, and test accounts.
