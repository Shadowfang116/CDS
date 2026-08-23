# CDS design sources

Inspected live on 16 Aug 2026. CDS visual contract is sovereign. External libraries are reference sources, not design systems.

**Rule:** a sourced pattern may be used only where it improves reviewer speed, evidence comprehension, navigation, spatial continuity, interaction polish, or the cinematic identity of Login / Overview.

**Objective:** adapt unusually good interactions until they look and behave as CDS. Not: put Aceternity or 21st.dev components into the app.

**Existing primitives (inspect first):** `@radix-ui/react-dialog`, `@radix-ui/react-tabs`, custom `drawer.tsx` (Escape, focus trap, 180ms), `sidebar.tsx` (collapsible), `table.tsx` + `@tanstack/react-table`, `gsap` + `Flip` + `useGSAP` + `SplitText` in `lib/gsap.ts`, `motion` already in `package.json` but **not used for new CDS motion** (GSAP/CSS is the production baseline).

**Rubric:** workflow fit 30% · usability/a11y 25% · maintainability 20% · motion quality 15% · visual originality potential 10%.

---

## Decision table

| CDS need | Source | Candidate | Decision | Why | Licence | Dependencies | Adaptation | Score |
|----------|--------|-----------|----------|-----|---------|--------------|------------|-------|
| Evidence Peek | CDS | `components/ui/drawer.tsx` | **ADAPT** | Finding stays; panel from right; Esc; focus restore; 180ms already. Best workflow fit. | Internal | none | Restyle to tokens; widen for document; compose with splitter. Production name: `cds/evidence-peek.tsx`. | 88 |
| Evidence Peek | 21st.dev / shadcn | Sheet (`@radix-ui/react-dialog` side panel) | **REJECT** (as second primitive) | Same job as existing drawer. Dialog-as-sheet would duplicate focus/Esc. Improve drawer instead. | MIT (Radix) | already have dialog | — | 72 |
| Evidence Peek | 21st.dev / shadcn | Drawer (Vaul bottom sheet) | **REJECT** | Mobile bottom-sheet. Wrong for a desktop legal file. | MIT (vaul) | vaul | — | 38 |
| Evidence Peek / split | 21st.dev / shadcn | Resizable (`react-resizable-panels`) | **ADOPT** behaviour | Keyboard-accessible split is the operational foundation for finding + page. MIT, small, no visual theme. | MIT | **new:** `react-resizable-panels` | Thin CDS wrapper `components/ui/resizable.tsx`. Tokens only. Used inside Evidence Peek. Justified new dep. | 86 |
| Document inspect | Aceternity | Lens | **REJECT** Phase 0 | Pointer-following magnifier. Weak keyboard story. Marketing demo (Vision Pro). Later optional `cds/evidence-lens.tsx` if OCR needs region inspect, with keyboard equivalent. | MIT (free registry copy) | Motion | Discard all styling and mouse-only follow. | 41 |
| OCR compare | Aceternity | Compare | **REJECT** Phase 0 | Needs two images; Compare CLI also pulls **Sparkles**. No Phase 0 backend for original↔processed pairs. Revisit if OCR already exposes both rasters. | MIT (free) | Motion + Sparkles | — | 28 |
| Matter nav | Aceternity | Animated Tabs | **REIMPLEMENT** | Borrow **shared moving indicator / spatial continuity only**. Stock is a SaaS pill with stacked fade content. CDS must look like file indexing. | MIT (free) | Motion | Rebuild on Radix Tabs + GSAP Flip. Hairline underline, not pill. `cds/matter-nav.tsx`. Discard FadeInDiv, rounded pill, hover-stack. | 74 |
| Matter nav | CDS | `components/ui/tabs.tsx` | **ADAPT** | Already Radix, keyboard, ARIA. Currently zinc/rgba chrome. Restyle + Flip indicator. | MIT (Radix) | existing | Tokens; no `rounded-md` tray. | 80 |
| Command palette | 21st.dev / Origin | Command Dialog (cmdk) | **DESIGN NOW / SHIP LATER** | Improves go-to matter later. Not required to freeze Login/Overview/Matter. Phase 0B: `/` filter on lists only. | MIT (cmdk / shadcn) | cmdk later | `cds/command-palette.tsx` when shipped. No Origin visual. | 70 |
| Command palette | 21st.dev / shadcn | Command | **REJECT** Phase 0B ship | Duplicate of above. | MIT | cmdk | — | 68 |
| Tables | CDS | `table.tsx` + TanStack Table | **ADAPT** | Already the table stack. Restyle to CDS grammar. | MIT | existing | 44–48px rows, no vertical borders, hairline rules, tabular nums, sticky head, status via type/rule. | 90 |
| Tables | 21st.dev Origin UI | Table with row selection | **REJECT copy** | **origin-space/originui now AGPL-3.0** (coss.com/ui). Do not copy Origin/coss source into CDS. Borrow ideas only (right-align numbers, transparent footer). | AGPL-3.0 (current repo) | — | Ideas only. No source. | — |
| Collapsible sidebar / focus mode | CDS | `sidebar.tsx` | **ADAPT** | Already collapsible (72px icon / expanded). Matter focus mode = collapse on matter route. | Internal / Radix slot | existing | Quiet collapse; no dashboard chrome. Width tokens 72 / 220–240. | 84 |
| Collapsible sidebar | 21st.dev / shadcn | Sidebar | **REJECT** | Would replace a working primitive with another author's visual system. | MIT | — | — | 55 |
| Dialog / confirm | CDS | `dialog.tsx` (Radix) | **ADAPT** | Waiver, approve/reject, destructive. Routine dialogs are not cinematic. | MIT | existing | Tokens; 180ms opacity; focus-visible. | 82 |
| File upload | CDS | `DocumentsPanel.tsx` | **ADAPT** | Upload API and drag/drop already exist. Improve hierarchy, progress, errors. No illustrated drop card. | Internal | existing | Compact drop target; filename; processing rail. | 85 |
| File upload | 21st.dev | illustrated upload cards | **REJECT** | Giant icon cards. Conflicts with no-card-by-default. | varies | — | — | 22 |
| Audit / lifecycle | Aceternity | Timeline | **REJECT** | Sticky year headers, scroll beam, content cards. Marketing changelog. | MIT (free) | Motion | — | 30 |
| Audit / lifecycle | Michele Du | Bolster / Signal hierarchy | **ADAPT idea** | Insight → lifecycle → underlying data → action. Maps to finding → evidence state → page → action. No assets copied. | Inspiration only | none | `cds/lifecycle-rail.tsx` hairline rail. Audit stays time/actor/action/object. | 78 |
| Process state | Aceternity | Multi Step Loader | **REJECT** as loader | Overlay loop is forbidden as primary loading. | MIT (free) | Motion | Idea only: compact rail UPLOAD→SPLIT→OCR→CLASSIFY→EXTRACT if document status already exists (`DocumentViewer` stage map). Skeletons remain primary. | 35 |
| Login / Overview reveal | Aceternity | Text Generate Effect | **REJECT** | Word-by-word blur fade is AI-slop and delays operational copy. | MIT (free) | Motion | — | 18 |
| Login / Overview reveal | CDS GSAP | SplitText / opacity | **REIMPLEMENT** | One atmospheric treatment. GSAP already registered. | Internal | existing GSAP | Login brand fade; Overview title once. `prefers-reduced-motion` = instant. Never operational body copy. | 76 |
| Overview composition | Michele Du | Signal / Bolster dashboard | **ADAPT idea** | Macro insight then underlying events; numbers as designed information; no cards. Translate idea, not appearance. | Inspiration only | none | `cds/next-matter.tsx`, `cds/aging-strip.tsx` metadata strip. | 81 |
| Sparkles / aurora / 3D / glare / vortex / beams / globe / docks / parallax / infinite cards / shaders | Aceternity | (rejection set) | **REJECT** | Conflicts with night stamp office, no glass, no orbs, no gradients, no decorative motion. | — | GPU loops | No exceptions this round. | 0 |
| Glass / neon / purple SaaS / 8-bit / gaming / physics / bento / glowing cards | 21st.dev | (rejection set) | **REJECT** | Wrong institution. Do not mix authors' visual systems. | — | — | Behaviour only if ever revisited. | 0 |

