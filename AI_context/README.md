# AI_context — OCR accuracy effort on `CDS`

Working context for the OCR accuracy work. Kept **outside** the git repo
(`Fahad Proj/CDS`) so nothing here is committed by accident.

**If you are an AI session starting here: read this file, then `02_findings.md`.
Everything else is reference.**

---

## Current state (updated 2026-08-15)

| | |
|---|---|
| **Phase** | WS0 / WS1 in progress |
| **Code changed** | `ocr_service/Dockerfile`, `eval_urdu_ocr.py`, `config.py`, `ocr_domain_ur.py`, `ocr_text.py`, `test_ocr_domain_ur.py`, `ci.yml`, `eval_ocr_service.py` |
| **Branch** | `feat/ocr-accuracy-improvements` |
| **Findings** | 8 open, 1 fixed (F5), 1 in progress (F6) |
| **Measurement** | Pending sample PDFs (Q1) |
| **Blocked on** | Sample documents (Q1) |

**The 65% accuracy figure is unverified and unreproducible from this repo.**
No accuracy claim gets made until Phase 0 produces a measured baseline.

**Nothing in CI touches the OCR system** — no Python tests, `ocr_service` never built or
started, the accuracy gate never wired in. A contributor can break OCR completely and CI
stays green. See `08_master_plan.md` §1 before contributing anything.

**Start here if you're picking up work:** `08_master_plan.md` §5 (H1 — a 30-second
Docker check that may be the highest-value fix in the plan), then units 0.1–0.4.
None need user input.

---

## Standing rules for this work

1. **No accuracy number is stated unless it was measured** on the sample set, by a
   run recorded in `04_worklog.md`. Not estimated, not inferred, not carried over
   from a previous claim.
2. **Measure the thing that runs.** Production OCR is the `ocr_service/`
   microservice, not the backend `ocr_*.py` stack. An eval that exercises Stack B
   is measuring dead code.
3. **Every change re-runs the eval**, and the before/after numbers go in the worklog.
4. **This folder stays outside the repo.** Never `git add` it.
5. **Findings carry a status.** When you fix one, update the table in
   `02_findings.md` in the same session — not later.

---

## Files

| File | What it is | Read when |
|---|---|---|
| `01_repo_map.md` | Where OCR code lives; the real production request path | Orienting in the codebase |
| `02_findings.md` | The 9 findings, each with evidence + a re-verify command | Always — this is the core |
| `03_plan.md` | Phased plan, and what "99%" realistically means | Deciding what to do next |
| `04_worklog.md` | Current state + dated log of changes and measurements | Resuming work |
| `05_decisions.md` | Decisions taken, with rationale and date | Before re-litigating anything |
| `06_open_questions.md` | What's blocked, and the default if unanswered | Before declaring yourself blocked |
| `07_runbook.md` | Exact commands to reach a measurable environment | Running anything |
| `08_master_plan.md` | **How work lands** — workstreams, PR units, DoD, CI reality | Before writing any code |

---

## Repo / branch state

- Repo root: `/Users/itsmibrahim/Documents/Fahad Proj/CDS`
- Remote: `https://github.com/Shadowfang116/CDS`
- Branch: **`feat/ocr-accuracy-improvements`** (off `master` @ `b94bb10`), created locally.
  Working tree was clean when cut. Push access to the remote **has not been tested** —
  if push is rejected, fall back to fork + PR.
- Other remote branches exist (`codex/*`, `feat/rule-engine-hardening`); none touched.

## Local toolchain (verified 2026-08-15)

Nothing OCR-related is installed on the host — no `cv2`, `numpy`, `PIL`,
`pytesseract`, `surya`, `paddleocr`, `pdf2image`; no `tesseract` binary.
Docker is installed (29.2.1) but **not running**.
`datasets/urdu_ocr/samples/` does not exist (gitignored, never populated).

**Consequence:** accuracy cannot be measured on this machine as-is. See `07_runbook.md`
for how to get to a measurable state. All changes must be verified in Docker against
real sample PDFs + ground truth before any accuracy number is claimed.
