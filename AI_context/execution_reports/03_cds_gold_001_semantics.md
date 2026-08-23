# CDS-GOLD-001 semantics patch — 2026-08-17

**Branch:** `fix/cds-gold-001-semantics`  
**RUN 1 (keep, pre-fix):** `4673c7f2-5f39-4ebb-8f4a-4406fab0decc`  
**Aborted hybrid (do not use):** `4802e8f7-e117-4a65-9d03-65500228d31b`  
**RUN 2 (fresh matter, patched engine):** `5bcdb8eb-75bc-440b-9bcb-3a963b574360`  
UI: http://localhost:3000/dashboard/cases/5bcdb8eb-75bc-440b-9bcb-3a963b574360

No OCR percentage is claimed. Surya and Paddle were not changed. Frontend was not changed.

## 1. Files changed

- `backend/app/services/extractors/candidate_arbitration.py` (new)
- `backend/app/services/canonical_docs.py` (new)
- `backend/app/services/extractors/document_facts.py` (new)
- `backend/app/services/dossier_autofill.py`
- `backend/app/services/extractors/party_roles.py`
- `backend/app/services/extractors/validators.py`
- `backend/app/services/extractors/doc_routing.py`
- `backend/app/services/rule_engine.py`
- `backend/app/services/rule_schema.py`
- `backend/app/core/config.py`
- `backend/app/workers/tasks_ocr.py`
- `docs/05_rulepack_v1.yaml`
- `docker-compose.yml` (already had worker `RULEPACK_PATH`)
- `docker-compose.prod.yml` (default `RULEPACK_PATH=/app/docs/05_rulepack_v1.yaml` + docs mount)
- `.env.example`, `.env.production.example`
- `scripts/dev/pilot_real_case.ps1` (cookie login, not removed `/dev-login`)
- `scripts/dev/run_cds_gold_001_e2e.ps1` (matter title RUN 3; waiver + bank pack)
- `backend/tests/test_contextual_autofill.py`
- `backend/tests/test_cds_gold_001_semantics.py` (new)
- `backend/tests/rulepack/factory.py`
- `backend/tests/rulepack/fixtures/gold_*.yaml` (new)
- `backend/tests/rulepack/fixtures/lda_*.yaml` (`regime: LDA`)
- `backend/tests/rulepack/fixtures/dha_0{1,2,3,4}_positive.yaml`
- `AI_context/02_findings.md`, `04_worklog.md`, `05_decisions.md`

## 2. Tests added

- `test_sale_deed_clause_survives_later_mutation_candidate`
- `test_weaker_same_source_does_not_downgrade`
- `test_mutation_form_labels_are_rejected`
- `test_mutation_is_not_sale_deed_from_one_keyword`
- `test_canonical_types_for_gold_corpus_filenames`
- `test_filename_wins_over_mutation_content`
- `test_area_fact_parses_kanal_marla`
- `test_owner_fact_rejects_label_fragments`
- `test_name_variation_ignores_implausible_owners`
- `test_company_mortgage_skips_photograph_rule`
- `test_infer_borrower_type_from_company_markers`
- `test_gold_area_mismatch_evaluator`
- `test_area_mismatch_requires_title_and_revenue_sources`
- `test_stale_fard_cleared_by_newer_undated_fard`
- Golden fixtures GOLD-AREA-01 … GOLD-TAX-01 (positive + negative)

## 3. Tests passed

```
cd backend
python -m pytest tests/test_contextual_autofill.py tests/test_cds_gold_001_semantics.py tests/test_rule_engine_mvp.py tests/rulepack -q
# 171 passed
python -m pytest tests -q --ignore=tests/test_exception_waivable.py
# 194 passed (host collection of test_exception_waivable.py needs PyJWT; unrelated)
```

Worker finished RUN 2 OCR + autofill + evaluate with no `run_rules` failure.

## 4. Before / after seller–buyer arbitration

| | RUN 1 (old) | RUN 2 (patched) |
|---|---|---|
| Lookup | first Pending row for `field_key` | Pending row for `(field_key, document_id)` |
| Later mutation | overwrote sale-deed row, including `document_id` | cannot update another document's row |
| Seller | `محمد اکرم` → `رجسٹریشن حوالہ` | sale-deed `clause_urdu` kept: `محمد اکرم` |
| Buyer | textile company → `/ منتقل الیہ` | sale-deed `clause_urdu` kept: `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ` |
| Method rank | ignored | `clause_urdu` > labelled > anchor |
| Conflicts | destroyed | preserved + `needs_review` (plot also kept `82` from the deed beside weaker HF hits) |

