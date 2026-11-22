"""Health and readiness probes."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe (database connectivity)")
async def readyz(
    response: Response, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - depends on infra
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}
    return {"status": "ready"}
