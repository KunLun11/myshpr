"""Unit tests for settings validation (no database required)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_URL = "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_requires_database_url_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_dev_defaults() -> None:
    settings = Settings(_env_file=None, DATABASE_URL=VALID_URL, JWT_SECRET="secret")
    assert settings.ENV == "dev"
    assert settings.MAX_UPLOAD_BYTES == 25 * 1024 * 1024
    assert settings.ACCESS_TOKEN_TTL_MIN == 15


def test_csv_list_parsing() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL=VALID_URL,
        JWT_SECRET="secret",
        CORS_ORIGINS="http://localhost:3000, http://example.com",
    )
    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]


def test_prod_rejects_short_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV="prod", DATABASE_URL=VALID_URL, JWT_SECRET="short")


def test_prod_rejects_default_db_password() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ENV="prod",
            DATABASE_URL="postgresql+asyncpg://myschoolproject:myschoolproject@db:5432/x",
            JWT_SECRET="x" * 40,
            RATE_LIMIT_BACKEND="redis",
        )


def test_prod_rejects_placeholder_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ENV="prod",
            DATABASE_URL="postgresql+asyncpg://myschoolproject:CHANGE-ME-DB@db:5432/x",
            JWT_SECRET="x" * 40,
            RATE_LIMIT_BACKEND="redis",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ENV="prod",
            DATABASE_URL="postgresql+asyncpg://app:strongpass@db:5432/x",
            JWT_SECRET="CHANGE-ME-AT-LEAST-32-CHARACTERS-LONG",
            RATE_LIMIT_BACKEND="redis",
        )


def test_prod_allows_default_db_name_with_strong_password() -> None:
    settings = Settings(
        _env_file=None,
        ENV="prod",
        DATABASE_URL="postgresql+asyncpg://myschoolproject:s3cret-pass@db:5432/myschoolproject",
        JWT_SECRET="x" * 40,
        RATE_LIMIT_BACKEND="redis",
    )
    assert settings.ENV == "prod"


def test_prod_accepts_strong_config() -> None:
    settings = Settings(
        _env_file=None,
        ENV="prod",
        DATABASE_URL="postgresql+asyncpg://app:strongpass@db:5432/x",
        JWT_SECRET="x" * 40,
        RATE_LIMIT_BACKEND="redis",
    )
    assert settings.ENV == "prod"


def test_prod_requires_redis_rate_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ENV="prod",
            DATABASE_URL="postgresql+asyncpg://app:strongpass@db:5432/x",
            JWT_SECRET="x" * 40,
        )
