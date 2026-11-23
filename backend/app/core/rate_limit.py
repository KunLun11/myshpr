"""Simple in-memory rate limiting.

Used as a stopgap for login/register/topic-check/upload before the Redis
backed limiter arrives in stage 5. Not suitable for multi-worker prod,
but fine for a single-process MVP pilot.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.errors import AppError


class RateLimiter:
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


def enforce_rate_limit(limiter: RateLimiter, key: str) -> None:
    if not limiter.allow(key):
        raise AppError(
            "RATE_LIMITED",
            "Слишком много попыток. Попробуйте через минуту.",
            status_code=429,
            headers={"Retry-After": "60"},
        )


# Pre-configured limiters (limits are intentionally generous for a pilot).
login_limiter = RateLimiter(limit=10, window_seconds=60)
register_limiter = RateLimiter(limit=5, window_seconds=60)
topic_check_limiter = RateLimiter(limit=30, window_seconds=60)
upload_limiter = RateLimiter(limit=20, window_seconds=60)

# Five bad passwords for the same email lock login for 15 minutes (HTTP 423).
login_failure_tracker = FailureTracker(limit=5, window_seconds=15 * 60)
