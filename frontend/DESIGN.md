---
version: alpha
name: CDS Threaded Registry
description: A premium evidence-led operating system for Pakistan property diligence.
colors:
  primary: "#183F37"
  primary-hover: "#143831"
  primary-pressed: "#102F29"
  on-primary: "#F8FAF7"
  canvas: "#E7ECE8"
  surface: "#F7F8F5"
  surface-sunken: "#DCE3DE"
  surface-ink: "#10231F"
  ink: "#12201C"
  body: "#3E4B45"
  mute: "#58665F"
  disabled: "#506059"
  hairline: "#C4CEC7"
  hairline-strong: "#94A39A"
  thread: "#705017"
  thread-soft: "#EFE4CE"
  proposed: "#315F8D"
  proposed-soft: "#DFEAF4"
  danger: "#8F3535"
  danger-hover: "#792D2D"
  danger-soft: "#F3DEDD"
  success: "#245E49"
  success-soft: "#DCECE4"
  warning: "#765516"
  warning-soft: "#F2E7CC"
  focus-on-light: "#175FC2"
  focus-on-dark: "#76B7FF"
typography:
  display-xl:
    fontFamily: "General Sans, sans-serif"
    fontSize: 56px
    fontWeight: 520
    lineHeight: 1.02
    letterSpacing: -0.035em
    fontFeature: '"kern", "liga", "ss01"'
  display-lg:
    fontFamily: "General Sans, sans-serif"
    fontSize: 40px
    fontWeight: 520
    lineHeight: 1.08
    letterSpacing: -0.025em
    fontFeature: '"kern", "liga", "ss01"'
  heading-xl:
    fontFamily: "General Sans, sans-serif"
    fontSize: 28px
    fontWeight: 560
    lineHeight: 1.15
    letterSpacing: -0.018em
  heading-lg:
    fontFamily: "General Sans, sans-serif"
    fontSize: 22px
    fontWeight: 560
    lineHeight: 1.2
    letterSpacing: -0.012em
  heading-md:
    fontFamily: "General Sans, sans-serif"
    fontSize: 18px
    fontWeight: 560
    lineHeight: 1.3
    letterSpacing: -0.008em
  body-lg:
    fontFamily: "General Sans, sans-serif"
    fontSize: 17px
    fontWeight: 430
    lineHeight: 1.55
    letterSpacing: -0.005em
  body-md:
    fontFamily: "General Sans, sans-serif"
    fontSize: 15px
    fontWeight: 430
    lineHeight: 1.5
    letterSpacing: -0.003em
  body-strong:
    fontFamily: "General Sans, sans-serif"
    fontSize: 15px
    fontWeight: 580
    lineHeight: 1.4
    letterSpacing: -0.003em
  body-sm:
    fontFamily: "General Sans, sans-serif"
    fontSize: 13px
    fontWeight: 430
    lineHeight: 1.45
    letterSpacing: 0
  label:
    fontFamily: "General Sans, sans-serif"
    fontSize: 12px
    fontWeight: 620
    lineHeight: 1.25
    letterSpacing: 0.04em
  caption:
    fontFamily: "General Sans, sans-serif"
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: 0.025em
  data:
    fontFamily: "Fragment Mono, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: -0.02em
  source-urdu:
    fontFamily: "Noto Nastaliq Urdu, serif"
    fontSize: 17px
    fontWeight: 500
    lineHeight: 2
    letterSpacing: 0
spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 32px
  xxxl: 48px
  section: 72px
rounded:
  none: 0px
  xs: 3px
  sm: 5px
  md: 8px
  lg: 12px
  full: 9999px
