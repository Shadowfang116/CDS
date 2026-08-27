# Frontend improvement worklog

## 2026-08-26 — Browser-comment regression fixes

- Fixed the shared page header overflow reported on `/dashboard/cases`: redundant
  self-breadcrumbs are omitted, meaningful breadcrumbs share the title row, and the
  title/subtitle remain inside the fixed header bounds.
- Fixed the Matter OCR panel overlap reported in the Evidence view: the `Extracted
  text / Copy` toolbar is no longer sticky inside the scrolling OCR content, so text
  cannot pass underneath it. Rechecked at the reported 1569×958 browser viewport;
  toolbar position is static and extracted text remains unobscured while scrolling.

## 2026-08-26 — CDS simplification recovery implementation and verification

- Scope: preserved the existing dirty worktree, then implemented the approved recovery
  plan in the active Docker stack. The primary frontend shell now has one stable sidebar
  with Inbox, Matters, Documents, Issues, Approval requirements, role-gated Approvals
  and Audit, Settings, Help, and account actions. Its labels/order remain stable across
  the canonical authenticated routes tested.
- Matter workflow: the case viewer now leads with a six-step workflow — Upload
  documents, Analyze documents, Review evidence, Resolve issues, Confirm facts, and
  Submit for approval. Desktop uses Files + Evidence with an on-demand Review work
  drawer; tablet/mobile use one surface at a time with Files, Evidence, Issues, Facts,
  and Decision tabs. The mobile 390px check measured `scrollWidth=390` with no page
  overflow.
- Browser evidence through Codex in-app Browser: desktop 1280px rendered the protected
  Matter page and evidence image/OCR; selecting the Registered Sale Deed then the
  Approved Building Plan updated the URL, selected row, page count, rendered viewer,
  and OCR content. `field=property.type` produced no edit dialog; explicit `edit=...`
  opened the review-work surface. An issue opened the drawer and Close restored the
  underlying page without the drawer. Tablet 768px and mobile 390px rendered the
  single-surface navigation; mobile Evidence and Issues tabs were interacted with.
- Corpus: `C:\\Users\\fahad\\Downloads\\CDS_GOLD_001_URDU_PDF_CORPUS`, ground truth
  from `03_GOLD_TRUTH/gold_truth.yaml`, `README_TEST_CASE.md`, and `SOURCE_BASIS.md`.
  The required separate run processed 12 initial PDFs and then 5 additional PDFs.
  Initial evaluation produced 7 open findings (4 high, 2 medium, 1 low), matching the
  seven expected gold issues. After the five additional PDFs, only the expected
  historic-tax item remained open. Reviewer proposal plus Admin approval of its waiver
  produced zero open findings and decision `PASS`. The bank-pack export was accepted
  and queued (`pending`). Full JSON: `AI_context/execution_reports/cds_gold_001_e2e_20260826-135747.json`.
- OCR: Docker `/health` reported Tesseract; default and explicit `/ocr` smoke requests
  both returned `engine_used: tesseract`; `eng`, `osd`, and `urd` language data were
  present. The active Surya dependency, selection/fallback path, and zero-caller engine
  module were removed. Focused OCR tests passed.
- Login visual: the Canvas2D retropc effect is login-only, locally sourced, reduced-
  motion aware, hidden-tab aware, and has a plain fallback. After signing out through
  the visible app control, the in-app browser rendered the unauthenticated login page
  at desktop and mobile widths with a live canvas, readable form, and no mobile page
  overflow. A narrow login composition fix added a dark translucent readable surface
  behind the form after the first screenshot showed the effect competing with the copy.
- Simplification verdict: **materially simplified, but not finished to a perfect
  low-density review experience**. The global navigation and outer Matter structure
  are now substantially clearer, and the mobile three-column compression is removed.
  Highest-impact remaining work is reducing density inside the Evidence viewer itself
  (thumbnail/source/highlight details compete in one area) and completing a fresh
  unauthenticated login screenshot check. The current implementation meets the tested
  workflow direction without claiming those remaining items are solved.
- Verification commands: `npm run lint`, `npm run typecheck`, `npm run test:workbench`,
  `npx --yes tsx lib/retropc.test.ts`, `npm run build`, and
  `FRONTEND_URL=http://localhost:3000 npm run smoke:routes` all passed. Docker Compose
  config, service health, OCR endpoint smoke, focused OCR tests, and the separate corpus
  runner also passed. Build emitted only existing Next.js middleware/Browserslist
  maintenance notices.

