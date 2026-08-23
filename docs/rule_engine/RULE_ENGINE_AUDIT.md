# Rule Engine Audit

This audit locks the current 57-rule pack behind synthetic golden fixtures in `backend/tests/rulepack/fixtures/` and the pure runner in `backend/tests/rulepack/test_golden.py`.

| Ledger Item | Status | Evidence |
| --- | --- | --- |
| 1. `is_hard_stop` ignored | Fixed | Hard-stop flags now flow through `RuleResult`, `Exception_`, `run_rules`, and approvals risk/readiness queries. Covered by `tpa_notice_possession_001_positive.yaml`, `tpa_chain_gap_001_positive.yaml`, `reg_001_positive.yaml`, `soc_001_positive.yaml`, `soc_002_positive.yaml`, `ruda_001_positive.yaml`, `cant_001_positive.yaml`, and `test_compute_case_decision_fail_for_hard_stop`. |
| 2. No PASS / CONDITIONAL PASS / FAIL decision | Fixed | `compute_case_decision()` is wired into `run_rules` and `evaluation_service`. Rule fixtures assert `expected_decision`, and `test_compute_case_decision_pass`, `test_compute_case_decision_fail_for_open_high`, and `test_compute_case_decision_conditional_pass_for_waived_high` cover the decision branches. |
| 3. Keyword substring matching | Fixed | Shared boundary-aware keyword matching now blocks substring false positives. Covered by `cant_002_negative.yaml` (`please`), `soc_04_negative.yaml` (`discharge`), `pos_02_negative.yaml` (`reclaim`), and `tpa_notice_possession_001_negative.yaml` (`Current`). |
| 4. `mismatch` ignored declared compare logic | Fixed | `mismatch` now supports field-pattern comparison, per-field comparison, date comparison, and threshold-percent comparison. Covered by `kyc_03_positive.yaml`, `reg_002_positive.yaml`, `stamp_002_positive.yaml`, and `lra_002_positive.yaml`. |
| 5. `missing_evidence` substring cross-match | Fixed | Required doc checks now use normalized exact matching with conservative canonicalization. Covered by `dha_03_positive.yaml`, where `map` no longer satisfies `approved_map`. |
| 6. No negation/context handling for keywords | Fixed | Negated matches are skipped. Covered by `pos_02_negative.yaml` (`no objection`) and `soc_04_negative.yaml` (`without encumbrance`). |
| 7. Regime gating silently skips when regime missing | Fixed | Evaluation now raises a hard precondition error when regime-conditional rules exist and `property.regime` is unavailable. Covered by `system_regime_unknown.yaml`. |
| 8. OCR-incomplete runs silently under-fire | Fixed | Evaluation now raises a hard precondition error when OCR is incomplete. Covered by `system_ocr_incomplete.yaml`. |
| 9. Unknown evaluator silently falls back | Fixed | Schema validation and runtime evaluation both reject unknown evaluators. Covered by `test_unknown_evaluator_is_rejected`. |
| 10. `timeline_gap` no-op evaluator | Fixed by removal | The schema now rejects `timeline_gap` so the dead evaluator cannot silently ship. Covered by `test_timeline_gap_is_rejected`. |
| 11. Legacy/P9 overlap duplicates | Decision documented | No deletion in this change. The harness records the current overlap explicitly and keeps behavior stable until a separate canonicalization pass retires duplicates with stakeholder signoff. Evidence: `reg_001_positive.yaml` and `tpa_chain_gap_001_positive.yaml` intentionally expect both `REG_001` and `TPA_CHAIN_GAP_001`. |
| 12. `mismatch` results lacked `evidence_refs` | Fixed | Mismatch results now attach note-based evidence refs. Covered by `expect_evidence_for` assertions in `kyc_03_positive.yaml`, `reg_002_positive.yaml`, `stamp_002_positive.yaml`, and `lra_002_positive.yaml`. |

## Canonical-Set Decision

For this project the overlap decision is:

1. Keep the legacy and P9 rules in place for now.
2. Make the overlap explicit in the fixtures instead of deleting rules opportunistically.
3. Treat future retirement or scoping of duplicate rules as a separate, fixture-proven change after legal/product review.

## Coverage Lock

`backend/tests/rulepack/test_golden.py::test_every_rule_has_fixtures` fails if any rule in `docs/05_rulepack_v1.yaml` lacks both:

1. At least one positive fixture.
2. At least one negative fixture.

`backend/tests/rulepack/test_metrics.py` regenerates `docs/rule_engine/rule_metrics.md` and fails if per-rule precision or recall drops below `1.0` on the synthetic corpus.
