# Decisions (this cleanup)

### D-BS1 — Strangler, not rewrite · 2026-08-18

Keep FastAPI / Postgres / MinIO / Redis / Celery / ocr_service / RBAC / audit / candidates vs confirmed / Exception and CP as separate models / dual-control / bank pack.

Do not add Kafka, Fact table, Exception+CP merge, auto-confirm OCR, or `backend/app/domain/` big-bang.

### D-BS2 — Workbench is a read model + façades · 2026-08-18

`GET /cases/{id}/workbench` aggregates CORE services. FindingView is a serializer. Old routes stay as adapters. Pack issuance stays in `exports.py` / `exports.generate_bank_pack`.

### D-BS3 — Analytics stay registered but frozen · 2026-08-18

dashboard, dashboard_views, case_insights, digests still have frontend or Celery callers. Unregistering would break those UIs. Completing a Matter does not require them.

### D-BS4 — Direct waive deprecated, not removed · 2026-08-18

Callers remaining: `ExceptionsPanel.tsx`, `frontend/lib/api.ts` `waiveException`, `frontend/lib/exceptions-api.ts`, `frontend/app/api/exceptions/[id]/waive/route.ts`. Remove PATCH/POST waive only when grep is zero.

### D-BS5 — One active Punjab pack · 2026-08-18

Production `RULEPACK_PATH` = `docs/rulepacks/punjab_mortgage_v1.yaml`. Archived generic KYC-02/05/07/10. Tests keep `docs/05_rulepack_v1.yaml`. GOLD-*-01 unchanged; do not hard-code RUN 3 values.

### D-BS6 — OCR delete gate (later PR; all must be true)

1. No production/worker/API import of engine-only modules (`ocr_paddle`, `ocr_layout`, unused `ocr_engine` path).
2. No active test depends on them.
3. OCR baseline exists (Q1/Q4).
4. RUN 3 passes.
5. Compose smoke passes.

Until then: Celery → `ocr_pipeline` → `ocr_service` → `DocumentPage` is the production path. Stack B helpers that workers still import stay.

### Pytest / RUN 3

- `python -m pytest tests -q` (backend): **205 passed** (2026-08-18).
- `npm run test:workbench` and `npm run typecheck`: passed.
- Live RUN 3 / compose smoke: not replayed this session (stack down). Do not claim CER.
