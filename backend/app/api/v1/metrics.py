"""Prometheus metrics endpoint.

Kept out of the OpenAPI schema and meant to be scraped from the private
network (or a platform sidecar), not exposed through the public ingress.
"""

from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.metrics import registry
from app.db.session import pool_stats

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not get_settings().METRICS_ENABLED:
        raise NotFoundError("Resource not found", "NOT_FOUND")
    return Response(
        content=registry.render(db_pool=pool_stats()),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