---

## Phase 0B approved selection (budget)

| Screen | Externally-derived family | CDS component | What is reused | What is discarded |
|--------|---------------------------|---------------|----------------|-------------------|
| Login | 1 atmospheric treatment | GSAP opacity on brand / form | Pacing of a single reveal | Aceternity text-generate, grain animation at high FPS, any CDN font |
| Overview | 1 hero | `cds/next-matter.tsx` | Michele Du: large numbers + metadata as composition | KPI cards, word-by-word text, sparkles |
| Overview | 1 list/rail | `cds/aging-strip.tsx` | Horizontal scan of aging matters; Michele Du strip | Card grid, charts |
| Matter | Evidence Peek (signature) | `cds/evidence-peek.tsx` | CDS drawer behaviour + resizable split | Vaul, Lens, Sheet duplicate, glass |
| Matter | 1 nav transition | `cds/matter-nav.tsx` | Aceternity **indicator motion principle** via GSAP Flip | Pill tabs, FadeInDiv, Motion |
| Matter | 1 document interaction | Evidence Peek page panel + existing `DocumentViewer` | Page + snippet; optional later lens | Compare, Sparkles |

Also original (not sourced): `cds/case-truth-bar.tsx`, `cds/lifecycle-rail.tsx`.

**Not in Phase 0B:** command palette, evidence-lens, document-compare, global queue restyle, secondary surfaces.

