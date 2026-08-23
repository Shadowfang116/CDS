# S0 freeze inventory

**Date:** 2026-08-18  
**Branch:** `refactor/cds-backend-core` (cut from `fix/cds-gold-001-semantics`)  
**Scope:** freeze unused surfaces, classify everything, delete only proven-dead duplicates. No Exception+CP merge. No Finding table. No Stack B OCR deletion.

## Feature freeze

No Surya/Paddle work, no new analytics, no new workflow engine, no new generic rules in this pass.

## Product loop (unchanged)

Evidence → Facts → Findings → Decision → Pack, with tenant isolation, audit, and maker/checker.

## RUN 3 baseline (already closed; do not use RUN 1)

| | |
|---|---|
| Flagship matter | `38e6069e-4c3d-4a41-94c8-8b9ecc92e069` |
| Gold findings | GOLD-AREA-01, GOLD-PLAN-01, GOLD-DUES-01, GOLD-ENCUMB-01, GOLD-FARD-01, GOLD-NAME-01, GOLD-TAX-01 |
| Waiver | GOLD-TAX via dual-control `exception_waive` |
| Pack | `670f6c3e-823c-4d1d-b2e6-3803391c0a59` |
| E2E | `scripts/dev/run_cds_gold_001_e2e.ps1` (do not use RUN 1) |
| Visual corpus | RUN 2 `5bcdb8eb-75bc-440b-9bcb-3a963b574360` |

Compose health and a live RUN 3 replay were **not** available at freeze time (API/frontend down). Recorded from prior RUN 3 report: `AI_context/execution_reports/04_cds_gold_001_run3.md`.

## Pytest gate

Targeted: `backend/tests/test_workbench.py`, `test_cds_gold_001_semantics.py`, `test_exception_waivable.py`, `test_next_action.py`, `test_dual_control.py`.  
Full: `python -m pytest tests -q` from `backend/` — **205 passed** (2026-08-18). Frontend `npm run test:workbench` and `npm run typecheck` passed.

## Active routes (`backend/app/api/router.py`)

auth, cases, **workbench**, inbox, documents, documents_phase10, downloads, ocr, ocr_text_corrections, pages_ocr, dossier, dossier_autofill, dossier_fields, rules, rules_evidence, exports, admin, verification, dashboard, dashboard_views, case_insights, digests, notifications, approvals, integrations_webhooks, integrations_email, health, ocr_extractions, config, regime, case_controls, audit_timeline, evaluations.

## Celery tasks (`backend/app/workers/`)

| Task | Module | Class |
|---|---|---|
| `ocr.process_document` | tasks_ocr.py | CORE |
| `ocr.rerun_page` | tasks_ocr_rerun.py (sent from pages_ocr) | CORE |
| `worker.ping` | celery_app.py | CORE |
| `retention.run_retention_now` | tasks_retention.py | CORE |
| `integrations.process_integration_events` | tasks_integrations.py | FROZEN growth |
| `exports.generate_bank_pack` | tasks_export.py | CORE |
| `digests.generate_pdf` | tasks_digest.py | FROZEN |
| `digests.run_due_schedules` | tasks_digest.py | FROZEN |

Beat still schedules digests, integrations, retention.

## Production OCR path (do not delete Stack B this pass)

Celery `ocr.process_document` → `ocr_pipeline.run_ocr_pipeline` (HTTP client) → `ocr_service` → `DocumentPage`.  
Workers still import `ocr.py` (`download_page_pdf` / `pdf_to_image`), `ocr_quality`, and autofill uses `ocr_fallback.get_page_text_with_fallback`.

## Nothing deleted in S0

Inventory only. Deletes are S3 and only after caller proof.
