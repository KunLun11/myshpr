"""Shared test fixtures.

A Postgres database is required. Point ``TEST_DATABASE_URL`` (or
``DATABASE_URL``) at it. Migrations are applied once per test session;
each test runs inside a transaction that is rolled back afterwards.
Services may call ``commit()``: the session is bound to a savepoint, so
commits never leak between tests.
"""

import os
import tempfile
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://postgres:postgres@localhost:55432/msp_test"
)

# Must be set before any ``app.*`` import triggers ``get_settings()``.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
# Keep bcrypt cheap in tests (production default stays 12).
os.environ.setdefault("BCRYPT_ROUNDS", "4")
# Uploads must not land in the developer's media/ folder.
os.environ.setdefault("MEDIA_ROOT", tempfile.mkdtemp(prefix="msp-test-media-"))
os.environ.setdefault("STORAGE_BACKEND", "local")

from app.api.deps import get_session  # noqa: E402
from app.core.rate_limit import (  # noqa: E402
    login_failure_tracker,
    login_limiter,
    register_limiter,
    topic_check_limiter,
    upload_limiter,
)
from app.main import app  # noqa: E402
from app.services.product_guide import clear_product_category_cache  # noqa: E402


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations() -> None:
    command.upgrade(_alembic_config(), "head")


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    for limiter in (login_limiter, register_limiter, topic_check_limiter, upload_limiter):
        limiter.reset()
    login_failure_tracker.reset_all()
    clear_product_category_cache()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as s:
            yield s
        await transaction.rollback()


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
