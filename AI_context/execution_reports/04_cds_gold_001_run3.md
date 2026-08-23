# CDS-GOLD-001 RUN 3 — 2026-08-17

**Branch:** `fix/cds-gold-001-semantics`  
**RUN 1 (keep):** `4673c7f2-5f39-4ebb-8f4a-4406fab0decc`  
**RUN 2 (keep):** `5bcdb8eb-75bc-440b-9bcb-3a963b574360`  
**Aborted first RUN 3 attempt:** `9c4771ae-b80e-4d42-a129-2a18d02bb3d1` (area compared mutation; Fard newest-doc tie used UUID)  
**RUN 3 (flagship):** `38e6069e-4c3d-4a41-94c8-8b9ecc92e069`  
UI: http://localhost:3000/dashboard/cases/38e6069e-4c3d-4a41-94c8-8b9ecc92e069

No OCR percentage is claimed. Surya, Paddle, and frontend were not changed.

## Lifecycle

| Stage | Decision | Open findings |
|---|---|---|
| Initial 11 PDFs | FAIL | GOLD-AREA-01, GOLD-PLAN-01, GOLD-DUES-01, GOLD-ENCUMB-01, GOLD-FARD-01, GOLD-NAME-01, GOLD-TAX-01 |
| Additional 5 PDFs | PASS (Low tax still open) | GOLD-TAX-01 only |
| Reviewer waiver + admin approve + re-eval | PASS | GOLD-TAX-01 Waived |

Resolved by additional evidence: area mismatch, building plan, development dues, prior encumbrance, stale Fard (issue date `2026-08-08` on the corrected Fard), name variation.

Waiver path: `reviewer@orga.com` proposed `exception_waive`; `admin@orga.com` approved. Re-eval did not reopen the waived row.

Bank pack export `670f6c3e-823c-4d1d-b2e6-3803391c0a59` queued as `bank_pack_pdf` / pending.

Snapshot: `AI_context/execution_reports/cds_gold_001_e2e_20260817-224406.json`

## What F12 changed so this run could fire

- Sale Deed `کل رقبہ 4 Jus` and old Fard `کل رقبہ … 3 JUS 18 مرلہ` now extract as 80 vs 78 marla.
- Area rule compares title to **Fard**, not to a same-day Mutation that already says 4 Kanal.
- Newest Fard is chosen by upload **datetime**, not calendar date + UUID.
- `گست` parses as August without corrupting `اگست`.
- Historic tax keywords match the PT-10 `تاریخی paper receipt` / `20-2019` wording.
- Waived rules are not recreated on the next evaluate.

## Tests

Host: 198 backend tests passed earlier in the session; gold semantics 166 passed after the Fard/area ordering fix (`test_exception_waivable.py` still skipped — host Python lacks PyJWT).