## Current state

| Field | Value |
|---|---|
| Last updated | 2026-08-26 |
| Phase | Matter simplification implemented; final corpus/release evidence remains to be consolidated |
| Scope | `frontend/` plus this context folder |
| Backend availability | Docker API, worker, OCR, frontend, database, Redis, and MinIO were healthy during verification |
| User-visible changes | Stable global navigation, Documents/Review/Decision Matter workspace, source-first evidence review, contextual inspector, mobile single-surface layout |

## 2026-08-26 — Fresh full-stack corpus and workflow verification

- Re-read the corpus documentation and ground truth from
  `C:\\Users\\fahad\\Downloads\\CDS_GOLD_001_URDU_PDF_CORPUS\\03_GOLD_TRUTH`.
- Ran the documented two-phase workflow on fresh matter
  `5e1ce693-6fcc-414f-a09d-5fa0eb538764`: 12 initial PDFs processed, then 5
  additional PDFs processed. Initial evaluation produced exactly 7 open findings
  (4 high, 2 medium, 1 low); additional evidence left only the expected historical
  property-tax issue; reviewer waiver proposal plus admin approval produced zero
  open findings and decision `PASS`.
- The bank-pack export completed successfully after initially reporting `running`,
  and the authenticated download endpoint returned a valid PDF download token.
- Service checks passed: API `/health`, OCR `/health` with Tesseract, Docker Compose
  config, and all Compose services healthy. Frontend lint, typecheck, workbench tests,
  backend gold tests (`32 passed`), and OCR tests (`1 passed`) passed. Warnings were
  limited to the configured example secret and FastAPI lifecycle deprecations.
- In-app browser checks against the fresh matter passed at desktop and 390px mobile:
  stable sidebar, Documents/Review/Decision surfaces, document selection changing URL
  and evidence, Source page / Extracted text switching, Review, Decision readiness, and
  mobile no-overflow (`scrollWidth=clientWidth=364px`).

## 2026-08-26 — Matter workspace recovery and browser verification

- Adapted the sampled Studio Editor pattern as a workspace model: a stable global
  sidebar, a compact Matter rail, one dominant evidence surface, and an inspector
  that opens only for a selected review item. Article editing, media, publishing, and
  slash-command behavior were not copied.
- The Matter rail now has exactly three user-facing destinations: Documents, Review,
  and Decision. Legacy `surface=files|evidence|issues|facts` values normalize into
  those destinations; legacy `work=1` remains readable for compatibility.
- Evidence defaults to Source page. Extracted text and Side by side are explicit
  views. The OCR toolbar is outside the scrollable text region, and the highlight
  column is removed from the compact workflow so it cannot cover extracted text.
- Fresh in-app browser checks after the rebuild: protected Matter rendered; Source
  page, Extracted text, and Side by side were each interacted with; Review and
  Decision rendered; a linked review item opened an inspector; closing it preserved
  the selected document/page context. At a 390px viewport, Documents, Review, and
  Decision tabs worked and `scrollWidth` equaled the client width (364px after the
  browser scrollbar), with no horizontal overflow.
- Plain-language review: the main shell and Matter workflow use Documents, Issues,
  Approval requirements, Review, and Decision rather than exposing internal panel
  names. Remaining wording cleanup is limited to older action labels inside legacy
  dialogs and should be handled as a separate copy pass.
- Simplification verdict: **materially simplified, not perfect**. The competing
  permanent panes and route-changing sidebar are removed. The highest-impact
  remaining simplification is reducing density inside the evidence/document list on
  very wide desktop layouts and replacing a few legacy dialog labels consistently.

## Log

### 2026-08-24 — Implementation started

- Prior audit opened the login route at `http://localhost:3100/login?next=%2Fdashboard`.
- Verified mobile overflow at 390px: document width measured 500px.
- Verified the server-side `/api/me` fallback defaults to Docker DNS (`http://api:8000`).
- The implementation will proceed in phases and update this log after each phase.

### 2026-08-24 — Runtime/testability seam