components:
  app-shell:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.none}"
    padding: 0px
  navigation-rail:
    backgroundColor: "{colors.surface-ink}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.none}"
    width: 248px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-primary-pressed:
    backgroundColor: "{colors.primary-pressed}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-secondary:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-secondary-hover:
    backgroundColor: "{colors.hairline}"
    textColor: "{colors.ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  focus-indicator-on-light:
    backgroundColor: "{colors.focus-on-light}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.none}"
    size: 2px
  focus-indicator-on-dark:
    backgroundColor: "{colors.focus-on-dark}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    size: 2px
  button-disabled:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.disabled}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
    height: 40px
  status-proposed:
    backgroundColor: "{colors.proposed-soft}"
    textColor: "{colors.proposed}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  status-open:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  status-failed:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  status-ready:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  status-pending:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.warning}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  evidence-thread:
    backgroundColor: "{colors.thread}"
    textColor: "{colors.on-primary}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    size: 8px
  selected-row:
    backgroundColor: "{colors.thread-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 10px 12px
  queue-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    typography: "{typography.body-md}"
    rounded: "{rounded.none}"
    padding: 16px 20px
    height: 68px
  search-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 10px 12px
    height: 40px
  metadata-label:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.mute}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: 0px
  object-exception:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  object-cp:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: 4px 7px
  source-urdu:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.source-urdu}"
    rounded: "{rounded.none}"
    padding: 0px
  evidence-peek:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: 24px
    width: 440px
  divider:
    backgroundColor: "{colors.hairline}"
    rounded: "{rounded.none}"
    height: 1px
  divider-strong:
    backgroundColor: "{colors.hairline-strong}"
    rounded: "{rounded.none}"
    height: 1px
---

# CDS Threaded Registry

## Overview

**Threaded Registry** is a new visual system for Covenant Diligence Systems (CDS). It is deliberately independent of the current frontend. Its governing idea is simple: every legal conclusion must remain visibly connected to the evidence that supports it.

The interface behaves like a finely made registry assembled with a continuous evidence thread. Matter stages, document sources, extracted facts, Exceptions, Conditions Precedent (CPs), decisions, and bank-pack pages sit on one traceable path. The thread is functional, not decorative: it marks provenance, indicates what remains provisional, and lets a Reviewer move from a finding back to its source without losing place.

The physical scene is a Reviewer at a desktop under mixed office light, moving quickly between scanned deeds, extracted fields, and approval states. A cool mineral canvas reduces glare; a deep registry-green navigation plane anchors the workspace; warm brass identifies the active evidence path. The result should feel composed and premium without sacrificing the density expected from a bank-grade operating tool.

### Design thesis

- **Premium means precision:** disciplined alignment, excellent typography, carefully tuned density, and authored transitions.
- **Evidence is spatial:** provenance should be visible in layout, not hidden in metadata or a modal.
- **Calm is not empty:** operational screens may be dense, but hierarchy must make the next action obvious.
- **Human confirmation is the visual center:** OCR is a reading aid. Proposed data never looks equivalent to confirmed data.
- **Product language stays legal:** matter, title chain, dossier, Exception, CP, waiver, annexure, and bank pack.

### Reference synthesis

The Awwwards research covered legal, fintech, and real-estate collections. The useful traits were architectural whitespace, restrained material palettes, confident typography, and large-scale composition. CDS takes those craft standards but rejects the category habits visible in many samples: luxury-property photography, generic financial gradients, oversized marketing type, and ornamental legal symbolism. The operational product must prove its quality through information design.

### Signature moment

Opening a matter draws one brass evidence thread from the selected queue row into the title-chain rail. As the workspace settles, nodes resolve into **Source**, **Proposed**, **Confirmed**, **Exception**, and **Decision** states. Motion lasts 420–560ms and then stops completely. `prefers-reduced-motion` shows the final connected state immediately.

## Colors

The palette is a **restrained mineral system**: cool pale working surfaces, deep green-black structure, and one warm brass provenance accent. Semantic colors label state and never replace text or icons.

### Core surfaces

- **Registry Green** (`{colors.primary}`): primary action, active navigation, and confirmed structural emphasis.
- **Pressed Green** (`{colors.primary-pressed}`): pressed primary action only.
- **Mineral Canvas** (`{colors.canvas}`): application background; cool enough to distinguish it from paper-themed legal products.
- **Ledger Surface** (`{colors.surface}`): document panes, rows, controls, and reading surfaces.
- **Recessed Mineral** (`{colors.surface-sunken}`): inactive wells, disabled controls, and grouped secondary regions.
- **Ink Plane** (`{colors.surface-ink}`): permanent desktop navigation rail and focused review mode.
- **Evidence Brass** (`{colors.thread}`): the active provenance path, selected title-chain node, and source-to-fact connectors.
- **Evidence Brass Soft** (`{colors.thread-soft}`): selected rows and connected evidence regions.

