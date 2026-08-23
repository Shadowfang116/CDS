# AI_context — OCR + field extraction on `CDS`

Working context for OCR accuracy and post-OCR autofill. Lives at
`bank-diligence-platform/AI_context/` (in-repo; see D5). Update it in the **same
session** as any OCR/extraction/autofill change.

**If you are an AI session starting here: read this file, then `02_findings.md`.
Everything else is reference.**

---

## Current state (updated 2026-08-18)

| | |
|---|---|
| **Phase** | Backend freeze-and-delete cleanup. Workbench gold findings already landed. |
| **Code changed this session** | workbench service/routes, Matter `load()`, rulepacks, `.bak` deletes, waive deprecation, OCR deprecation notes |
| **Branch** | `refactor/cds-backend-core` |
| **Findings** | F10 🟢, F11 🟢, F12 🟢. Open: F7 (samples), F8 (quality.py). In progress: F3 (Surya), F6 (settings/text-layer follow-up). |
| **Measurement** | No CER. |
| **Blocked on (OCR claims)** | Q1 sample PDFs + ground truth |
| **Next action** | Live walk RUN 2 then RUN 3 waiver + pack on the workbench once the stack is up. |

**The 65% accuracy figure is unverified and unreproducible from this repo.**
No accuracy claim gets made until Phase 0 produces a measured baseline.

**Start here if you're picking up work:** Gold workbench is in the Matter page and now reads `GET /cases/{id}/workbench`. Walk RUN 2 `5bcdb8eb-…` and RUN 3 `38e6069e-…`. Do not use RUN 1. Cleanup notes: `AI_context/backend_simplification/`. Next OCR step is still Q1 samples.

---

## Standing rules for this work

1. **No accuracy number is stated unless it was measured** on the sample set, by a
   run recorded in `04_worklog.md`. Not estimated, not inferred, not carried over
   from a previous claim.
2. **Measure the thing that runs.** Production OCR is the `ocr_service/`
   microservice, not the backend `ocr_*.py` stack. An eval that exercises Stack B
   is measuring dead code.
3. **Every change re-runs the eval**, and the before/after numbers go in the worklog.
   Field-extraction changes that cannot produce CER still get a pytest + worklog entry.
4. **Update this folder in the same session** as the code (D5). Do not push unless asked.
5. **Findings carry a status.** When you fix one, update the table in
   `02_findings.md` in the same session — not later.

---

## Files

| File | What it is | Read when |
|---|---|---|
| `01_repo_map.md` | Where OCR code lives; the real production request path | Orienting in the codebase |
| `02_findings.md` | Findings F1–F10, each with evidence + a re-verify command | Always — this is the core |
| `03_plan.md` | Phased plan, and what "99%" realistically means | Deciding what to do next |
| `04_worklog.md` | Current state + dated log of changes and measurements | Resuming work |
| `05_decisions.md` | Decisions taken, with rationale and date | Before re-litigating anything |
| `06_open_questions.md` | What's blocked, and the default if unanswered | Before declaring yourself blocked |
| `07_runbook.md` | Exact commands to reach a measurable environment | Running anything |
| `08_master_plan.md` | **How work lands** — workstreams, PR units, DoD, CI reality | Before writing any code |

---

## Repo / branch state

- Inner repo: `bank-diligence-platform/` (`origin` = `https://github.com/Shadowfang116/CDS.git`)
- Gold workbench and CDS-GOLD-001 semantics are on `fix/cds-gold-001-semantics`. OCR WS0/WS1 landed earlier on `feat/ocr-accuracy-improvements`.
- Do not push unless asked.

## Local toolchain (verified 2026-08-17)

Docker is in use for the full stack. Field-extraction tests run on the host:

```bash
cd backend
python -m pytest tests/test_contextual_autofill.py -q
```

`datasets/urdu_ocr/samples/` still does not exist (Q1). No CER may be claimed until that is populated and `04_worklog.md` records a run.
