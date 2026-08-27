# CDS Figma Frontend Prototype Design

## Status

Approved direction: build a separate, clickable Figma prototype before moving the design into the CDS repository.

## Objective

Create a complete front-end walkthrough for Covenant Diligence Systems (CDS) in Figma. The prototype should let a law-firm Reviewer understand the daily workflow from matter intake through review, decision, and bank-pack issuance without requiring a backend.

The prototype is a visual and interaction artifact. It uses believable static matter data and Figma prototype actions. It does not replace API behavior or claim legal conclusions.

## Product surface

The file will be a separate Figma design file named `CDS — Frontend Prototype`, leaving the existing CDS reference file unchanged. It will contain a small foundations section, reusable UI components, and five connected product surfaces:

1. **Entry / matter queue**
   - Queue groups: Needs me, Blocked, Waiting, Ready, Aging.
   - Matter rows show matter name, facility context, owner, current stage, and next action.
   - Primary action opens the selected matter in Command Centre.

2. **Command Centre**
   - Matter summary and title-chain progress.
   - Dossier confidence and proposed-versus-confirmed distinction.
   - Exception and CP counts with risk states.
   - Recent activity and next action.
   - Navigation into the Matter Workspace and Review & Decision.

3. **Matter Workspace**
   - File / Evidence / Work navigation.
   - Document inventory for deed, mutation, fard/jamabandi, NOC, and annexures.
   - OCR state shown as Proposed until a human confirms it.
   - Evidence row opens a right-side Evidence Peek overlay.
   - Work view exposes the computed next action.

4. **Review & Decision**
   - Exception table with severity, status, and concise finding language.
   - Evidence Peek overlay for the selected exception.
   - Actions: Mark resolved, Propose waiver, Return for review.
   - Approval gate separates maker review from approver decision.
   - Bank pack panel distinguishes Draft / Not approved from Issued.

5. **Bank Pack**
   - Draft pack contents: executive summary, exceptions, CPs, annexures, evidence references.
   - Review checklist and version metadata.
   - Review & issue action leads to an issued confirmation state.
   - Issued state is versioned; a failed pack is never labelled clearance.

## Prototype interactions

All primary buttons and meaningful rows will have a visible result in Figma:

- Queue matter row or `Open matter` → Command Centre.
- Command Centre `Continue review` → Matter Workspace.
- Matter Workspace tab changes → File, Evidence, and Work states.
- Evidence row → Evidence Peek overlay.
- Evidence Peek close → return to the same underlying state.
- Exception row → selected exception state in Review & Decision.
- `Mark resolved` → resolved status state with updated counts.
- `Propose waiver` → waiver-proposed state with a review-needed label.
- `Approve matter` → approval confirmation state.
- `Return for review` → returned state with next action updated.
- `Review & issue` → Bank Pack review state.
- `Issue pack` → versioned issued state.
- Back and breadcrumb actions → previous surface.

Interactions should use Figma navigation, overlays, and modest smart-animate transitions. Prototype actions should be named in a way that makes the intended eventual implementation clear.

## Visual system

The system preserves the existing CDS night-stamp-office identity:

- Canvas: near-black, with charcoal surfaces and a quiet border hierarchy.
- Accent: restrained signal red for irreversible or primary actions.
- Risk: amber for open/high-attention states; green for resolved/ready states; blue for low/informational states.
- Typography: Source Serif 4 Display for major editorial headings; Switzer for operational UI; Array for matter IDs, timestamps, and instrument metadata.
- Layout: dense but calm desktop workspace, hairline rules, no ornamental gradients, glass panels, neon, giant rounded cards, or generic SaaS KPI tiles.
- Components: sidebar, queue rows, status labels, tabs with an underline indicator, evidence peek, exception rows, approval gate, bank-pack panel, buttons, and breadcrumbs.

## Data model for the prototype

Use one fictional matter and a small set of supporting records so the states remain coherent:

- Matter: `ABC Textiles · secured facility review`.
- Documents: sale deed, mutation no. 4481, fard/jamabandi, society NOC, board resolution, annexure set.
- Exceptions: mutation ownership mismatch (High / Open), society NOC expiry unclear (Medium / Open), updated Fard required (High / Pending docs), board resolution certified copy (Low / Resolved).
- Conditions Precedent: two pending and two resolved.
- Bank pack: Draft v0.3 → Issued v0.4 after review.

No testimonials, customer logos, benchmarks, bank names, or unsupported legal claims will be added.

## Build sequence

1. Inspect the existing file and confirm pages, components, and available fonts.
2. Create the separate Figma file and establish foundations/tokens.
3. Build reusable components and the Entry / Command Centre surfaces.
4. Add Matter Workspace and Evidence Peek states.
5. Add Review & Decision and Bank Pack states.
6. Wire prototype interactions.
7. Validate structure, screenshots, labels, and click-through paths.

Each Figma write is incremental, returns created/mutated node IDs, and is visually checked before the next build step.

## Motion handoff

Figma prototype transitions are the reviewable approximation. When the design is later moved into the CDS repo, the implementation will use GSAP with explicit plugin registration. Flip is intended for tab and layout continuity; SplitText is reserved for the single entry reveal if needed; ScrollTo/Observer/Draggable are only added when a concrete interaction requires them. No development-only GSDevTools will ship.

## Accessibility and product truth

Prototype labels will remain explicit and operational. Proposed OCR values will never be presented as confirmed facts. Maker/checker separation, waiver eligibility, and pack approval will be expressed in the UI copy even though the Figma artifact cannot enforce backend permissions.

## Out of scope

- Moving the design into the CDS repository.
- Backend/API wiring.
- Real authentication, file uploads, OCR, exports, or persistence.
- Marketing landing pages.
- Bilingual UI.
- Production accessibility certification.
