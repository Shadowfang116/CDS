# Shadcn Dashboard Professionalization Plan (MVP)

## Goal
Upgrade the Next.js dashboard UI to a bank-grade, consistent, reviewer-first experience using shadcn/ui as the primary component and theming system.

## Phases
### Phase 0 — Baseline
- [ ] shadcn init (existing Next.js app)
- [ ] CSS variable theming enabled
- [ ] App shell: Sidebar + Topbar + Content layout
- [ ] Smoke page renders core components

### Phase 1 — Design System
- [ ] Token decisions: severity/status colors, radius, spacing
- [ ] Wrapper components: SeverityBadge, StatusPill, PageHeader, EmptyState, EvidenceLink

### Phase 2 — Core Screens
- [ ] Cases list: Data Table (filters/sort/pagination/row actions)
- [ ] Case detail: Tabs (Summary/Exceptions/CP/Documents/Dossier/Audit)
- [ ] Exceptions review: details panel + evidence linking + waive/resolution flows
- [ ] CP list: due date/status + evidence required

### Phase 3 — Document Viewer (UI only)
- [ ] Thumbnails + main viewer + OCR text panel
- [ ] "Add as Evidence" action from selection/snippet
- [ ] Evidence deep-linking to page

### Phase 4 — Governance UX
- [ ] RBAC-aware UI controls
- [ ] Audit log table with filters and diff preview

### Phase 5 — Polish
- [ ] Loading/Empty/Error states everywhere
- [ ] Toast notifications for actions
- [ ] Consistent typography and spacing
- [ ] Export Bank Pack action states
