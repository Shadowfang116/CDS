from __future__ import annotations

import warnings

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_VALUES = {
    "change_me",
    "change_me_to_random_secret_key",
    "replace-with-32-plus-character-random-secret",
    "replace-with-strong-postgres-password",
    "replace-with-strong-minio-password",
    "replace-with-minio-user",
    "minioadmin",
    "",
}


def _is_placeholder_value(raw_value: str) -> bool:
    normalized = (raw_value or "").strip().lower()
    return (
        not normalized
        or normalized in PLACEHOLDER_VALUES
        or "change_me" in normalized
        or "replace-with" in normalized
    )


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
    APP_ENV: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )  # development | staging | production

    # Database
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "bank_diligence"
    POSTGRES_PASSWORD: SecretStr = SecretStr("change_me")
    POSTGRES_DB: str = "bank_diligence"

    # JWT
    APP_SECRET_KEY: SecretStr = Field(
        default=SecretStr("change_me_to_random_secret_key"),
        validation_alias=AliasChoices("APP_SECRET_KEY", "SECRET_KEY"),
    )
    APP_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    APP_ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # MinIO
    MINIO_ENDPOINT: str = "minio"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: SecretStr = SecretStr("change_me")
    MINIO_REGION: str = "us-east-1"
    MINIO_BUCKET: str = "case-files"
    MINIO_USE_SSL: bool = False
    MINIO_PUBLIC_ENDPOINT: str = Field(
        default="",
        validation_alias=AliasChoices("MINIO_PUBLIC_ENDPOINT", "MINIO_EXTERNAL_ENDPOINT"),
    )
    MINIO_PUBLIC_PORT: int = Field(
        default=9000,
        validation_alias=AliasChoices("MINIO_PUBLIC_PORT", "MINIO_EXTERNAL_PORT"),
    )
    PUBLIC_URL: str = "http://localhost"

    # Retention
    RETENTION_DAYS: int = 365

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 100

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("CORS_ORIGINS", "ALLOWED_ORIGINS"),
    )

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

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

    # OCR service
    OCR_SERVICE_URL: str = "http://localhost:8001"
    RULEPACK_PATH: str = "/app/backend/rules/diligence_rules.yaml"
    DEMO_MODE: bool = False

    # OCR
    OCR_DPI: int = 300
    OCR_DPI_MIN: int = 300
    OCR_DPI_MAX: int = 400
    OCR_ENABLE_ORIENTATION_DETECTION: bool = True
    OCR_LANG: str = "urd+eng"
    OCR_PSM: int = 6
    OCR_OEM: int = 1
    OCR_MAX_PAGES_PER_DOC: int = 50
    OCR_IMAGE_MAX_SIDE: int = 2200
    OCR_TIMEOUT_SECONDS: int = 120
    OCR_LOW_CHAR_COUNT_THRESHOLD: int = 50
    OCR_LOW_AVG_CONFIDENCE_THRESHOLD: int = 40
    OCR_HIGH_NOISE_RATIO_THRESHOLD: float = 0.6

    # Doc conversion (LibreOffice) - Phase 8
    DOC_CONVERT_TIMEOUT_SECONDS: int = 90
    OCR_ENABLE_PREPROCESS: bool = True
    OCR_ENABLE_ENHANCED_PREPROCESS: bool = True
    OCR_ENABLE_SCRIPT_DETECTION: bool = True

    def assert_production_safe(self) -> None:
        app_secret = self.APP_SECRET_KEY.get_secret_value()
        if _is_placeholder_value(app_secret) and self.APP_ENV != "production":
            warnings.warn(
                "[CONFIG] APP_SECRET_KEY is still using a default/example value.",
                RuntimeWarning,
                stacklevel=2,
            )

        if self.APP_ENV != "production":
            return

        def check_secret(name: str, secret: SecretStr, min_len: int):
            raw = secret.get_secret_value()
            if _is_placeholder_value(raw):
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