### Text and rules

- **Ink** (`{colors.ink}`): headings and primary values.
- **Body** (`{colors.body}`): default prose and row copy.
- **Mute** (`{colors.mute}`): supporting metadata that still meets body contrast requirements.
- **Disabled** (`{colors.disabled}`): unavailable controls only; never use it for ordinary metadata.
- **Hairline** (`{colors.hairline}`): table rules and low-emphasis boundaries.
- **Hairline Strong** (`{colors.hairline-strong}`): pane divisions, sticky boundaries, and focused field edges.

### State colors

- **Proposed Blue** (`{colors.proposed}` / `{colors.proposed-soft}`): machine-extracted values awaiting human confirmation.
- **Exception Red** (`{colors.danger}` / `{colors.danger-soft}`): blocking, failed, rejected, or destructive states.
- **Verified Green** (`{colors.success}` / `{colors.success-soft}`): human-confirmed, resolved, ready, or issued states.
- **Pending Ochre** (`{colors.warning}` / `{colors.warning-soft}`): waiting on documents, approvals, or third parties.
- **Focus on Light** (`{colors.focus-on-light}`): keyboard focus ring on canvas, ledger, and recessed mineral surfaces.
- **Focus on Dark** (`{colors.focus-on-dark}`): keyboard focus ring on the registry-green navigation plane.

### Color rules

1. Brass always means **evidence connection or current chain position**. It is not a general-purpose brand accent.
2. Red never marks a primary navigation item or ordinary CTA.
3. State meaning always includes a word and, where useful, an icon. Color alone is insufficient.
4. Large surfaces remain mineral, ledger, or ink. Semantic colors stay compact.
5. Avoid gradients. Material depth comes from tone, rules, and pane overlap.

## Typography

### Families

**General Sans Variable** is the primary face. Its tailored grotesk construction feels precise without looking generic or clinical. Load weights 400–650 and use optical interpolation rather than separate static files. Self-host **Manrope Variable** as the metrically resilient fallback; map unsupported intermediate weights to the nearest available weight.

**Fragment Mono** is restricted to content that is genuinely machine-identifying or measured: matter IDs, document hashes, version numbers, timestamps, page coordinates, and audit event IDs. It must never be used for navigation, headings, buttons, or decorative “technical” atmosphere.

Fallbacks:

- General Sans → `Manrope Variable`, `system-ui`, `sans-serif`
- Fragment Mono → `ui-monospace`, `monospace`

### Hierarchy

- `{typography.display-xl}`: entry and empty-state statements only; never a dashboard metric.
- `{typography.display-lg}`: workspace title on low-density overview surfaces.
- `{typography.heading-xl}`: matter title and major decision heading.
- `{typography.heading-lg}`: pane heading and bank-pack section.
- `{typography.heading-md}`: grouped row heading and evidence title.
- `{typography.body-lg}`: explanatory copy and consequential confirmation text.
- `{typography.body-md}`: default operational copy.
- `{typography.body-strong}`: actions, active tabs, and important values.
- `{typography.body-sm}`: metadata and supporting explanations.
- `{typography.label}`: compact state and column labels; use title case, not all caps.
- `{typography.caption}`: tertiary metadata.
- `{typography.data}`: identifiers and measurements only.

### Typesetting rules

- Use tabular numerals for counts, dates, page numbers, and versions.
- Keep body text between 55 and 72 characters per line.
- Use sentence case everywhere except legal acronyms such as CP, NOC, and OCR.
- Do not use eyebrow text above headings.
- Headings describe the task or object: “Review title chain,” not “Overview.”
- Use weight and spacing before introducing another text size.
- Urdu source text uses `{typography.source-urdu}` inside document and evidence panes only. Preserve right-to-left direction and never force Urdu into General Sans.

## Layout

### Structural model

Desktop uses a five-region workspace:

