"""ARQ worker configuration.

Run locally:

    uv run arq app.workers.settings.WorkerSettings

The cron entry is expressed in UTC (03:00 UTC = 06:00 Europe/Moscow).
Schools keep their own timezone; the job converts to it when computing
"today", so the schedule only decides when the sweep happens.
"""

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import daily_reminders, shutdown


class WorkerSettings:
    functions = [daily_reminders]
    cron_jobs = [cron(daily_reminders, hour=3, minute=0, run_at_startup=False)]
    redis_settings = RedisSettings.from_dsn(get_settings().REDIS_URL)
    on_shutdown = shutdown
