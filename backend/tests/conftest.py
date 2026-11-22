"""Shared test fixtures.

A Postgres database is required. Point ``TEST_DATABASE_URL`` (or
``DATABASE_URL``) at it. Migrations are applied once per test session;
each test runs inside a transaction that is rolled back afterwards.
"""

import os
from pathlib import Path

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


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations() -> None:
    command.upgrade(_alembic_config(), "head")


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()