- Added `frontend/lib/runtime-config.ts` with a test-first resolver: development falls back from Docker DNS to `API_BASE_URL` or `http://localhost:8000`.
- Updated the `/api/me`, catch-all proxy, exception, resolve, and waive route handlers to use the resolver.
- `/api/me` now returns a structured 503 when the API is unavailable instead of leaking a fetch failure as a 500.
- Red test was observed first (`Cannot find module '../runtime-config'`); the focused workbench test then passed after implementation.

### 2026-08-24 — Release blockers

- Login heading now wraps below the `sm` breakpoint instead of forcing a 500px document width on a 390px viewport.
- Login API/session failures are announced with `role="status"`; credential errors use `role="alert"`.
- Shared button variants and CDS navigation/icon controls now expose a 44px minimum hit area.
- Added a real `.light` theme token set and semantic status tokens for high, medium, low, good, and neutral states.
- Chart palette now consumes semantic CSS variables instead of fixed hex values.

### 2026-08-24 — Visual system and maintainability

- Added dark/light semantic tokens for surfaces, text, borders, and status states.
- Updated CDS pills and dashboard chart palettes to consume semantic status variables.
- Reduced sidebar transition duration to 200ms and added a reduced-motion transition fallback.
- Extracted document type and OCR quality formatting into `components/documents/document-viewer-format.ts` with focused unit assertions.
- Focused workbench tests pass after the extraction.

### 2026-08-24 — Accessibility pass

- Evidence previews now have descriptive alt text when a page image is present.
- Change-password inputs now have explicit `id`/`htmlFor` associations and live alert semantics.
- Evidence, drawer, notification, document-delete, and navigation controls received 44px hit-area treatment.
- Reduced the change-password page’s oversized corner radii and shadow depth to match the operational UI system.

### 2026-08-24 — Route verification

- Added `npm run smoke:routes` covering 22 frontend routes.
- Fresh run: all routes returned acceptable 200/307 responses; protected routes redirected to login as expected.

### 2026-08-24 — Final verification

- `npm run test:workbench` passed.
- `npm run typecheck` passed.
- `npm run lint` passed with zero errors and zero warnings after removing the unused insights setter.
- `npm run build` passed; Next.js reported only existing maintenance notices for the deprecated middleware convention and stale Browserslist data.
- `npm run smoke:routes` passed for all 22 routes.
- Browser review remains open at `http://localhost:3100/login?next=%2Fdashboard`.
- The fresh desktop browser state has no document overflow; the earlier 390px mobile measurement after the login fix was `bodyWidth=390`, `scrollWidth=390`, confirming the release-blocking overflow is resolved.
- Authenticated dashboard, case, document, exception, and workspace visual QA could not be completed because no local API service is running. Start the API, then repeat the protected-route browser pass before release.

### 2026-08-24 — Docker image and container verification

- Rebuilt the frontend image from the current `frontend/` workspace with `docker compose up -d --build frontend`.
- Rebuilt and started the API dependency chain; frontend and API containers are healthy on ports 3000 and 8000.
- Docker frontend image digest: `sha256:d398965ba1da85a4236621a04a9c1737d2abccc08a7780405a374c50174346cb`.
- Docker API image digest: `sha256:4b1b3e9ac2072456579ac04795ead89a56349c36b76d23302c73f1d24dc5adb0`.
- Container smoke test passed against `FRONTEND_URL=http://localhost:3000` for all 22 routes.
- In-browser container test passed: login rendered, invalid credentials produced the expected alert, and `/dashboard` redirected unauthenticated users to `/login?next=%2Fdashboard`.
- Workbench tests, typecheck, and lint were rerun against the current workspace after the container build; no new failures were observed.

### 2026-08-26 — First-run onboarding flow