1. **Navigation rail** — 248px fixed, deep registry green.
2. **Matter rail** — 272–320px, title-chain position and file navigation.
3. **Primary work surface** — fluid, minimum 560px.
4. **Evidence Peek** — 440px contextual pane, persistent when space allows.
5. **Decision dock** — 56–72px sticky bottom band for the computed next action.

The regions share baselines and are separated by rules, not floating cards. A surface should feel assembled like one instrument, not a dashboard made of independent widgets.

### Grid

- Desktop content grid: 12 columns with 24px gutters.
- Maximum shell width: none; the application is full viewport.
- Readable overview width: 1440px max with 32–48px outer gutters.
- Dense table row: 44–52px.
- Standard queue row: 68px.
- Work-surface inset: 24px desktop, 20px compact desktop, 16px tablet.
- Major overview separation: `{spacing.section}`.
- Pane heading to content: `{spacing.xl}`.
- Related control gap: `{spacing.sm}`.

### Density modes

CDS supports one visual identity with two deliberate densities:

- **Review density:** 44px rows, compact labels, maximum visible evidence. Default for Workspace, Exceptions, CPs, and Audit.
- **Overview density:** 60–72px rows, more explanatory copy. Default for Inbox, Command Centre, and Bank Pack.

Density is selected by route, never exposed as an arbitrary user preference.

### Evidence-thread geometry

- The primary thread is 1px at rest and 2px only during active tracing.
- Nodes are 8px; the selected node expands to 12px with a 2px ledger-surface center.
- Connectors use orthogonal paths with 8px elbows. Curves are reserved for transitions between panes.
- Every connector terminates at a labelled object. Decorative loose lines are prohibited.
- When multiple sources support one finding, connectors merge into a short 2px trunk before the finding.
- On scroll, the active connector may pin to the pane edge with a labelled continuation marker.

### Responsive behavior

| Breakpoint | Width | Adaptation |
|---|---:|---|
| Wide desktop | 1600px+ | All five regions visible; Evidence Peek stays persistent. |
| Desktop | 1280–1599px | Matter rail narrows; Evidence Peek overlays the right 38% without hiding the decision dock. |
| Compact desktop | 1024–1279px | Navigation rail collapses to 72px; matter rail becomes a switchable pane. |
| Tablet | 768–1023px | One primary pane plus a bottom evidence sheet; title chain becomes a horizontal step rail. |
| Mobile | 390–767px | Triage and approval only; document review uses sequential Source → Extracted → Decision steps. |
| Narrow mobile | below 390px | Keep one action per row, abbreviate metadata, never abbreviate legal state labels. |

Mobile is a supported companion, not a compressed desktop. High-stakes source comparison should clearly recommend returning to desktop when simultaneous panes are necessary.

## Elevation & Depth

Depth is quiet and structural.

| Level | Treatment | Use |
|---|---|---|
| 0 | `{colors.canvas}`, no border | Application ground |
| 1 | `{colors.surface}`, 1px `{colors.hairline}` | Reading panes, queue surface, controls |
| 2 | `{colors.surface}`, 1px `{colors.hairline-strong}` | Sticky headers, selected pane, decision dock |
| 3 | 0 12px 36px rgba(16,35,31,0.12) | Evidence Peek overlay and protected confirmation dialogs only |
| 4 | Ink scrim at 36% | Destructive or irreversible confirmation only |

Rules:

- Never shadow ordinary cards, rows, metrics, or buttons.
- The Evidence Peek shadow has vertical offset and soft blur; no colored glow.
- Sticky surfaces use a rule plus a 4px tonal overlap before using shadow.
- Selection is expressed with brass connection, background tone, and type weight—not elevation.

## Shapes

The system uses small, tailored radii. Legal objects remain crisp; controls remain comfortable.

- `{rounded.none}`: shell, rails, tables, pane boundaries, decision dock.
- `{rounded.xs}`: status labels and compact metadata chips.
- `{rounded.sm}`: buttons, inputs, selected rows, and inline actions.
- `{rounded.md}`: document preview wells and grouped confirmation regions.
- `{rounded.lg}`: Evidence Peek overlay and protected dialogs only.
- `{rounded.full}`: evidence nodes, avatars, and presence indicators.

