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
