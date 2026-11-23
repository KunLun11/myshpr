"""Stage 7: security and observability tests."""

import json
import logging
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

import app.api.v1.metrics as metrics_module
import app.core.rate_limit as rate_limit
from app.core.logging import JsonFormatter, request_id_ctx, user_id_ctx
from app.core.metrics import registry
from app.core.rate_limit import AdaptiveLimiter, RateLimiter


async def test_register_endpoint_is_rate_limited(client: AsyncClient) -> None:
    """Sixth registration attempt from one address is rejected with 429."""
    results = []
    for index in range(6):
        results.append(
            await client.post(
                "/api/v1/auth/register/student",
                json={
                    "invite_code": "NOPE1234",
                    "email": f"rate{index}@example.com",
                    "password": "password123",
                    "full_name": "Rate Limit",
                },
            )
        )

    assert all(response.status_code != 429 for response in results[:5])
    assert results[5].status_code == 429
    assert results[5].json()["code"] == "RATE_LIMITED"
    assert results[5].headers["Retry-After"] == "60"


async def test_security_headers_and_request_id_echo(client: AsyncClient) -> None:
    response = await client.get("/api/v1/healthz", headers={"X-Request-ID": "trace-me-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-me-1"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    # HSTS is only sent when explicitly enabled (behind TLS).
    assert "Strict-Transport-Security" not in response.headers


async def test_metrics_endpoint_reports_requests_and_pool(client: AsyncClient) -> None:
    registry.reset()
    await client.get("/api/v1/healthz")

    response = await client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "# TYPE http_requests_total counter" in body
    assert 'route="/api/v1/healthz"' in body
    assert "http_request_duration_seconds_bucket" in body
    assert "# TYPE background_job_runs_total counter" in body


async def test_metrics_can_be_disabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        metrics_module, "get_settings", lambda: SimpleNamespace(METRICS_ENABLED=False)
    )
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_json_formatter_serialises_context() -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="processed %s",
        args=("request",),
        exc_info=None,
    )
    record.request_id = "rid-1"
    record.user_id = "user-1"
    record.route = "/api/v1/x"
    record.method = "GET"
    record.status = 200
    record.duration_ms = 12.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "processed request"
    assert payload["request_id"] == "rid-1"
    assert payload["user_id"] == "user-1"
    assert payload["route"] == "/api/v1/x"
    assert payload["duration_ms"] == 12.5
    assert payload["time"].endswith("+00:00")


def test_json_formatter_falls_back_to_contextvars() -> None:
    rid_token = request_id_ctx.set("ctx-rid")
    uid_token = user_id_ctx.set("ctx-user")
    try:
        record = logging.LogRecord("app.test", logging.WARNING, __file__, 1, "hi", None, None)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(rid_token)
        user_id_ctx.reset(uid_token)

    assert payload["request_id"] == "ctx-rid"
    assert payload["user_id"] == "ctx-user"


def test_memory_limiter_window() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False
    limiter.reset()
    assert limiter.allow("k") is True


async def test_adaptive_limiter_uses_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.counts: dict[str, int] = {}
            self.expirations: list[tuple[str, int]] = []

        async def incr(self, key: str) -> int:
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def expire(self, key: str, seconds: int, nx: bool = False) -> None:
            self.expirations.append((key, seconds, nx))

    fake = FakeRedis()
    monkeypatch.setattr(
        rate_limit, "get_settings", lambda: SimpleNamespace(RATE_LIMIT_BACKEND="redis")
    )
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: fake)

    limiter = AdaptiveLimiter("demo", limit=2, window_seconds=30)
    assert await limiter.allow("user") is True
    assert await limiter.allow("user") is True
    assert await limiter.allow("user") is False
    assert len(fake.expirations) == 3
    assert set(fake.expirations) == {("rl:demo:user", 30, True)}


async def test_adaptive_limiter_fails_open_when_redis_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenRedis:
        async def incr(self, key: str) -> int:
            raise ConnectionError("redis down")

    monkeypatch.setattr(
        rate_limit, "get_settings", lambda: SimpleNamespace(RATE_LIMIT_BACKEND="redis")
    )
    monkeypatch.setattr(rate_limit, "_get_redis", lambda: BrokenRedis())

    limiter = AdaptiveLimiter("demo", limit=1, window_seconds=30)
    assert await limiter.allow("user") is True
    # Falls back to the in-memory window, which still enforces the limit.
    assert await limiter.allow("user") is False