Avoid:

- Large rounded dashboard cards.
- Pills for ordinary filters, navigation, or tabs.
- Radius above 12px except circles.
- Mixed radii on sibling controls.

## Components

### Application shell

**`app-shell`** uses `{colors.canvas}` and `{typography.body-md}`. It fills the viewport and owns keyboard navigation, skip links, route announcements, and the persistent decision dock.

**`navigation-rail`** is the only large dark plane. It contains the CDS mark, Inbox, Matters, Approvals, Governance, and Help. The active item uses `{colors.on-primary}` plus a 1px brass route line that visually continues into the current surface.

Collapsed navigation keeps icons and tooltips; it never reduces targets below 40×40px.

If bilingual application chrome is approved, the expanded rail becomes 288px and labels may wrap to two lines. The 248px token remains authoritative for English-only chrome; do not squeeze bilingual labels into it.

### Buttons

**`button-primary`**

- Use for the single next action in the current region: `Confirm field`, `Submit for approval`, `Approve matter`, or `Issue pack`.
- 40px high, `{rounded.sm}`, no shadow.
- Hover uses `{component.button-primary-hover}`; pressed uses `{component.button-primary-pressed}`.
- Loading keeps the label width stable and changes copy to a present-tense action such as `Issuing pack…`.

**`button-secondary`**

- Recessed mineral fill with no border; hover uses `{component.button-secondary-hover}`.
- Used for reversible supporting actions.
- Never visually compete with the decision-dock primary action.

**`button-danger`**

- Reserved for destructive actions after a protected confirmation.
- Hover uses `{component.button-danger-hover}`.
- Copy names the object: `Delete annexure`, not `Delete`.

**Focus indicators**

- Preserve the control's original fill and add a 2px ring with 2px offset.
- Use `{colors.focus-on-light}` on light working surfaces and `{colors.focus-on-dark}` on `{colors.surface-ink}`.
- Each token maintains at least 3:1 non-text contrast against its intended adjacent surface.
- The DESIGN.md component schema represents these ring-color roles through `backgroundColor`; implementation maps them to CSS `outline-color`.

**`button-disabled`**

- Must include a nearby explanation or tooltip stating what is required.
- Disabled styling is not a substitute for permission-aware copy.

### Status labels

Status labels are compact rectangles, not pills:

- `{component.status-proposed}`: `Proposed`, `Needs confirmation`.
- `{component.status-open}`: `Open`, `Returned`.
- `{component.status-failed}`: `Failed`, including failed bank-pack generation. Its solid treatment prevents it from reading as an ordinary open item.
- `{component.status-ready}`: `Confirmed`, `Resolved`, `Ready`, `Issued`.
- `{component.status-pending}`: `Pending documents`, `Waiting approval`.

Every label carries text. Use an icon only when it improves scanning.

### Queue and matter rows

**`queue-row`** spans the content width and uses rules between siblings. Columns:

1. evidence-thread position,
2. matter and facility context,
3. stage,
4. owner,
5. aging,
6. next action.

The row's primary interaction opens the matter. Embedded buttons must stop row activation and have explicit labels.

**`selected-row`** uses `{colors.thread-soft}` only when the row is connected to the active Evidence Peek or title-chain node. Ordinary keyboard focus selects the appropriate light- or dark-surface focus token instead.

### Title-chain rail

The title-chain rail is the signature navigational component. Each instrument is a node with:

- instrument name,
- registration or mutation reference,
- date,
- source pages,
- confirmation state,
- linked Exceptions and CPs.

The rail supports `Complete`, `Gap`, `Conflict`, `Proposed`, and `Confirmed`. A gap is an explicit missing interval with recovery copy, never an empty spacer.

### Evidence Peek

**`evidence-peek`** is a contextual side pane, not a generic modal. It opens from a fact, Exception, CP, or audit event and preserves the underlying scroll position.

Header:

- source document and page,
- confidence or confirmation state,
- `Open full document`,
- close action.

Body:

- source image crop,
- extracted text,
- linked dossier field,
- reviewer note,
- previous confirmation history.

