# Rulepacks

- `punjab_mortgage_v1.yaml` — **ACTIVE**. Compose, `RULEPACK_PATH`, and the worker default load this pack. GOLD-*-01 stay here unchanged.
- `archive/generic_mvp_legacy.yaml` — KYC-02 photograph, KYC-05 income/salary, KYC-07 utility, KYC-10 co-applicant. Not loaded in production.
- `../05_rulepack_v1.yaml` — full compatibility pack for `backend/tests/rulepack` golden fixtures.

Do not hard-code RUN 3 finding values. Applicability (`applies_when`) stays in YAML.
