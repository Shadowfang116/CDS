---
target: the dashboard
total_score: 23
max_score: 40
na_heuristics:
p0_count: 1
p1_count: 2
timestamp: 2026-08-13T13-35-04Z
slug: frontend-app-dashboard-page-tsx
---
# CDS dashboard critique

Method: dual-agent (A: design review · B: detector)

## Design Health Score: 23/40 Acceptable

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Refresh/skeletons exist; auto tutorial competes |
| 2 | Match System / Real World | 2 | Nav says Cases; product voice is matters |
| 3 | User Control and Freedom | 3 | Filters clearable; forced first-run tutorial |
| 4 | Consistency and Standards | 1 | Three token systems; zinc vs stone vs dashboard-* |
| 5 | Error Prevention | 2 | Weak destructive confirm; filter+drawer over-narrow |
| 6 | Recognition Rather Than Recall | 3 | Labels present; chart-click filters must be remembered |
| 7 | Flexibility and Efficiency | 2 | Saved views; no keyboard accelerators |
| 8 | Aesthetic and Minimalist Design | 1 | Orbs, grid backdrop, 4 KPIs + 3 queues |
| 9 | Error Recovery | 3 | Retry CTAs and failure toasts |
| 10 | Help and Documentation | 3 | Tour/walkthrough abundant for Operate |
| **Total** | | **23/40** | **Acceptable** |

Cognitive load: 5/8 checklist failures (high).

## Design Specificity Verdict

Partially authored for CDS, visually category-generic SaaS. IA knows exceptions/CP; chrome is interchangeable dark admin.

**Deterministic scan:** 1 advisory — `codex-grid-background` at `frontend/app/globals.css:385` (`.dashboard-backdrop__grid` dual-axis 72px grid). Broader rescan of dashboard/layout/ui/globals: still 1 finding. Low–medium false-positive chance if treated as a blueprint surface; class + nearby orbs read as cosmetic.

LLM and detector agree: decorative atmosphere (grid, orbs, gradients) is the visual problem. Detector missed the token war because it is CSS variable collision, not a slop rule.

## Priority Issues

- **[P0] Token war + light/purple leakage** — `@layer base :root` light oklch; `.dark --sidebar-primary` purple-ish; body radials. Fix: one near-black sheet. `/impeccable quieter`
- **[P1] Dashboard density** — 4 KPIs + 4 counters + 3 lists + tours. Fix: 3 KPIs + one queue + one chart. `/impeccable distill`
- **[P1] Voice drift** — Cases/Documents vs matter/exception/CP/dossier. `/impeccable clarify`
- **[P2] Hierarchy + accent overuse** — `h1` is text-sm; olive on orbs/pills/chips. `/impeccable typeset` `/impeccable quieter`
- **[P3] Button API** — `variant="primary"` / `loading` vs CVA `default`. `/impeccable polish`

## Persona red flags

Alex: no shortcuts; auto TutorialDialog. Sam: colour-as-status; stone-500 at 11px. Reviewer: first CTA row is tours/demo, not next blocking matter.

## Questions

1. If the job is clear the next blocking exception, why do first CTAs open tours?
2. What if olive appeared only on KPI numerals, ready checks, and one primary button?
3. Should Documents be a top-level peer, or OCR inside a matter?
