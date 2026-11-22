# ADR-06: Background jobs (Redis + ARQ)

**Status:** Accepted.

## Decision

- Redis backs the reminders queue (and later dashboard cache / rate limit).
- Prefer ARQ (native async); Celery acceptable if the team already owns it.
- Daily job computes reminders idempotently via `notifications.dedupe_key`.
- Email is optional; start in-app only.

Implemented in stage 5. Redis service + healthcheck are already in compose.