## 5. Canonical document types recognized (RUN 2 live)

Sale Deed, Mutation, Fard, CNIC, Society/Authority NOC, Search Report, Valuation, Facility Approval, Possession Letter, Property Tax/PT-10, Board Resolution, Building Plan, Dues Clearance, Charge Release, Identity Confirmation.

All 16 corpus files classified to that vocabulary. `Sale Deed` aliases to `registry_deed` for REG_001. Filename is protected for Fard / Search Report / Valuation / PT-10 / Possession / etc.; a stray mutation keyword in OCR cannot reclassify them.

## 6. Gold rules that now exist

| ID | Evaluator | RUN 2 initial | After additional | After evaluator rebuild re-eval |
|---|---|---|---|---|
| GOLD-PLAN-01 | `missing_evidence` (company) | Open | resolved by Building Plan | closed |
| GOLD-DUES-01 | `keyword_risk` + `cleared_by_doc_types` | Open | resolved by Dues Clearance | closed |
| GOLD-ENCUMB-01 | `keyword_risk` on Search Report | Open | resolved by Charge Release | closed |
| GOLD-NAME-01 | `name_variation` | Open | resolved by Identity Confirmation | closed |
| GOLD-FARD-01 | `stale_document` (90 days) | Open | stayed Open (no parseable date on corrected Fard) | closed (newer Fard document `created_at`) |
| GOLD-AREA-01 | `area_mismatch` title vs revenue | did not fire (no sale-deed kanal fact) | Open (spurious 18 vs 10 Marla fallback) | closed (compare only Sale Deed/Possession vs Fard/Mutation) |
| GOLD-TAX-01 | `historical_keyword` | did not fire | did not fire | still absent |

Retail KYC photograph / salary-slip / utility / co-applicant, LDA scheme, society-transfer, municipal NDC, and e-stamp rules did **not** fire on this company mortgage. REG_001 / POS-01 did **not** fire (Sale Deed and Possession Letter recognized).

Initial RUN 2 evaluate: **5 exceptions, decision FAIL** (3 High + 2 Medium). That is the 6–8 legal band, not 24–25 generic missing-doc cards.

## 7. Gold facts still hard to evaluate

- **Title area (4 Kanal on the sale deed)** was not extracted from Tesseract text on this corpus, so GOLD-AREA-01 could not fire on the initial batch for the legally correct reason. The engine now refuses to compare unrelated docs (search report vs valuation) as a fake title/record pair.
- **Corrected Fard issue date** was not parsed, so GOLD-FARD-01 originally stayed open until the evaluator started using the newer Fard document's upload time as a freshness fallback.
- **Historical tax language** (`previous year` / `گزشتہ سال`) was not captured as `fact.tax_history`, so GOLD-TAX-01 never opened and therefore cannot be waived. The rule exists; this run had no keyword evidence.
- Name variation across scripts still depends on a plausible `fact.owner_name`. Garbage fragments (`ملاحظہ`, `کے لیے`) are rejected.
- Party names remain **candidates** until confirm (D7). Rules read pending candidates via `document_facts`.

## 8. Rebuild and RUN 2

```powershell
cd C:\Users\fahad\Desktop\bank-diligence-platform\bank-diligence-platform
docker compose up -d --build api worker
docker compose logs --tail=100 api
docker compose logs --tail=100 worker

Push-Location backend
python -m pytest tests/test_contextual_autofill.py -q
python -m pytest tests/test_rule_engine_mvp.py -q
python -m pytest tests -q --ignore=tests/test_exception_waivable.py
Pop-Location

# Fresh matter. Do not reuse RUN 1 4673c7f2-5f39-4ebb-8f4a-4406fab0decc.
powershell -File scripts\dev\run_cds_gold_001_e2e.ps1
```

RUN 2 is already on the live stack: `5bcdb8eb-75bc-440b-9bcb-3a963b574360`.
Raw snapshots: `AI_context/execution_reports/cds_gold_001_e2e_20260817-182830.json` (initial 5 gold findings + additional batch) and `cds_gold_001_run2_reeval.json` (canonical types + seller/buyer after rebuild).

F12 (2026-08-17) tightens gold fact extraction so RUN 3 can fire area mismatch, Fard issue dates, historic tax, waiver, and bank pack. Do not reuse RUN 1 or RUN 2 as the gold-complete matter.
