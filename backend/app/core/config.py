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
    CORS_ORIGINS: str = "http://localhost:3000"  # Comma-separated origins
    
    # External Verification Portal URLs (for assisted verification)
    ESTAMP_VERIFY_URL: str = "https://estamping.punjab-zameen.gov.pk/verify"  # Placeholder
    REGISTRY_VERIFY_URL: str = "https://lda.gop.pk/rod-verify"  # Placeholder
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

