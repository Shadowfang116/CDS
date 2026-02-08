from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "bank_diligence"
    POSTGRES_PASSWORD: str = "change_me"
    POSTGRES_DB: str = "bank_diligence"
    
    # JWT
    APP_SECRET_KEY: str = "change_me_to_random_secret_key"
    APP_ALGORITHM: str = "HS256"
    APP_ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # MinIO / S3
    MINIO_ENDPOINT: str = "minio"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "change_me"
    MINIO_REGION: str = "us-east-1"
    MINIO_BUCKET: str = "case-files"
    MINIO_USE_SSL: bool = False
    # External URL for presigned URLs (if different from internal endpoint)
    MINIO_EXTERNAL_ENDPOINT: str = "localhost"
    MINIO_EXTERNAL_PORT: int = 9000
    
    # Retention
    RETENTION_DAYS: int = 365  # Days to retain case data
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50  # Max file upload size in MB
    
    # CORS
    # Comma-separated origins for CORS (for direct API access, Swagger, etc.)
    # Frontend uses same-origin proxy, but CORS is still needed for direct API calls
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # External Verification Portal URLs (for assisted verification)
    ESTAMP_VERIFY_URL: str = "https://estamping.punjab-zameen.gov.pk/verify"  # Placeholder
    REGISTRY_VERIFY_URL: str = "https://lda.gop.pk/rod-verify"  # Placeholder
    
    # Email configuration (Phase 9)
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False
    SMTP_FROM_NAME: str = "Bank Diligence Platform"
    SMTP_FROM_EMAIL: str = "noreply@bankdiligence.local"
    
    # Webhook configuration (Phase 9)
    WEBHOOK_DELIVERY_ENABLED: bool = True
    WEBHOOK_TIMEOUT_SECONDS: int = 10
    
    # Encryption key for webhook secrets (derive from APP_SECRET_KEY if not set)
    INTEGRATIONS_ENCRYPTION_KEY: str = ""
    
    # HF Extractor service configuration
    HF_EXTRACTOR_URL: str = "http://hf-extractor:8090"
    HF_EXTRACTOR_VERSION: str = "rules-v1"  # "rules-v1" or "layoutxlm-v1"
    HF_EXTRACTOR_ENABLE_LAYOUTXLM: bool = False  # Explicit gate for LayoutXLM
    HF_LAYOUTXLM_MODEL_PATH: str = ""  # Optional model path (overrides env in hf-extractor)
    
    # OCR configuration (Phase 10 + P8 gold defaults + Urdu upgrade)
    OCR_DPI: int = 300  # Legacy: kept for backwards compatibility, use OCR_DPI_MIN/MAX
    OCR_DPI_MIN: int = 300  # Minimum DPI for dynamic rendering
    OCR_DPI_MAX: int = 400  # Maximum DPI for dynamic rendering
    OCR_LANG: str = "eng"  # Default language (can be overridden by script detection)
    OCR_PSM: int = 6  # Page segmentation mode
    OCR_OEM: int = 1  # OCR Engine Mode (1 = LSTM only)
    OCR_MAX_PAGES_PER_DOC: int = 50  # Safety limit
    OCR_IMAGE_MAX_SIDE: int = 2200  # Resize if larger
    OCR_TIMEOUT_SECONDS: int = 120  # Per page timeout
    OCR_ENABLE_PREPROCESS: bool = True  # Legacy: basic preprocessing
    OCR_ENABLE_ENHANCED_PREPROCESS: bool = True  # Enhanced preprocessing (deskew, denoise, etc.)
    OCR_ENABLE_SCRIPT_DETECTION: bool = True  # Script-aware language selection
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

