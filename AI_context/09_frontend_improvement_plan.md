# Frontend improvement plan — CDS

## Scope

Implement the frontend audit plan from 2026-08-24 without changing CDS product terminology or backend semantics. The protected UI must remain operationally focused: Inbox, Matter, File, Evidence, Work, Exceptions, Conditions Precedent, approvals, and audit.

## Acceptance criteria

- Local frontend can be run with a local API URL and shows a useful unavailable-backend state when the API is down.
- Login has no horizontal overflow at 320–430px and retains readable hierarchy.
- Interactive controls have at least a 44px hit area unless they are non-interactive decoration.
- Status, surface, border, and chart colors are semantic tokens rather than repeated raw values.
- Protected routes remain keyboard navigable and preserve existing data workflows.
- Large viewer/workspace responsibilities have clearer seams without changing API behavior.
- `npm run typecheck`, `npm run build`, and focused frontend checks provide reproducible evidence.

## Completion status — 2026-08-24

- [x] Local API fallback and an explicit unavailable-backend state.
- [x] Login verified without horizontal overflow at 390px; the prior 500px document width is resolved.
- [x] Shared interactive controls and reviewed navigation controls have a 44px minimum hit area.
- [x] Semantic surface, border, status, and chart tokens added and consumed by the reviewed UI.
- [x] Form labels, live error/status announcements, evidence alt text, and reduced-motion handling improved.
- [x] Focused document-viewer formatting seam extracted without changing API behavior.
- [x] Workbench tests, typecheck, lint, production build, and 22-route smoke checks pass.
- [ ] Authenticated protected-route visual QA remains pending until the local API service is running.

## Case workspace redesign — 2026-08-24

- Required evidence rows open their preferred document and page through the workbench query state.
- Viewer uses a reviewer-sized PNG render for crisp, browser-compatible page display, with PDF download preserved separately.
- OCR text has a larger responsive panel, sticky controls, and improved bilingual text line-height.
- Matter header now separates status, decision, readiness, counts, blocker, and next action into clearer hierarchy.

## Phases

1. Runtime/testability: local API fallback, explicit unavailable state, route smoke coverage.
2. Release blockers: mobile overflow, touch targets, form/error semantics, dialog focus.
3. Visual system: semantic tokens and removal of repeated product colors.
4. Maintainability: extract focused viewer/workspace seams only where behavior is preserved.
5. Verification: lint/typecheck/build, browser desktop/mobile checks, and audit notes.

## Non-goals

- No backend API redesign.
- No replacement of the CDS visual identity.
- No fabricated demo data, legal conclusions, bank branding, or customer claims.
- No broad rewrite of every component solely to reduce line count.
