# Environment Variable Matrix

Reference for deployment. **Required** means the app will fail or refuse to start in that environment if missing or invalid.

---

## Table

| Variable | Required (Dev) | Required (Prod) | Example | Notes |
|----------|----------------|-----------------|---------|------|
| **APP_ENV** | No | Yes | `production` | `development` \| `staging` \| `production`. Prod enables secret checks. |
| **POSTGRES_HOST** | No | No | `db` | Default `db` (Compose service name). |
| **POSTGRES_PORT** | No | No | `5432` | |
| **POSTGRES_USER** | No | No | `bank_diligence` | |
| **POSTGRES_PASSWORD** | No | **Yes** | *(secret)* | Min 12 chars in prod. No placeholder. |
| **POSTGRES_DB** | No | No | `bank_diligence` | |
| **APP_SECRET_KEY** | No | **Yes** | *(secret)* | Min 32 chars in prod. Used for JWT signing. |
| **APP_ALGORITHM** | No | No | `HS256` | |
| **APP_ACCESS_TOKEN_EXPIRE_HOURS** | No | No | `24` | |
| **MINIO_ENDPOINT** | No | No | `minio` | Service name in Compose. |
| **MINIO_PORT** | No | No | `9000` | |
| **MINIO_ROOT_USER** | No | No | `minioadmin` | |
| **MINIO_ROOT_PASSWORD** | No | **Yes** | *(secret)* | Min 12 chars in prod. |
| **MINIO_REGION** | No | No | `us-east-1` | |
| **MINIO_BUCKET** | No | No | `case-files` | Bucket name. |
| **MINIO_USE_SSL** | No | No | `false` | Set true if MinIO is served over TLS. |
| **MINIO_EXTERNAL_ENDPOINT** | No | No | `YOUR_PUBLIC_HOSTNAME` | Host used in presigned URLs (browser). |
| **MINIO_EXTERNAL_PORT** | No | No | `9000` | Port for presigned URLs. |
| **CORS_ORIGINS** | No | **Yes** (restrict) | `https://YOUR_PUBLIC_HOSTNAME` | Comma-separated. Prod should list only allowed origins. |
| **RETENTION_DAYS** | No | No | `365` | Only **Closed** cases older than this are pruned by retention job. |
| **DOC_CONVERT_TIMEOUT_SECONDS** | No | No | `90` | LibreOffice convert timeout for DOC→PDF. |
| **INTEGRATIONS_ENCRYPTION_KEY** | No | If using integrations | *(secret)* | If set, min 32 chars in prod. Encrypts webhook/email secrets. |
| **EMAIL_ENABLED** | No | No | `false` | Enable SMTP sending. |
| **SMTP_HOST** | No | No | `mailhog` | |
| **SMTP_PORT** | No | No | `1025` | |
| **SMTP_USERNAME** / **SMTP_PASSWORD** | No | No | | Leave empty if not used. |
| **SMTP_USE_TLS** | No | No | `false` | |
| **SMTP_FROM_NAME** / **SMTP_FROM_EMAIL** | No | No | | Sender identity. |
| **WEBHOOK_DELIVERY_ENABLED** | No | No | `true` | |
| **WEBHOOK_TIMEOUT_SECONDS** | No | No | `10` | |
| **HF_EXTRACTOR_URL** | No | No | `http://hf-extractor:8090` | Optional ML extractor. |
| **HF_EXTRACTOR_VERSION** | No | No | `rules-v1` | |
| **HF_EXTRACTOR_ENABLE_LAYOUTXLM** | No | No | `false` | |
| **HF_LAYOUTXLM_MODEL_PATH** | No | No | `` | |
| **OCR_DPI** / **OCR_DPI_MIN/MAX** | No | No | `300` / `300` / `400` | Optional OCR tuning. |
| **OCR_LANG** / **OCR_PSM** / **OCR_OEM** | No | No | `eng` / `6` / `1` | |
| **OCR_MAX_PAGES_PER_DOC** | No | No | `50` | |
| **OCR_TIMEOUT_SECONDS** | No | No | `120` | |
| **OCR_ENABLE_PREPROCESS** etc. | No | No | `true` | Optional preprocessing flags. |
| **APP_BUILD_SHA** | No | No | `abc123` | Optional; shown by `/api/v1/admin/build-info`. |
| **APP_BUILD_TIME** | No | No | `2024-02-11T12:00:00Z` | Optional; shown by build-info. |

---

## Secrets policy

- **No placeholders in production.** Values like `change_me`, `REPLACE_ME_*`, or empty where a secret is required will cause the API to fail startup in `APP_ENV=production`.
- **Rotation:**
  - **APP_SECRET_KEY:** Generate a new 32+ character secret. Deploy with the new value; all existing JWTs will be invalid after deploy (users must log in again).
  - **POSTGRES_PASSWORD:** Change in DB and in `.env`, then recreate/restart the `db` service and any app that connects to it.
  - **MINIO_ROOT_PASSWORD:** Update in MinIO and in `.env`, restart MinIO and API/worker so they reconnect.
- **Do not store `.env` in git.** Use `.env.prod.example` as a template and keep real `.env` only on the deployment host or in a secrets manager.
