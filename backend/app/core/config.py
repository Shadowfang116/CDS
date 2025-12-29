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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

