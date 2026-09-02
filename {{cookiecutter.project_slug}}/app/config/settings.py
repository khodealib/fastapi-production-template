from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import Environment

# A placeholder, not a credential: _guard_secret rejects it in production.
DEV_SECRET = "dev-insecure-secret-change-me"  # nosec B105


class Settings(BaseSettings):
    """Central configuration, read from environment and ``.env``.

    Mirror of Django's ``settings.py``: every value is overridable via an
    environment variable of the same name (case-sensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- app -------------------------------------------------------------
    APP_NAME: str = "{{ cookiecutter.project_name }}"
    APP_VERSION: str = "{{ cookiecutter.version }}"
    APP_DESCRIPTION: str = "{{ cookiecutter.description }}"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    SECRET_KEY: str = DEV_SECRET
    ALLOWED_HOSTS: list[str] = ["*"]
    # Number of reverse proxies in front of the app. 0 ignores X-Forwarded-For
    # entirely; any other value must match the deployment exactly, or clients
    # can forge the header and escape rate limiting.
    TRUSTED_PROXY_HOPS: int = 0
    CORS_ORIGINS: list[str] = ["http://localhost:8000"]
    ENABLE_METRICS: bool = True
    ENABLE_TRACING: bool = False  # opt-in: set to True and wire an OTLP exporter

    # --- database ---------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://app:app@localhost:5432/{{ cookiecutter.project_slug }}"
    DB_ECHO: bool = False

    # --- auth -------------------------------------------------------------
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- redis / cache / queues -------------------------------------------
    REDIS_URL: str | None = None
    CACHE_DEFAULT_TTL_SECONDS: int = 300

    # --- rate limiting -----------------------------------------------------
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    RATE_LIMIT_STRATEGY: str = "fixed-window"
    RATE_LIMIT_GLOBAL: str = "1000/minute"

    # --- email -------------------------------------------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_STARTTLS: bool = True
    EMAIL_FROM: str = "no-reply@example.com"

    # --- i18n / logging ----------------------------------------------------
    DEFAULT_LOCALE: str = "en"
    LOG_JSON: bool = False
    LOG_LEVEL: str = "INFO"

    # --- paths (computed) --------------------------------------------------
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "media"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT is Environment.PRODUCTION

    @model_validator(mode="after")
    def _guard_secret(self) -> "Settings":
        if self.is_production and self.SECRET_KEY == DEV_SECRET:
            raise ValueError("SECRET_KEY must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
