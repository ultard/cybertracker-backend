from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL


class LogLevel(StrEnum):
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """Настройки приложения."""

    environment: str = "dev"
    log_level: LogLevel = LogLevel.INFO

    app_name: str = "CyberTracker API"
    debug: bool = False

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    reload: bool = False
    origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_secret_key: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    ai_model_path: str = "models/xgboost_attendance.ubj"
    qr_token_ttl_seconds: int = 30

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "cybertracker"
    postgres_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def parse_origins(self) -> list[str]:
        """Разбор `origins` в список URL (через запятую)."""
        return [origin.strip() for origin in self.origins.split(",") if origin.strip()]

    @property
    def db_url(self) -> URL:
        """Строка подключения к БД как `yarl.URL`."""
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.postgres_host,
            port=self.postgres_port,
            user=self.postgres_user,
            password=self.postgres_password,
            path=f"/{self.postgres_db}",
        )

    @property
    def database_url(self) -> str:
        """Строка для SQLAlchemy / Alembic."""
        return str(self.db_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
