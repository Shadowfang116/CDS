# Decisions

Answered questions and settled choices. **Once something is here, don't re-litigate it** —
if it needs revisiting, add a new dated entry that supersedes the old one rather than
editing history.

Format: one entry per decision. Keep them short.

---

### D1 — Work on a local branch, not a fork · 2026-08-15

**Decision:** `feat/ocr-accuracy-improvements`, cut locally off `master` @ `b94bb10`.

**Why:** the clone is writable, so a fork adds friction for no benefit.

**Caveat:** push access to `github.com/Shadowfang116/CDS` has **not** been tested. If a
push is rejected, fall back to fork + PR. This is not yet settled.

---

### D2 — Context folder lives outside the repo · 2026-08-15

**Decision:** `AI_context/` sits at `Fahad Proj/AI_context/`, a sibling of `CDS/`, and is
never committed.

**Why:** it holds working notes, unverified estimates and user-specific context that
shouldn't enter project history. Keeping it outside the repo makes accidental commits
structurally impossible rather than a matter of remembering `.gitignore`.

---

### D3 — Fixes land in `ocr_service/`, not the backend stack · 2026-08-15

**Decision:** all accuracy work targets the `ocr_service/` microservice. Where Stack B
already has a correct implementation (e.g. the `minAreaRect` deskew at
`ocr_preprocess.py:146`), port it into the microservice rather than trying to route
traffic to Stack B.

**Why:** production OCR goes Celery → HTTP → `ocr_service/`. Roughly 3,337 lines of
Stack B OCR code never execute (`01_repo_map.md`). Improving unreachable code changes
nothing measurable.

**Note:** this is about *where fixes go*, not about whether the two stacks should
eventually be merged — that's Q4 in `06_open_questions.md` and remains open.

---

### D4 — No accuracy number without a measurement · 2026-08-15

**Decision:** no CER/WER/F1/percentage figure is stated in any deliverable unless it came
from a recorded run on the sample set, logged in `04_worklog.md`.

**Why:** the inherited "65%" turned out to be unreproducible from the repo — the eval
harness doesn't import and no ground truth exists (F7). Repeating unverified numbers is
how that happened; not repeating them is how it stops.

**Consequence:** Phase 0 is blocking. Estimated causal weights in `02_findings.md` are
labelled as estimates and stay that way until measured.

---

### D5 — `AI_context/` is the in-repo working folder · 2026-08-17

**Decision:** Working memory lives at `bank-diligence-platform/AI_context/`. Update it in
the same session as any OCR, extraction, or autofill change.

**Why:** D2 placed the folder outside git as a sibling of `CDS/`. The copy that is
actually used now sits inside the inner repo. Path follows the files that exist;
whether the folder is committed remains a later choice. Do not push unless asked.

**Supersedes:** D2's filesystem location only. D2's "don't leak working notes into
history by accident" still applies if you choose not to commit this folder.

---

### D6 — Autofill stays rules-first · 2026-08-17

**Decision:** No LLM for dossier autofill. Pakistani sale-deed recitals are parsed with
a clause grammar (`sale_deed_clauses.py`). Regex remains for plot/block/registry/CNIC.

**Why:** Test case 1 already had the correct names in OCR. The miss was window/marker
logic, not language understanding.

---

### D7 — Autofill writes candidates; confirm writes the dossier · 2026-08-17

**Decision:** `autofill_dossier` persists `ocr_extraction_candidates` only. Confirm (or
a manual dossier edit) upserts `case_dossier_fields`. Do not auto-confirm.

**Why:** Bank-grade review. F8's earlier "bad pages get auto-filled into the dossier"
wording was incorrect; garbage could still become high-confidence *candidates* (F10).

---

### D8 — Candidates are per source; rules have applicability · 2026-08-17

**Decision:** A dossier field is a set of Pending candidates keyed by
`(case_id, field_key, document_id)`, not one row per field. A later document must not
silently replace a better candidate. Conflicting values stay and are marked for review.

Rules carry `applies_when` (`borrower_type`, `transaction_type`, `regime`). Unspecified
borrower defaults to `individual`; unspecified transaction defaults to `mortgage`.
Company mortgages therefore skip photograph / salary-slip / utility / co-applicant
requirements unless policy says otherwise.

Canonical `doc_type` is persisted before rule evaluation. Filename may hint; OCR
content classifies when present. Protected filename types (Fard, Search Report,
Valuation, PT-10, Possession, etc.) are not overridden by a stray mutation keyword
in the OCR text.

**Why:** CDS-GOLD-001 RUN 1 showed the second autofill destroying sale-deed names and
the 28-rule MVP pack producing 24–25 generic exceptions instead of 6–8 legal findings.

---

### D9 — Inferred case context may be written to the dossier · 2026-08-17

**Decision:** `case.borrower_type` and `case.transaction_type` are system-inferred
fields (same pattern as `property.regime`). Autofill and `run_rules` upsert them
onto `case_dossier_fields` so `applies_when` can see them. Party names, area, and
other legal facts remain candidates until confirm (D7). A reviewer-confirmed
borrower type is not overwritten.

**Why:** RUN 2 hybrid (`4802e8f7-…`) inferred company from `لمیٹڈ` but stored it
only as an OCR candidate. The rule engine reads dossier fields, defaulted to
`individual`, and still raised photograph / salary-slip / LDA / society-transfer
noise.

---

### D10 — Upload time is not a legal issue date · 2026-08-17

**Decision:** Document `created_at` may be used only to decide which instrument is
the newest *on file*. Freshness, staleness, and “current Fard” are computed from a
parseable `fact.issue_date`. If the newest Fard has no issue date, raise
unconfirmed rather than treating today’s upload as current.

**Why:** A Fard uploaded today can have been issued months earlier. RUN 2 cleared
GOLD-FARD-01 from upload time; that is not production-legal.

**Also:** Waived exceptions are preserved across `run_rules`. A later evaluate must
not reopen a dual-control waiver.

---