- Mounted the existing onboarding tour and checklist in the authenticated application shell.
- Reduced the first-run tour to four plain-language steps: review queue, create a matter, open a matter, and work through evidence.
- Added reliable tour anchors to the dashboard, new-matter form, matter list, and matter workspace.
- Updated checklist copy so it describes a new matter workflow instead of assuming a demo case.
- Kept auto-start limited to the dashboard and removed the checklist's unnecessary query-hook dependency so static routes remain buildable.
- Verification passed: `npm run lint`, `npm run typecheck`, `npm run test:workbench`, `npm run build`.
- Live local checks passed: `http://localhost:3000/dashboard` returned 200 and `http://localhost:8000/api/v1/health/deep` returned 200.
- Authenticated API smoke passed with the repository's documented demo account: login 200, current-user 200, inbox 200, and seeded matter workbench 200 with documents and findings present. Browser visual verification is pending explicit permission to enter the documented password.
- Dashboard empty-state onboarding was strengthened with a direct Create a matter action, an explicit optional-document label, and a live matter-list tour anchor.
- `npm run smoke:routes` passed all 22 routes against the Docker frontend at `FRONTEND_URL=http://localhost:3000`; the script's default `3100` port is for the older standalone dev setup.
- Full backend verification passed: `python -m pytest -q` → `205 passed, 1 warning`. The warning is the expected local example `APP_SECRET_KEY` configuration warning.
- Help now includes a Restart tour action, allowing users to recover the onboarding walkthrough after dismissing it.
- Frontend lint, typecheck, workbench tests, and production build were rerun after the Help/onboarding change and passed.
- Added a reproducible authenticated browser smoke checklist to `docs/ops/RELEASE_CHECKLIST.md`, covering onboarding recovery, matter creation, evidence continuity, provisional OCR, role separation, and plain-language risk states.
- Added `docs/ONBOARDING_GUIDE.md` with a plain-language first-day flow, role responsibilities, matter-reading rules, stuck-state guidance, and pilot setup checklist for bank and legal teams.

### 2026-08-24 — Case workspace interaction and viewer redesign

- Fixed required-evidence navigation: rows now expose accessible `Open <filename>` buttons and update the workbench `doc`/`page` query state.
- Replaced the blank embedded-PDF path with a reviewer-sized PNG render endpoint at `/api/v1/documents/{document_id}/pages/{page_number}/render`, backed by the existing 200-DPI PDF renderer.
- Viewer test confirmed the rendered page is visible in Docker at `2481×3508` pixels instead of the previous low-resolution thumbnail.
- Expanded the compact OCR panel from a fixed 150px height to a responsive 190–280px region, with sticky controls and improved line height.
- Reworked the matter header status/decision/readiness and file metrics into a clearer hierarchy.
- Final frontend checks passed: workbench tests, typecheck, lint, and Docker production build.

### 2026-08-26 — CDS-GOLD-001 Urdu corpus browser QA

- Corpus: `C:\\Users\\fahad\\Downloads\\CDS_GOLD_001_URDU_PDF_CORPUS`; 17 synthetic Urdu PDFs (12 initial-evidence files including the duplicate board resolution plus 5 additional-evidence files), with `03_GOLD_TRUTH/gold_truth.yaml`, `README_TEST_CASE.md`, and `SOURCE_BASIS.md` used as the comparison basis.
- Runtime: Docker Compose API, worker, OCR service, and frontend; migrations current; authenticated browser session used `admin@orga.com`.
- In-browser ingestion: created matter `CDS-GOLD-001 Browser QA` (`6f9a2181-82ad-4b0b-9aeb-8795db1406fa`) and uploaded all 17 PDFs in one multi-file action. All 17 classified and reached `OCR complete`; no document showed a failed state.
- Viewer/OCR: protected matter workspace rendered on desktop; page image completed loading, OCR confidence/status appeared, extracted OCR text was visible, and evidence-highlight actions (`Use as fact`, `Copy text`, `Attach as evidence`, `Open viewer`) were present and interactive. OCR text contained the synthetic disclaimer and Urdu content, but quality was noisy/mixed-script in places.
- Evaluation comparison: after `Process new evidence`, the UI produced `CONDITIONAL_PASS`, 4 open findings, 2 open CPs, and 3 proposed values requiring confirmation. Gold expected 7 initial exceptions and a final state with area/building-plan/dues/prior-charge/name resolutions plus a tax waiver; because all initial and additional files were uploaded together, the browser run cannot prove the initial-vs-final transition. The observed findings were tax/Fard focused and included duplicate Fard/tax entries; expected area, approved-plan, development-dues, prior-charge, and company-name findings were not surfaced distinctly.
- Error state: signed out in-browser, submitted invalid credentials, and verified the visible `Invalid credentials. Please try again.` alert.
- Responsive check: at 390px the document width remained 390px with no page-level horizontal overflow, but the three-pane matter workspace compressed into narrow independently scrollable columns; important controls and reading areas were clipped behind internal horizontal/vertical scrollbars. Desktop 1280px rendered all three panes but remained dense.
- Simplification verdict: materially simplified compared with the prior implementation (clearer header hierarchy, fewer top-level navigation items, compact status metrics), but not yet simple enough for a low-density review workflow. Highest-impact remaining work is a mobile single-pane/stacked matter layout and a more deliberate reduction of simultaneous file/evidence/findings controls; desktop still presents three competing panes, a status timeline, metrics, readiness strip, and action rail at once.
- Bugs/blockers: the matter initially opened with the `Edit Field: Type` modal active via the `field=property.type` URL state; the file-pane `Open 01_Registered_Sale_Deed_URDU.pdf` action did not visibly change the selected evidence/viewer in the tested state; and full-batch ingestion prevented a clean gold initial/final comparison. No product code fix was applied because the browser evidence was insufficient to safely identify the owning state transition without risking unrelated work; these remain reproducible QA findings.

