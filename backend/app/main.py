"""FastAPI application factory.

Structure:
- ``create_app`` builds the app (lifespan, middleware, CORS, error handlers).
- No database connection is made at import time.
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.csrf import allowed_origin_set, is_request_allowed
from app.core.errors import AppError
from app.core.logging import get_logger, request_id_ctx, setup_logging
from app.core.metrics import registry
from app.core.rate_limit import close_rate_limit_redis
from app.db.session import engine

logger = get_logger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    # The API only returns JSON and file downloads; nothing should render.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting (env=%s)", get_settings().ENV)
    yield
    await close_rate_limit_redis()
    await engine.dispose()
    logger.info("Application stopped")


def _route_template(request: Request) -> str:
    """Route label with concrete path params replaced by their names.

    FastAPI 0.165 wraps included routers, so ``route.path`` is the router-local
    path without the ``/api/v1`` prefix. The full URL path plus the matched
    ``path_params`` reconstructs a low-cardinality template.
    """
    if request.scope.get("route") is None:
        return "unmatched"
    path = request.url.path
    for name, value in (request.scope.get("path_params") or {}).items():
        if value not in (None, ""):
            path = path.replace(str(value), "{" + name + "}")
    return path


async def _origin_guard_middleware(request: Request, call_next: Callable[[Request], Awaitable]):
    """Reject unsafe cross-origin browser requests (CSRF defence in depth)."""
    settings = get_settings()
    allowed = allowed_origin_set(settings.CORS_ORIGINS, settings.CSRF_TRUSTED_ORIGINS)
    if not is_request_allowed(
        method=request.method,
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
        fetch_site=request.headers.get("sec-fetch-site"),
        allowed=allowed,
        fail_closed=settings.ENV == "prod",
    ):
        logger.warning(
            "origin guard rejected: method=%s path=%s origin=%s",
            request.method,
            request.url.path,
            request.headers.get("origin"),
        )
        return JSONResponse(
            status_code=403,
            content={
                "type": "about:blank",
                "title": "csrf_origin_rejected",
                "status": 403,
                "detail": "Запрос с недопустимого источника",
                "code": "CSRF_ORIGIN_REJECTED",
            },
        )
    return await call_next(request)


async def _request_context_middleware(request: Request, call_next: Callable[[Request], Awaitable]):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    request.state.request_id = request_id
    token = request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    duration = time.perf_counter() - start
    duration_ms = round(duration * 1000, 2)

    route_path = _route_template(request)
    user_id = getattr(request.state, "user_id", None)

    response.headers["X-Request-ID"] = request_id
    response.headers.update(SECURITY_HEADERS)
    if get_settings().HSTS_ENABLED:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    registry.observe_request(
        method=request.method,
        route=route_path,
        status=response.status_code,
        seconds=duration,
    )
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "route": route_path,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=exc.to_problem(), headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "type": "about:blank",
                "title": "validation_error",
                "status": 422,
                "detail": "Некорректные данные запроса",
                "code": "VALIDATION_ERROR",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "internal_error",
                "status": 500,
                "detail": "Внутренняя ошибка сервера",
                "code": "INTERNAL_ERROR",
            },
        )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Индивидуальный проект API",
        description="Backend платформы ведения индивидуальных проектов школьников.",
        version="0.1.0",
        lifespan=lifespan,
    )

    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.middleware("http")(_origin_guard_middleware)
    app.middleware("http")(_request_context_middleware)
    _register_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
