# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user is a **law-firm Reviewer** sitting with a Pakistan property title chain, clearing Exceptions and Conditions Precedent before a financing decision can proceed.

Other in-product roles exist in the implementation (Admin, Approver, Viewer) but were not confirmed as primary audiences for future design work.

## Product Purpose

Covenant Diligence Systems (CDS) is an on-prem diligence workspace for Pakistan property-backed finance documentation. A Reviewer intakes a matter, uploads the title chain, uses OCR as a first-pass reading aid, confirms extracted fields into a dossier, tracks Exceptions and Conditions Precedent with evidence, and produces a reviewable bank pack.

Success is a file a solicitor can stand behind: every extracted fact checked against the deed, every exception and CP accounted for, and an auditable pack ready for financing — not a machine-issued legal conclusion.

## Positioning

OCR and extraction are a **reading aid, never a silent legal conclusion**. The Reviewer must still compare extracted fields with the underlying deed, mutation, or transfer paper before confirming them. A neighboring DMS or OCR product could not truthfully claim this human-in-the-loop legal review stance as the product’s core mechanism.

## Operating Context

Reviewers work matters (finance / collateral files) that contain a title chain: sale deeds, mutation entries (including fard and jamabandi), allotment or transfer papers, NOCs, and annexures. Daily ritual is the command centre and matters queue: what needs legal review, what is aging, what is blocked on exceptions or CP closure. The bank is a recipient of the pack, not the confirmed daily operator.

## Capabilities and Constraints

Confirmed in the running product (implementation facts, not extra brand bindings):

- Case intake, document upload, page-level OCR review, dossier confirm, rule evaluation, Exceptions / waivers / evidence / annexures, CP workflow, audit timeline, DOCX and PDF bank-pack export.
- Multi-tenant org isolation; RBAC includes Admin, Reviewer, Approver, Viewer.
- Uncertain extractions are stored with `needs_confirmation`; they must not be silently written as verified dossier facts.
- Urdu and Urdu+English OCR exist as document-language options. Whether the UI itself is bilingual is **undecided**.
- Deployed on-prem via Docker Compose (Next.js, FastAPI, Celery, PostgreSQL, Redis, MinIO).

Undecided: WCAG as a required accessibility bar; bilingual product UI.

## Brand Commitments

- Name: **Covenant Diligence Systems** (short: **CDS**).
- Subtitle: **Pakistan property diligence workspace**.
- Voice and terminology stay in the legal file: matter, exception, Condition Precedent (CP), dossier, bank pack, waiver, annexure, title chain. Do not genericize into “tickets,” “projects,” or “docs.”

## Evidence on Hand

- In-product walkthrough copy: `frontend/config/product-walkthrough.ts`, `frontend/app/tutorial/page.tsx`.
- Brand strings: `frontend/lib/brand.ts`.
- Architecture, security baseline, rulepack, and bank-IT pack: `docs/`.
- Pilot demo case and seed data exist for walkthroughs.

Future work must not fabricate testimonials, customer names, bank logos, benchmarks, or press.

## Product Principles

1. The Reviewer is the legal decision-maker; the system assists, it does not conclude.
2. Speak in the language of the file (matter, exception, CP, bank pack), not SaaS generic.
3. Every extracted field stays provisional until a human confirms it against the source document.
4. Design for the person clearing a title chain under financing pressure, not for a bank officer reading an export.
5. Preserve the CDS name and Pakistan property-diligence identity; do not rebrand in passing.
