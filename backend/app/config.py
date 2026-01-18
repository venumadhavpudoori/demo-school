"""Application configuration with environment variable loading."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env file
    )

    # Application
    app_name: str = "School ERP"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database - SQLite for local development, PostgreSQL for production
    database_url: str = "sqlite:///./school_erp.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Flower (Celery monitoring)
    flower_port: int = 5555
    flower_basic_auth: str | None = None  # Format: "user:password"

    # Multi-tenancy
    base_domain: str = "localhost"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
