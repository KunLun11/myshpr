"""Background tasks (ARQ).

The daily reminder job is idempotent: it can be re-run at any time and the
notification dedupe keys prevent duplicates.
"""

from app.core.logging import get_logger
from app.db.session import async_session_factory, engine
from app.services.reminders import run_daily_reminders

logger = get_logger(__name__)


async def daily_reminders(ctx: dict) -> dict:
    async with async_session_factory() as session:
        result = await run_daily_reminders(session)
    logger.info(
        "daily_reminders finished: created=%s duplicates=%s",
        result.created,
        result.duplicates,
    )
    return {"created": result.created, "duplicates": result.duplicates}


async def shutdown(ctx: dict) -> None:
    await engine.dispose()