Footer:

- `Confirm against source`,
- `Flag mismatch`,
- keyboard shortcut hints.

Evidence Peek uses a visible connector back to the invoking object. On tablet it becomes a bottom sheet; on mobile it becomes the next step in the flow.

### Proposed-versus-confirmed field

The comparison component presents:

- **Source** — scanned crop and page reference.
- **Proposed** — OCR extraction in `{component.status-proposed}`.
- **Confirmed value** — editable Reviewer-owned field.
- **Difference** — character-level emphasis only when the values differ.
- **Action** — `Confirm`, `Correct`, or `Cannot verify`.

Never pre-check a confirmation control. Confidence percentage may support review but cannot determine confirmation styling.

### Findings list

The Findings list is one interface over two distinct domain objects:

- Exception — `{component.object-exception}` with a diamond-outline object icon.
- Condition Precedent (CP) — `{component.object-cp}` with a bracket object icon.

Each row must name its object type, severity or due state, evidence count, owner, waiver eligibility, and next action. Filtering may combine the objects; editing and API behavior must preserve the distinction.

Waiver actions appear only when the data marks a finding `waivable` and it is not a hard stop.

### Approval gate

The Approval Gate is an inline protected region at the end of review. It shows:

- maker identity and submission time,
- unresolved Exceptions and CPs,
- required approver role,
- pack state,
- exact consequences of approval or return.

Maker and checker remain separate even when the user is an Admin. The UI must explain permission failures rather than imply the button malfunctioned.

### Bank-pack panel

The panel distinguishes:

- `Draft — not approved`
- `Submitted for approval`
- `Approved — ready to issue`
- `Issued · vN`
- `Failed — not a clearance`

Version, generated time, approver, and source snapshot use `{typography.data}`. The issue action is primary only after approval.

### Inputs

Inputs use `{colors.surface}`, `{rounded.sm}`, and a 1px `{colors.hairline-strong}` border. Focus uses a 2px `{colors.focus-on-light}` ring. Error copy appears below the field and states both problem and recovery.

Search is an input, not a decorative pill. Filters are underlined text tabs or compact select controls, not rows of rounded chips.

### Tables

- Sticky header on long collections.
- Row actions remain visible at keyboard focus.
- Numeric and date columns align to tabular figures.
- A table never hides a primary legal state behind an icon.
- On compact widths, preserve the first identifying column and scroll remaining columns horizontally.
- Empty tables explain what belongs there and provide the next valid action.

### Notifications

Toasts acknowledge reversible background events. Destructive, failed, or permission-sensitive outcomes remain inline until resolved.

Notifications use semantic color only in the icon and compact state label; the message body remains `{colors.body}` on `{colors.surface}`.

### Motion

Motion is functional and infrequent:

- Matter opening: thread trace and node resolution, 420–560ms.
- Evidence Peek: connector draws while pane enters, 260ms.
- Tab change: content crossfades 120ms; the active rule translates 160ms.
- Row reordering after state change: layout transition 180–240ms.
- Success confirmation: one node fill, 180ms; no confetti.

Use `cubic-bezier(0.16, 1, 0.3, 1)` for the exponential ease-out and `cubic-bezier(0.4, 0, 0.2, 1)` for short state crossfades. Content is visible by default. Reduced-motion mode removes drawing and transforms while retaining immediate state changes.

## Do's and Don'ts

### Do

- Use the evidence thread to show a real source-to-fact or fact-to-decision relationship.
- Keep the computed next action visible in the decision dock.
- Mark OCR output as Proposed until a Reviewer confirms it against the source.
- Separate status from decision: a processed document is not necessarily legally cleared.
- Preserve Exception and CP as distinct objects even when shown in one Findings list.
- Use full legal-file terminology and explicit recovery copy.
- Let tables, rails, and panes share boundaries instead of wrapping everything in cards.
- Keep one clear primary action per working region.
- Use Urdu source text with correct right-to-left rendering.
- Provide loading, empty, error, offline, permission-denied, and stale-data states.

### Don't

