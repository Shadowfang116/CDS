from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_VALUES = {
    "change_me",
    "change_me_to_random_secret_key",
    "minioadmin",
    "",
}


class Settings(BaseSettings):
    """
    Production-safe settings.
    In production, placeholder or weak secrets cause startup failure.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # Environment
    APP_ENV: str = Field(default="development")  # development | staging | production

    # Database
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "bank_diligence"
    POSTGRES_PASSWORD: SecretStr = SecretStr("change_me")
    POSTGRES_DB: str = "bank_diligence"

    # JWT
    APP_SECRET_KEY: SecretStr = SecretStr("change_me_to_random_secret_key")
    APP_ALGORITHM: str = "HS256"
    APP_ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # MinIO
    MINIO_ENDPOINT: str = "minio"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: SecretStr = SecretStr("change_me")
    MINIO_REGION: str = "us-east-1"
    MINIO_BUCKET: str = "case-files"
    MINIO_USE_SSL: bool = False
    MINIO_EXTERNAL_ENDPOINT: str = "localhost"
    MINIO_EXTERNAL_PORT: int = 9000

    # Retention
    RETENTION_DAYS: int = 365

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Optional integrations
    INTEGRATIONS_ENCRYPTION_KEY: SecretStr = SecretStr("")

    # External verification portal URLs
    ESTAMP_VERIFY_URL: str = "https://estamping.punjab-zameen.gov.pk/verify"
    REGISTRY_VERIFY_URL: str = "https://lda.gop.pk/rod-verify"

    # Email (Phase 9)
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_USE_TLS: bool = False
    SMTP_FROM_NAME: str = "Bank Diligence Platform"
    SMTP_FROM_EMAIL: str = "noreply@bankdiligence.local"

    # Webhooks (Phase 9)
    WEBHOOK_DELIVERY_ENABLED: bool = True
    WEBHOOK_TIMEOUT_SECONDS: int = 10

    # HF Extractor
    HF_EXTRACTOR_URL: str = "http://hf-extractor:8090"
    HF_EXTRACTOR_VERSION: str = "rules-v1"
    HF_EXTRACTOR_ENABLE_LAYOUTXLM: bool = False
    HF_LAYOUTXLM_MODEL_PATH: str = ""

    # OCR
    OCR_DPI: int = 300
    OCR_DPI_MIN: int = 300
    OCR_DPI_MAX: int = 400
    OCR_LANG: str = "eng"
    OCR_PSM: int = 6
    OCR_OEM: int = 1
    OCR_MAX_PAGES_PER_DOC: int = 50
    OCR_IMAGE_MAX_SIDE: int = 2200
    OCR_TIMEOUT_SECONDS: int = 120

    # Doc conversion (LibreOffice) - Phase 8
    DOC_CONVERT_TIMEOUT_SECONDS: int = 90
    OCR_ENABLE_PREPROCESS: bool = True
    OCR_ENABLE_ENHANCED_PREPROCESS: bool = True
    OCR_ENABLE_SCRIPT_DETECTION: bool = True

    def assert_production_safe(self) -> None:
        if self.APP_ENV != "production":
            return

        def check_secret(name: str, secret: SecretStr, min_len: int):
            raw = secret.get_secret_value()
            if not raw or raw in PLACEHOLDER_VALUES or "change_me" in raw:
                raise RuntimeError(f"[CONFIG] {name} is not set for production.")
            if len(raw) < min_len:
                raise RuntimeError(f"[CONFIG] {name} is too short for production.")

        check_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD, 12)
        check_secret("APP_SECRET_KEY", self.APP_SECRET_KEY, 32)
        check_secret("MINIO_ROOT_PASSWORD", self.MINIO_ROOT_PASSWORD, 12)

        if self.INTEGRATIONS_ENCRYPTION_KEY.get_secret_value():
            check_secret("INTEGRATIONS_ENCRYPTION_KEY", self.INTEGRATIONS_ENCRYPTION_KEY, 32)


settings = Settings()
settings.assert_production_safe()
