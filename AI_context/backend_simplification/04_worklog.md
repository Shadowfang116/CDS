# Backend simplification worklog

## 2026-08-18 — freeze-and-delete pass on `refactor/cds-backend-core`

S0 inventory + S1 classification in this folder. No Exception+CP merge. No Finding table.

S2: `GET /cases/{id}/workbench` plus extract / confirm-fact / evaluate / process-document / request-waiver / submit façades. Pack stays on existing `/exports` path. Matter workbench `load()` uses the single read model.

S3: deleted two `.bak` files. Left phase10 and frozen analytics registered.

S4: deprecated PATCH/POST direct waive (Deprecation headers). ExceptionsPanel still calls it. Workbench uses maker/checker.

S5: `docs/rulepacks/punjab_mortgage_v1.yaml` ACTIVE; archive KYC-02/05/07/10; `05_rulepack_v1.yaml` remains for rulepack tests. `RULEPACK_PATH` pointed at the Punjab pack. GOLD-*-01 unchanged.

S6: documented production OCR path; marked `ocr_paddle.py` / `ocr_layout.py` deprecated; Stack B not deleted.

RUN 3 live replay not run this session (stack was down at freeze). Pytest recorded in `05_decisions.md`.