### 2026-08-26 — Design authority cleanup and live responsive verification

- Applied `frontend/DESIGN.md` to the authenticated shell: light mode now uses the mineral canvas/surface palette, deep registry-green navigation rail, brass active-route accent, semantic status colors, and sentence-case status labels. The existing dark mode remains available as an explicit toggle.
- Reworked shared navigation styling so the same labeled destinations remain visible across authenticated routes; the active route is a restrained green row with a brass edge rather than a route-dependent sidebar treatment.
- Repaired a live Matters-list contrast failure caused by legacy dark-only table/status styles. Matters now uses readable token-based table text/status treatments, the page copy says “Matters,” “New matter,” and “Open matter,” and the queue description explains the next workflow in plain language.
- Corrected a contradictory Matter header action: a new matter with no server-confirmed readiness now displays `Review matter readiness`, not `Submit for approval`; uppercase API lifecycle values are normalized before this decision.
- Browser verification through the Codex in-app browser: desktop 1280px Matter and Matters views rendered with readable text and stable navigation; mobile 390px Matter view used the sequential Files/Evidence/Issues/Facts/Decision tabs with no page-level horizontal overflow; the mobile navigation drawer opened with the same labeled destinations.
- Verification passed after the changes: `npm run lint`, `npm run typecheck`, `npm run test:workbench`, and `docker compose up -d --build frontend`. The live DOM confirmed the Matters heading, New matter/Open matter actions, all stable sidebar items, and the corrected Review matter readiness text.
- Simplification verdict: materially improved and visually closer to the design authority, but not complete. The Matter evidence area still carries a dense document/page/highlight/OCR composition at desktop widths, and legacy dark-only styling remains in secondary/older presentation surfaces. Highest-impact next work is to consolidate the evidence highlight into an on-demand Work drawer and migrate remaining authenticated secondary pages to the same semantic token layer.

### 2026-08-26 — Production-readiness completion pass

- Fresh full-corpus execution report: `AI_context/execution_reports/cds_gold_001_e2e_20260826-165739.json`. The 12-file initial phase produced the expected 7 issues (4 high, 2 medium, 1 low); the 5-file additional phase reduced this to the historical property-tax item; reviewer waiver proposal plus Admin approval produced final `PASS`; bank-pack export completed successfully.
- OCR verification: service health reports Tesseract; default and explicit `/ocr` requests both returned `engine_used: tesseract`.
- Frontend gates: lint, typecheck, workbench tests, retropc tests, route smoke, and `git diff --check` passed. Route smoke was run against `FRONTEND_URL=http://localhost:3000`; the script's standalone default port `3100` is not running in Docker.
- In-app browser verification after the latest rebuild: `/dashboard/documents`, `/dashboard/exceptions`, `/dashboard/cp`, and `/dashboard/audit` now render their own canonical pages with the stable sidebar instead of redirecting. Login, invalid-credentials feedback, valid Admin login, Matter Documents/Review/Decision surfaces, source/OCR switching, document selection, explicit edit state, reviewer role separation, and audit rendering were exercised.
- The Matter workflow is materially simpler and more understandable than the prior three-pane version, but the final acceptance verdict remains **not complete**: mobile still needs a true one-surface-at-a-time workflow and the desktop evidence/review composition needs further reduction.
- Release blocker: `scripts/ops/verify_prod_readiness.ps1` still fails because the local production environment uses placeholder `POSTGRES_PASSWORD`, `APP_SECRET_KEY`, and `MINIO_ROOT_PASSWORD` values. Do not treat local readiness as production-ready until real secret provisioning is supplied.
