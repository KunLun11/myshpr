"""Async engine, session factory and per-request session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


def pool_stats() -> dict[str, int]:
    """Best-effort connection-pool gauges for /metrics; never raises."""
    pool = getattr(engine, "pool", None)
    if pool is None:
        return {}
    stats: dict[str, int] = {}
    for name, method in (
        ("checked_out", "checkedout"),
        ("checked_in", "checkedin"),
        ("size", "size"),
        ("overflow", "overflow"),
    ):
        getter = getattr(pool, method, None)
        if getter is None:
            continue
        try:
            stats[name] = int(getter())
        except Exception:  # pragma: no cover - driver specific
            continue
    return stats


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
