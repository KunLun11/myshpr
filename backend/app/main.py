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
from app.core.errors import AppError
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

logger = get_logger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting (env=%s)", get_settings().ENV)
    yield
    await engine.dispose()
    logger.info("Application stopped")


async def _request_context_middleware(request: Request, call_next: Callable[[Request], Awaitable]):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers.update(SECURITY_HEADERS)
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
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

    app.middleware("http")(_request_context_middleware)
    _register_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
