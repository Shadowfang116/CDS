# CDS Figma Frontend Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a separate, clickable Figma prototype that demonstrates the CDS workflow from matter queue through issued bank pack.

**Architecture:** Use Figma MCP `use_figma` in incremental calls against a new design file. Build a small foundations/component layer first, then compose five desktop surfaces and explicit state frames for overlays and decisions. Use Figma prototype navigation and overlays for interaction; defer production GSAP code to the later CDS-repo phase.

**Tech Stack:** Figma Design API via `mcp__codex_apps__figma_use_figma`, Figma prototype actions, Source Serif 4 Display, Switzer, Array, CDS night-stamp-office tokens, Impeccable operate-mode guidance, GSAP plugin handoff notes.

**Spec:** `docs/superpowers/specs/2026-08-24-cds-figma-frontend-prototype-design.md`

## Global Constraints

- Preserve the CDS name and Pakistan property-diligence identity.
- Proposed OCR values must remain visibly provisional until confirmed.
- Exception and CP remain distinct objects.
- Draft bank pack must be labelled not approved; issued pack must be versioned.
- No gradients, glass, neon, ornamental dashboard tiles, unsupported claims, logos, testimonials, or bank names.
- Every `use_figma` write must load `figma-use`, return all created/mutated node IDs, and be validated before the next write.
- Use `await figma.setCurrentPageAsync(page)` for page changes and load fonts before text mutation.

---

### Task 1: Discover the active Figma context

**Files:**
- Read: `docs/superpowers/specs/2026-08-24-cds-figma-frontend-prototype-design.md`
- Read: `frontend/DESIGN.md`
- Tool: Figma metadata/context inspection

**Interfaces:**
- Produces: authenticated Figma plan key, source file context if available, and confirmed font/style names for later calls.

- [ ] Inspect the available Figma file context and plans without mutating the canvas.
- [ ] Confirm Source Serif 4 Display, Switzer, and Array style names using the Figma font list or existing file context.
- [ ] Record the returned plan key and new-file prerequisites for Task 2.

### Task 2: Create the separate prototype file

**Files:**
- Tool: `mcp__codex_apps__figma_create_new_file`

**Interfaces:**
- Consumes: plan key from Task 1.
- Produces: `fileKey` and editable Figma URL for all later tasks.

- [ ] Create a design file named `CDS — Frontend Prototype` in the user’s draft space.
- [ ] Verify the returned file key and URL.
- [ ] Keep the existing CDS reference file untouched.

### Task 3: Establish foundations and reusable components

**Files:**
- Figma pages/sections: `00 — Foundations`, `01 — Components`
- Tool: `mcp__codex_apps__figma_use_figma`

**Interfaces:**
- Produces: token reference, button variants, status labels, queue row, tabs, evidence peek shell, exception row, approval gate, and bank-pack panel node IDs.

- [ ] Create the foundations frame with near-black canvas, charcoal surfaces, hairline rules, signal red, amber, green, blue, and the three type roles.
- [ ] Create reusable components with descriptions that state their operational purpose.
- [ ] Build button, status, tab, queue row, evidence peek, exception row, approval gate, and bank-pack panel components.
- [ ] Validate component hierarchy and take a screenshot of the foundations/component sections.

### Task 4: Compose Entry / matter queue and Command Centre

**Files:**
- Figma page: `02 — Product Surfaces`
- Frames: `Entry — Matter Queue`, `Command Centre — ABC Textiles`
- Tool: `mcp__codex_apps__figma_use_figma`

**Interfaces:**
- Consumes: component IDs from Task 3.
- Produces: frame IDs for Entry and Command Centre, plus navigation targets.

- [ ] Build queue groups Needs me, Blocked, Waiting, Ready, and Aging using the fictional matter data.
- [ ] Add the selected matter row and `Open matter` action.
- [ ] Build Command Centre with title-chain progress, dossier confidence, exception/CP counts, recent activity, and next action.
- [ ] Add `Continue review`, Review & Decision, and back/breadcrumb targets.
- [ ] Validate desktop layout and text legibility with screenshots.

### Task 5: Compose Matter Workspace and Evidence Peek states

**Files:**
- Figma page: `02 — Product Surfaces`
- Frames: `Matter — File`, `Matter — Evidence`, `Matter — Work`, `Evidence Peek — Mutation 4481`
- Tool: `mcp__codex_apps__figma_use_figma`

**Interfaces:**
- Consumes: component IDs from Task 3 and Command Centre target from Task 4.
- Produces: Matter Workspace frame IDs and Evidence Peek overlay target.

- [ ] Build File, Evidence, and Work tab states with a hairline active indicator.
- [ ] Add document inventory for sale deed, mutation, fard/jamabandi, NOC, board resolution, and annexures.
- [ ] Show OCR values as Proposed with a human confirmation affordance.
- [ ] Build the right-side Evidence Peek overlay with mutation no. 4481, page reference, snippet, and close action.
- [ ] Validate the overlay alignment and underlying-state continuity.

### Task 6: Compose Review & Decision and Bank Pack

**Files:**
- Figma page: `02 — Product Surfaces`
- Frames: `Review — Exceptions & Decision`, `Review — Resolved`, `Review — Waiver Proposed`, `Bank Pack — Draft`, `Bank Pack — Issued`
- Tool: `mcp__codex_apps__figma_use_figma`

**Interfaces:**
- Consumes: component IDs from Task 3 and Matter Workspace target from Task 5.
- Produces: review, decision, and pack state frame IDs.

- [ ] Build the exception table with the four specified exception records and severity/status treatments.
- [ ] Add Evidence Peek, Mark resolved, Propose waiver, Approve matter, and Return for review states.
- [ ] Build approval gate with maker/checker language and separate approval action.
- [ ] Build Draft v0.3 bank pack with contents, checklist, and Not approved label.
- [ ] Build Issued v0.4 state and make clear it is versioned, not a legal clearance.
- [ ] Validate all states with screenshots.

### Task 7: Wire prototype interactions

**Files:**
- Figma prototype interactions on all frames from Tasks 4–6
- Tool: `mcp__codex_apps__figma_use_figma`

**Interfaces:**
- Consumes: all frame IDs from Tasks 4–6.
- Produces: complete click-through prototype starting at Entry / matter queue.

- [ ] Link queue row/Open matter to Command Centre.
- [ ] Link Continue review to Matter Workspace and tabs to each workspace state.
- [ ] Link evidence row to the Evidence Peek overlay and close back to the same state.
- [ ] Link exception row and decision buttons to resolved, waiver, approval, and returned states.
- [ ] Link Review & issue to Bank Pack Draft and Issue pack to Bank Pack Issued.
- [ ] Add back and breadcrumb actions for each surface.
- [ ] Use modest smart-animate/navigation transitions with no decorative animation loops.

### Task 8: Validate and hand off

**Files:**
- Read: all prototype frames and interactions
- Output: final Figma URL and walkthrough notes

- [ ] Run a complete click-through from Entry → Command Centre → Matter → Evidence Peek → Review → Bank Pack → Issued.
- [ ] Inspect screenshots for cropped text, overlap, contrast, and incorrect status labels.
- [ ] Confirm every primary button has a visible target or overlay.
- [ ] Record the final Figma URL, starting frame, known Figma-only limitations, and GSAP handoff notes.

## Self-review

- Spec coverage: all five surfaces, static data, interaction states, visual rules, motion handoff, and out-of-scope boundaries are mapped to Tasks 3–8.
- Placeholder scan: no TBD/TODO/FIXME placeholders are used.
- Type consistency: later tasks consume only the frame/component/file IDs explicitly produced by earlier tasks.
