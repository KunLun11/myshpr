"""Simple in-memory rate limiting.

Used as a stopgap for login/register/topic-check/upload before the Redis
backed limiter arrives in stage 5. Not suitable for multi-worker prod,
but fine for a single-process MVP pilot.
"""

import time
from collections import defaultdict, deque
from threading import Lock


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


# Pre-configured limiters (limits are intentionally generous for a pilot).
login_limiter = RateLimiter(limit=10, window_seconds=60)
register_limiter = RateLimiter(limit=5, window_seconds=60)
topic_check_limiter = RateLimiter(limit=30, window_seconds=60)
upload_limiter = RateLimiter(limit=20, window_seconds=60)
