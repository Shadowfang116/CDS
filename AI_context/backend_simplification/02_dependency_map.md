# S1 classification

Labels: **CORE** | **ADAPTER** | **FROZEN** | **DEV-ONLY** | **DELETE-CANDIDATE** | **UNKNOWN**.  
UNKNOWN cannot be deleted.

## Routes (`backend/app/api/routes/`)

| File | Purpose | Callers | Tests / RUN 3 | Class |
|---|---|---|---|---|
| auth.py | Login/session | frontend, e2e | rbac | CORE |
| cases.py | Case CRUD/status | workbench upload path, inbox | dual-control | CORE |
| workbench.py | GET workbench + thin façades | Matter UI | test_workbench | CORE |
| documents.py | Upload/list | workbench, viewer | gold e2e | CORE |
| documents_phase10.py | Page thumbnail + OCR text | `getPageThumbnailUrl` | viewer | ADAPTER |
| downloads.py | Signed downloads | exports, viewer | pack | CORE |
| ocr.py | Enqueue OCR / status / doc type | documents, workers | gold e2e | CORE |
| ocr_text_corrections.py | Corrected OCR text | viewer | — | CORE |
| pages_ocr.py | Per-page OCR + rerun | viewer | — | CORE |
| dossier.py / dossier_fields.py / dossier_autofill.py | Candidates vs confirmed | workbench extract, editor | contextual autofill | CORE |
| ocr_extractions.py | Candidate confirm | editor | gold | CORE |
| rules.py | Evaluate, exceptions, CPs, **deprecated direct waive** | workbench façades + ExceptionsPanel | gold, dual-control | CORE |
| rules_evidence.py | Evidence refs | exceptions | — | CORE |
| approvals.py | Maker/checker | workbench decide | dual-control | CORE |
| exports.py | Bank pack + drafts | workbench pack | RUN 3 pack | CORE |
| verification.py | e-stamp / registry | workbench verifications | — | CORE |
| inbox.py | Reviewer inbox | Inbox UI | — | CORE |
| health.py / config.py / regime.py | Ops | compose | — | CORE |
| admin.py | Admin + demo seed | admin UI | DEV-ONLY seed | CORE + DEV-ONLY seed |
| audit_timeline.py | Audit | AuditPanel | — | CORE |
| case_controls.py | Playbook/checklist | old case-workspace | keep until proven duplicate of Findings | CORE (review later) |
| evaluations.py | Golden-case eval | evaluations UI | DEV-ONLY-ish | ADAPTER |
| dashboard.py | Analytics KPIs | governance, dashboard | not RUN 3 | FROZEN |
| dashboard_views.py | Saved views | api.ts | not RUN 3 | FROZEN |
| case_insights.py | Per-case analytics | case-workspace | not RUN 3 | FROZEN |
| digests.py | Digest schedules | `/digests` page + beat | not RUN 3 | FROZEN |
| integrations_webhooks.py / integrations_email.py | Notify expansion | settings | later | FROZEN |
| notifications.py | In-app bell | shell | — | ADAPTER |
| extractions.py | Older extraction routes | **not registered in router.py**, no frontend callers | — | DELETE-CANDIDATE (not deleted this pass; unregistered shadow of ocr_extractions) |

## Services (`backend/app/services/`)

| File / area | Class | Notes |
|---|---|---|
| workbench.py | CORE | Read model + façades over existing services |
| rule_engine.py, rule_schema.py, exception_waive.py | CORE | GOLD-* evaluators; RUN 3 |
| dossier_autofill.py + extractors/* | CORE | Do not shrink this pass |
| canonical_docs.py, document_facts.py | CORE | Gold classification/facts |
| ocr_pipeline.py, ocr_enqueue.py | CORE | HTTP client to ocr_service |
| ocr.py (download_page_pdf / pdf_to_image) | CORE | Worker still imports |
| ocr_quality.py, ocr_fallback.py, ocr_text_quality.py | CORE | Autofill / candidate_gate |
| ocr_engine.py, ocr_preprocess.py, ocr_script_detect.py, ocr_text.py, ocr_domain_ur.py | ADAPTER | Legacy Stack B helpers still imported from ocr.py / fallback |
| ocr_paddle.py, ocr_layout.py | FROZEN / deprecated | **Zero production imports.** Do not delete until Q4 gate |
| ocr_eval.py | DEV-ONLY | scripts/dev/eval_*.py |
| approvals.py, workflow.py, next_action.py, audit.py | CORE | |
| export_bank_pack.py, export_drafts.py | CORE | |
| inbox.py, storage.py, thumbnails.py, pdf_splitter.py, download_tokens.py | CORE | |
| playbooks.py, regime_classifier.py | CORE until merge later | |
| digest_generator.py, cohort_pdf_generator.py | FROZEN | |
| webhooks_sender.py, email_sender.py, event_bus.py | FROZEN | |
| demo_seed.py | DEV-ONLY | admin seed |
| retention.py, notifications.py, crypto.py, candidate_validation.py, evaluation_service.py | CORE or ADAPTER | keep |

## ocr_service/

| File | Class |
|---|---|
| main.py, schemas.py, preprocessing.py, quality.py | CORE |
| engines/tesseract_engine.py | CORE |
| engines/surya_engine.py | CORE optional engine already wired; **no new Surya work this freeze** |

## Frontend leftovers

| Item | Class |
|---|---|
| ExceptionsPanel PATCH waive | ADAPTER until S4 callers = 0 |
| case-workspace + insights | FROZEN UI; keep routes |
| DocumentViewer.tsx.bak, doc_classifier.py.bak | DELETE-CANDIDATE → deleted in S3 |

## Not deleted

`documents_phase10.py` — live thumbnail ADAPTER.  
Dashboard/digest/insight routes — frontend callers exist; FROZEN, still registered.