- Do not borrow visual tokens, fonts, red accent, dark canvas, or cinematic login treatment from the current CDS frontend.
- Do not make the product look like a generic fintech dashboard.
- Do not use glass, neon, decorative gradients, giant metric cards, or ornamental courthouse imagery.
- Do not use brass on generic CTAs or decorative lines.
- Do not imply machine confidence equals legal confirmation.
- Do not label a failed pack as clearance.
- Do not expose `Approve` to the maker or imply Admin bypasses maker/checker separation.
- Do not hide missing documents behind a neutral empty state.
- Do not use color as the only carrier of risk or status.
- Do not truncate matter names, instrument references, or legal states without a full accessible value.

## Product states

Every major surface must specify these states before implementation:

- **Loading:** skeleton follows the final geometry; legal-state labels do not shimmer.
- **Empty:** names what is absent, why it matters, and the next valid action.
- **Error:** identifies the failed operation, preserves user input, and offers recovery.
- **Offline:** keeps last-known data visibly timestamped and disables state-changing actions.
- **Stale:** warns when source data changed after the current review snapshot.
- **Permission denied:** names the required role and offers a non-destructive path back.
- **Processing:** distinguishes queued, running, retrying, and failed OCR/export work.
- **Proposed:** extraction exists but no human has confirmed it.
- **Confirmed:** includes Reviewer and confirmation time.
- **Conflict:** shows competing values and their sources side by side.

## Accessibility

- Target WCAG 2.2 AA.
- Minimum text contrast: 4.5:1; large text: 3:1.
- Minimum pointer target: 40×40px desktop, 44×44px touch.
- Focus is always visible and never encoded with brass alone.
- All pane transitions announce the new region to assistive technology.
- Evidence connectors are supplementary; source relationships also exist in semantic text.
- Document crops have source page labels and meaningful alternatives.
- Tables use proper headers and expose sorting state.
- Dialogs are limited to destructive or protected decisions and trap focus correctly.
- Time-sensitive states never rely on animation or color.

## Implementation notes

- Treat this document as the new visual authority; the existing frontend is product-behavior evidence only.
- Build tokens as CSS custom properties and map Tailwind utilities to them.
- Prefer Radix primitives for focus, dialogs, popovers, and accessible state behavior, then restyle fully.
- Use Lucide icons at 1.5px stroke unless a domain icon requires an authored SVG.
- Render evidence connectors as accessible SVG overlays tied to semantic DOM anchors.
- Keep connector geometry derived from layout; never hard-code viewport coordinates.
- Use View Transitions or Motion for pane continuity. Use GSAP only for the single thread-trace sequence if the implementation requires path drawing.
- Lazy-load document images and OCR overlays; the work surface must remain responsive during processing.
- Virtualize collections only when measured row counts justify it; preserve keyboard and screen-reader behavior.
- Never place untrusted document text into raw HTML.

## Responsive priorities

1. Preserve legal state and next action.
2. Preserve source provenance.
3. Preserve object identity and version.
4. Preserve simultaneous comparison where the device permits it.
5. Collapse secondary metadata before hiding any of the above.

## Iteration guide

1. Implement one connected workflow at a time: Queue → Matter → Source → Decision.
2. Resolve tokens directly from this file; do not approximate colors or spacing.
3. Verify the evidence thread terminates at real semantic objects.
4. Test keyboard navigation and screen-reader announcements before visual polish.
5. Validate desktop at 1440×900 and 1280×800, tablet at 834×1194, and mobile at 390×844.
6. Test long Urdu and English source values, missing documents, conflicting extracts, and permission-denied approvals.
7. Run `npx -p @google/design.md designmd lint DESIGN.md` on Windows after edits.
8. Keep the palette restrained. Add a token only when an existing role cannot express the required state.

## Known gaps

- Final General Sans licensing and self-hosting path must be confirmed before production.
- Bilingual application chrome is undecided; Urdu source rendering is required regardless.
- Mobile supports triage and approval, but the exact threshold for requiring desktop source comparison needs usability testing.
- The evidence-thread animation requires a performance prototype against large matters.
- WCAG 2.2 AA is the design target; formal product compliance remains a project decision.
