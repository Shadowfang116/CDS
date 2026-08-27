# Open questions

Each question carries a **default** — what happens if it goes unanswered. Work does not
stop on an unanswered question unless the default is marked ⛔ BLOCKING.

When one is answered, move it to `05_decisions.md` with the date and delete it here.

Current status: the previously blocking corpus/ground-truth question is answered by the
local Urdu corpus at `C:\Users\fahad\Downloads\CDS_GOLD_001_URDU_PDF_CORPUS`. Its gold
truth was used for separate 12-file initial and 5-file additional runs on 2026-08-26.

---

### Q1 — Sample documents + ground truth (historical; resolved 2026-08-26)

**Asked:** 2026-08-15 · **Status:** resolved by external local corpus

Originally needed ~20-30 representative pages with ground-truth text in
`datasets/urdu_ocr/samples/`. Format is specified in `datasets/urdu_ocr/README.md`;
the existing manifest expects `sample1.pdf` + `sample1.page1.txt` + `sample1.page2.txt`
and none of those files are in the repo.

**Resolution:** the external corpus supplies 17 synthetic PDFs, `gold_truth.yaml`,
`README_TEST_CASE.md`, and `SOURCE_BASIS.md`; the execution report is recorded in
`AI_context/execution_reports/cds_gold_001_e2e_20260826-165739.json`.

**Partial unblock:** synthetic or public-domain Urdu documents would let the *harness*
be built and smoke-tested (Phase 0.1–0.4), but cannot produce a meaningful accuracy
number for your document mix. Phase 0.1–0.4 proceed without this; 0.5–0.6 do not.

---

### Q2 — Document mix

**Asked:** 2026-08-15 · **Status:** open

What share of real documents is:
- native-text PDF vs scanned image?
- printed/typed vs handwritten?
- Urdu vs English vs mixed?

This decides which phase pays off most. If a large share is native-text PDF, F6 alone
(routing those around OCR entirely) is worth more than everything else combined.

**Default if unanswered:** assume a scanned-dominant, Urdu-dominant, printed-dominant
mix, and implement F6's text-layer fast path anyway — it is cheap, additive, and falls
back safely. Sequence stays as written in `03_plan.md`. Revisit once the sample set
arrives, since the samples will reveal the mix directly.

---

### Q3 — Accuracy target framing

**Asked:** 2026-08-15 · **Status:** open

Raw CER, or validated-field accuracy? See the table at the top of `03_plan.md`.
99% raw CER on scanned Urdu Nastaliq is not achievable by any current system; 99% on
validated key fields is.

**Default if unanswered:** build and report **both** — raw CER/WER/F1 on the full page,
plus field-level accuracy with an auto-accept rate on CNIC / khasra / khewat / dates /
amounts / names. Report measured numbers for each and let the framing be chosen once
real numbers exist rather than in advance. Costs a little extra harness work in Phase 0;
avoids committing to a target that may be unreachable.

---

### Q4 — Keep the two-stack split, or consolidate?

**Asked:** 2026-08-15 · **Status:** open

`ocr_service/` (~648 lines, runs everything) vs `backend/app/services/ocr_*.py`
(~3,480 lines, ~3,337 of them unreachable).

**Default if unanswered:** **keep the split.** Port fixes into `ocr_service/`, leave
Stack B untouched, and don't delete it. Rationale: consolidation is a large blast radius
with no measurement in place to catch regressions — exactly the wrong order. Revisit
after Phase 1, when a baseline exists and the deltas are measurable.

Worth flagging regardless of the answer: ~3,337 lines of unreachable OCR code is a
standing maintenance and confusion cost. Even if consolidation is declined, the dead
modules should eventually be either wired up or deleted, not left ambiguous.

---

### Q5 — Push access to the remote

**Asked:** 2026-08-15 · **Status:** open, low priority

Push to `github.com/Shadowfang116/CDS` has not been tested.

**Default if unanswered:** keep committing locally on the branch. Test push at the first
point where sharing actually matters; fall back to fork + PR if rejected. Nothing
depends on this until there is code worth pushing.
