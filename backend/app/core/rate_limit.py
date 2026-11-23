"""Rate limiting and login failure tracking.

Two backends are supported (``RATE_LIMIT_BACKEND``):

* ``memory`` — an in-process sliding window. Fine for tests and a
  single-worker dev server.
* ``redis`` — a fixed-window counter shared by all uvicorn workers and
  hosts. Production runs multiple workers, so the compose stack sets this.

The limiter fails **open** when Redis is unreachable: an outage of the cache
must not lock every user out of the product. The event is logged so the
alerting pipeline can catch it.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """In-memory sliding-window limiter (single process)."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window = self._hits[key]
            while window and now - window[0] > self.window_seconds:
                window.popleft()
            if len(window) >= self.limit:
                return False
            window.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class AdaptiveLimiter:
    """Dispatches to Redis when configured, memory otherwise."""

    def __init__(self, name: str, limit: int, window_seconds: int) -> None:
        self.name = name
        self.limit = limit
        self.window_seconds = window_seconds
        self._memory = RateLimiter(limit=limit, window_seconds=window_seconds)

    async def allow(self, key: str) -> bool:
        if get_settings().RATE_LIMIT_BACKEND == "redis":
            try:
                return await _redis_allow(self.name, key, self.limit, self.window_seconds)
            except Exception:  # pragma: no cover - depends on infra
                logger.warning(
                    "rate limiter backend unavailable, falling back to memory: name=%s",
                    self.name,
                )
        return self._memory.allow(key)

    def reset(self) -> None:
        """Reset the in-memory window (used by tests)."""
        self._memory.reset()


_redis_client = None


def _get_redis():
    """Lazy Redis client so tests without Redis never open a connection."""
    global _redis_client
    if _redis_client is None:
        from redis.asyncio import Redis  # imported lazily to keep dev imports light

        _redis_client = Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis_client


async def _redis_allow(name: str, key: str, limit: int, window_seconds: int) -> bool:
    client = _get_redis()
    redis_key = f"rl:{name}:{key}"
    count = await client.incr(redis_key)
    # SET only if the key has no TTL: survives a crash between INCR and EXPIRE.
    await client.expire(redis_key, window_seconds, nx=True)
    return int(count) <= limit


async def close_rate_limit_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


class FailureTracker:
    """Counts failures per key; used to lock accounts after repeated bad logins."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        window = self._hits[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        return window

    def is_locked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self.limit

    def record(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._hits.clear()


async def enforce_rate_limit(limiter: AdaptiveLimiter, key: str) -> None:
    if not await limiter.allow(key):
        raise AppError(
            "RATE_LIMITED",
            "Слишком много попыток. Попробуйте через минуту.",
            status_code=429,
            headers={"Retry-After": "60"},
        )


# Pre-configured limiters (limits are intentionally generous for a pilot).
login_limiter = AdaptiveLimiter("login", limit=10, window_seconds=60)
register_limiter = AdaptiveLimiter("register", limit=5, window_seconds=60)
topic_check_limiter = AdaptiveLimiter("topic_check", limit=30, window_seconds=60)
upload_limiter = AdaptiveLimiter("upload", limit=20, window_seconds=60)

# Five bad passwords for the same email lock login for 15 minutes (HTTP 423).
login_failure_tracker = FailureTracker(limit=5, window_seconds=15 * 60)