---

## Licence notes

- **Aceternity free registry components** (Lens, Compare, Tabs, Timeline, Multi Step Loader, Text Generate, Sparkles): copy-paste MIT-style registry items. CDS will **not** vendor their Motion source; behaviour is reimplemented in GSAP where approved. Pro/All-Access blocks are **not** used.
- **react-resizable-panels:** MIT (Brian Vaughn). Only new runtime dependency justified in Phase 0B.
- **Origin UI / coss.com/ui:** current GitHub licence **AGPL-3.0**. **Do not copy source.** Pattern ideas only.
- **Michele Du / Bolster / Signal:** inspiration. No proprietary assets, layouts, or code.
- **Array + Switzer (Fontshare / ITF Free Font License):** commercial and app embedding permitted; self-host WOFF2; do not resell font files; no Fontshare CDN at runtime. Confirm the per-family licence file at download.

---

## Institutional / originality tests

- Would this still feel appropriate while an Approver decides a PKR 500 million secured facility? Lens, Sparkles, Compare autoplay, Multi Step Loader overlay, Text Generate: **no**.
- If the source name sat beside the component, would it be obvious? Stock Aceternity tabs / timeline / lens: **yes** — therefore REIMPLEMENT or REJECT, never ADOPT styled.

---

## Inspected URLs

- https://ui.aceternity.com/components/lens
- https://ui.aceternity.com/components/compare
- https://ui.aceternity.com/components/tabs
- https://ui.aceternity.com/components/timeline
- https://ui.aceternity.com/components/multi-step-loader
- https://ui.aceternity.com/components/text-generate-effect
- https://ui.aceternity.com/components/sparkles
- https://21st.dev/@shadcn/components/sheet
- https://21st.dev/@shadcn/components/resizable
- https://21st.dev/@shadcn/components/drawer
- https://21st.dev/@shadcn/components/command
- https://21st.dev/@originui/components/command
- https://21st.dev/@originui/components/table/table-with-row-selection
- https://ui.shadcn.com/docs/components/resizable
- https://micheledu.com/project/signal
- https://micheledu.com/case-study
- https://github.com/origin-space/originui (AGPL-3.0)
- https://www.fontshare.com/licenses/itf-ffl
