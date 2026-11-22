"""Application configuration.

All environment variables are documented in ``backend/.env.example``.
The app intentionally fails at startup when critical variables are missing.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

DEFAULT_UPLOAD_MIME = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/png",
    "image/jpeg",
    "application/zip",
)

DEFAULT_UPLOAD_EXTENSIONS = (".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".zip")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Runtime
    ENV: Literal["dev", "prod"] = "dev"
    DEBUG: bool = False

    # Database / storage / cache
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    BACKEND_URL: str = "http://localhost:8000"

    # Auth (used starting from stage 2, validated now)
    JWT_SECRET: str
    ACCESS_TOKEN_TTL_MIN: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: list[str] = []

    # Topic check thresholds
    TOPIC_DUPLICATE_WARN: float = 0.55
    TOPIC_DUPLICATE_BLOCK: float = 0.85
    TOPIC_BROADNESS_OK: int = 70
    TOPIC_BROADNESS_WARN: int = 40

    # Dashboard thresholds
    INACTIVITY_YELLOW_DAYS: int = 7
    INACTIVITY_RED_DAYS: int = 14
    CHECKPOINT_SOON_DAYS: int = 7
    CHECKLIST_SOON_DAYS: int = 3
    CHECKLIST_STALLED_DAYS: int = 14
    FINAL_FILE_DAYS_BEFORE: int = 14
    REVIEW_WAIT_DAYS: int = 5

    # File storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    MEDIA_ROOT: Path = Path("media")
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_FILES_PER_PROJECT: int = 10
    ALLOWED_UPLOAD_MIME: list[str] = list(DEFAULT_UPLOAD_MIME)
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = list(DEFAULT_UPLOAD_EXTENSIONS)
    S3_ENDPOINT: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str | None = None

    # Email (optional)
    EMAIL_FROM: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    @field_validator(
        "CORS_ORIGINS", "ALLOWED_UPLOAD_MIME", "ALLOWED_UPLOAD_EXTENSIONS", mode="before"
    )
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if self.ENV == "prod":
            if not self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
            if "myschoolproject" in self.DATABASE_URL:
                raise ValueError("Default database password is not allowed in production")
            if self.STORAGE_BACKEND == "s3" and not (self.S3_BUCKET and self.S3_ENDPOINT):
                raise ValueError("S3 storage requires S3_ENDPOINT and S3_BUCKET")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not self.JWT_SECRET:
            raise ValueError("JWT_SECRET is required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
